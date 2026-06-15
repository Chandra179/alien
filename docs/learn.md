# AI Infrastructure Learnings

## Modal — Serverless GPU

### Cold Start Anatomy (H200, 31B dense model)

| Phase | Duration (cached) | Duration (fresh) | Detail |
|-------|-------------------|------------------|--------|
| Container init | ~30s | ~30s | Image pull, env setup |
| Weights load | ~32s | ~5-10 min | from `huggingface-cache` volume vs fresh download (58.25 GiB) |
| torch.compile | ~8s | ~60s+ | from `vllm-cache` volume vs cold compilation |
| CUDA graph capture | ~14s | ~14s | 51 piecewise + 51 full graphs |
| Engine init (rest) | ~10s | ~10s | Profiling, KV cache allocation |
| Engine init total | ~107s | ~107s+download | Includes compile + graph capture |
| Warm-up query | ~7s | ~10s | Absorbs JIT kernel compilation spikes |
| **Total** | **~182s** | **10-15 min** | |

### Volumes

Modal [Volumes](https://modal.com/docs/guide/volumes) are network-attached persistent storage mounted into containers at runtime. Two are critical:

- **`huggingface-cache`** — stores model weights via `HF_HOME=/cache`. First deploy downloads 58+ GiB; subsequent deploys read from cache. Without this, every cold start pays the full download penalty.
- **`vllm-cache`** — stores torch.compile artifacts and AOT compilation outputs via `VLLM_CACHE_DIR=/root/.cache/vllm`. Reusing compiled graphs saves ~60s+ vs cold compilation.

Volumes persist across deploys; they are NOT wiped when a container scales down.

### Image Building

- **Dependencies**: use `.uv_pip_install("package==version")` on the image chain. Prefer this over raw `pip_install` for consistency with the project's `uv` tooling.
- **Bundled files**: use `.add_local_file(local_path, remote_path, copy=True)`. Without `copy=True`, files are mounted at container startup (not baked into the image layer), making them unavailable for subsequent image build steps.
- **Decorator params** (`gpu=`, `scaledown_window=`, `volumes=`): these are evaluated at **Python module load time on the deploy host** (your machine), not inside the Modal container. Module-level constants work fine for these.

### Path Resolution

Inside a Modal container, `__file__` resolves to `/root/modal_serve.py` (the script is copied flattened into the root). `Path(__file__).parent.parent.parent` does NOT point to your project root. For runtime config files, bundle them into the image and reference the bundled path:

```python
# At module level — try the bundled image path first, fall back to local project path
for path in (Path("/opt/config.yaml"), Path(__file__).resolve().parent.parent.parent / "config.yaml"):
    if path.exists():
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        break
```

### Idle Management

Two competing knobs:

| Knob | Behavior | Cost |
|------|----------|------|
| `keep_warm` | Keeps N containers alive permanently | H200: $4.54/hr × N continuously |
| `scaledown_window` | Kills container after N minutes of no requests | H200: $4.54/hr for those N idle minutes per session end |

For limited budgets (e.g., $240 hackathon credit), **30-minute `scaledown_window`** is the practical sweet spot. Max idle waste per session: ~$2.27. `keep_warm` is unsustainable (burns credit in ~53 hours).

### Cost Model (H200, ~$0.001261/sec → $4.54/hr)

| Event | Cost |
|-------|------|
| Cold start (182s from cache) | ~$0.23 |
| Per inference | ~$0.005-0.01 |
| Idle waste (30 min after last request) | ~$2.27 |
| Keep-warm (per hour) | $4.54 |

### Deploy Lifecycle

- **`modal deploy`** pushes a new immutable deployment with the current code + image. Existing live containers continue running the OLD deployment.
- **Killing a container** (`modal app stop`) restarts it from the same old deployment. Code/image changes require `modal deploy` to take effect.
- **Modal endpoints are public HTTPS URLs** with no built-in auth layer. The backend class must skip API key validation (unlike HuggingFace or OpenRouter).

---

## HuggingFace Hub

### Gated Models

Models like `google/gemma-4-31b-it` require an **accepted license agreement** on HuggingFace before the model becomes accessible. Without this, even a valid token returns 401/403.

### Token Access

- **Read access**: a HuggingFace token (`HF_TOKEN`) with READ scope is sufficient for downloading gated models.
- **Inference API**: requests require `Authorization: Bearer <token>` header. Tokens with only READ work for inference endpoints too.
- **Environment variables**: `HF_TOKEN` (auth), `HF_HUB_ENABLE_HF_TRANSFER=1` (fast downloads via hf_transfer Rust library). `HF_HOME` controls the cache directory.

### Model Identity

- Model IDs follow `org/model-name` format (e.g., `google/gemma-4-31b-it`).
- **Revisions**: optional branch/tag/commit hash pin. An invalid revision causes a 404 from the HF Hub. When in doubt, omit it and use the default (`main`).
- Checkpoint format: safetensors (`.safetensors` files), typically sharded. Gemma 4 31B = 2 shards, 58.25 GiB total.

---

## vLLM (Runtime Notes)

### Relevant Startup Flags

| Flag | Value | Reason |
|------|-------|--------|
| `--tensor-parallel-size` | 1 | Single GPU (H200). >1 only for multi-GPU. |
| `--enforce-eager` | omit (default=False) | Let vLLM use CUDA graphs. Eager mode is a debug fallback and hurts throughput. |
| `--async-scheduling` | enabled | Improves throughput for single-request scenarios. |
| `--tool-call-parser` | `gemma4` | Model-specific. Needed for structured output / tool calling. |
| `--reasoning-parser` | `gemma4` | Model-specific. Parses chain-of-thought in responses. |
| `--limit-mm-per-prompt` | `{"image":0,"video":0,"audio":0}` | Force text-only mode. Reduces memory overhead. |
| `--enable-auto-tool-choice` | enabled | Allows the model to decide when to use tools. |
| `--max-model-len` | auto | vLLM auto-detects. Gemma 4 → 262144. |
| `--gpu-memory-utilization` | 0.92 | Leaves headroom for CUDA graphs and KV cache. |
| `--safetensors-load-strategy` | `prefetch` | Can speed up weight loading on network FS; omitted when on 9P (Modal default). |
| `--generation-config` | `vllm` | Override model's `generation_config.json` sampling defaults (see Sampling Defaults below). |

### Gemma4-Specific Architecture Notes

- **Heterogeneous head dimensions**: `head_dim=256`, `global_head_dim=512`. This forces the TRITON_ATTN backend to prevent mixed-backend numerical divergence.
- **Multimodal-bidirectional attention**: causes vLLM to force `--disable_chunked_mm_input` automatically.
- **Architecture**: resolved as `Gemma4ForConditionalGeneration`.
- **Context length**: auto-detected as 262,144 tokens.
- **Chunked prefill**: enabled with `max_num_batched_tokens=8192`.

### Attention Backend

Gemma4's heterogeneous head dimensions trigger automatic selection of `TRITON_ATTN`. vLLM emits a config-time warning and forces this backend:

```
Gemma4 model has heterogeneous head dimensions (head_dim=256, global_head_dim=512).
Forcing TRITON_ATTN backend to prevent mixed-backend numerical divergence.
```

FlashInfer is used only for top-p & top-k sampling (via `topk_topp_sampler.py`), not for attention.

### CUDA Graph Memory Profiling (v0.21.0+)

Since v0.21.0, vLLM profiles CUDA graph memory during startup and subtracts it from the GPU memory budget. The effective `--gpu-memory-utilization` is lower than the nominal value:

- **Nominal**: `--gpu-memory-utilization=0.9200`
- **Effective**: `0.9145` (i.e., you lose ~0.55pp to CUDA graph overhead)
- **To maintain the same KV cache size**: increase `--gpu-memory-utilization` to `0.9255`
- **To disable profiling**: set `VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=0`

### GPU Memory Breakdown (H200, 31B dense)

| Component | Memory |
|-----------|--------|
| Model weights | 57.91 GiB |
| CUDA graphs (actual) | 0.67 GiB |
| CUDA graphs (estimated) | 0.76 GiB (difference: 13.7%) |
| Available KV cache | 65.94 GiB |
| KV cache capacity | 639,184 tokens |
| Max concurrency (262k-token reqs) | ~2.44x |

### Filesystem & Weight Loading

Modal containers use the **9P** filesystem by default. vLLM's auto-prefetch detection skips 9P because it is not a recognized network filesystem (NFS/Lustre):

```
Auto-prefetch is disabled because the filesystem (9P) is not a recognized network FS (NFS/Lustre).
If you want to force prefetching, start vLLM with --safetensors-load-strategy=prefetch.
```

Weight loading from `huggingface-cache` volume takes ~27.65s for a 58.25 GiB model (2 safetensors shards).

### Sampling Defaults

vLLM warns that the model's `generation_config.json` overrides its built-in defaults:

```
Default vLLM sampling parameters have been overridden by the model's `generation_config.json`:
`{'temperature': 1.0, 'top_k': 64, 'top_p': 0.95}`.
If this is not intended, please relaunch with `--generation-config vllm`.
```

### Chat Template Detection

vLLM auto-detects the chat template format as `openai`. You can override with `--chat-template-content-format`.

### Warm-Up

Sending a trivial chat completion query (`[{"role":"user","content":"Hi"}]`) during startup triggers JIT kernel compilation (Triton) for the first-inference shapes. Without this, the first real user request pays a 2-3s latency spike from JIT compilation. Warm-up absorbs this cost before traffic arrives.

**Known JIT compilation gaps during inference** — even after a warm-up query, some Triton kernels compile on first real use:
- `_compute_slot_mapping_kernel`
- `kernel_unified_attention`

Each causes a latency spike. Consider extending the warm-up to cover these shapes/configs if consistent tail latency matters.

### Throughput (H200, 31B dense, single request)

| Metric | Value |
|--------|-------|
| Avg prompt throughput | 244.6 tok/s |
| Avg generation throughput | 55.9 tok/s |

### Startup Timeline (cached)

| Phase | Duration |
|-------|----------|
| Container init | ~30s |
| Model load | ~29s |
| torch.compile (cached) | ~8.8s |
| Profiling/warmup run | ~0.3s |
| CUDA graph capture | ~15s |
| Engine init total | ~117s |
| Warm-up query | ~7s |
| **Total to healthy** | **~202s** |
