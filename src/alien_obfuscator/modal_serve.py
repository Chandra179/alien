"""Deploy Gemma 4 31B IT as an OpenAI-compatible vLLM server on Modal.

Usage
-----
    modal deploy src/alien_obfuscator/modal_serve.py   # deploy permanently
    modal run src/alien_obfuscator/modal_serve.py      # test locally

After deployment, set the URL in your .env::

    MODAL_API_URL=https://YOUR_WORKSPACE--modal-gemma-serve.modal.run
"""

import json
from typing import Any

import aiohttp
from aiohttp import ClientTimeout
import modal

MODEL_NAME = "google/gemma-4-31b-it"

N_GPU = 1
MINUTES = 60
VLLM_PORT = 8000

FAST_BOOT = False

vllm_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.9.0-devel-ubuntu24.04", add_python="3.12"
    )
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0")
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",
            "VLLM_LOG_STATS_INTERVAL": "1",
        }
    )
)

hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)

app = modal.App("modal-gemma")


@app.function(
    image=vllm_image,
    gpu=f"H200:{N_GPU}",
    scaledown_window=15 * MINUTES,
    timeout=10 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    secrets=[modal.Secret.from_name("hf-token")],
)
@modal.concurrent(max_inputs=100)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve() -> None:
    import subprocess

    cmd = [
        "vllm",
        "serve",
        MODEL_NAME,
        "--served-model-name",
        MODEL_NAME,
        "gemma-4-31b",
        "--host",
        "0.0.0.0",
        "--port",
        str(VLLM_PORT),
        "--uvicorn-log-level=info",
        "--async-scheduling",
    ]

    cmd += ["--enforce-eager" if FAST_BOOT else "--no-enforce-eager"]
    cmd += ["--tensor-parallel-size", str(N_GPU)]

    cmd += [
        "--limit-mm-per-prompt",
        f"'{json.dumps({'image': 0, 'video': 0, 'audio': 0})}'",
        "--enable-auto-tool-choice",
        "--reasoning-parser",
        "gemma4",
        "--tool-call-parser",
        "gemma4",
    ]

    print(*cmd)
    subprocess.Popen(" ".join(cmd), shell=True)


@app.local_entrypoint()
async def test(test_timeout: int = 15 * MINUTES) -> None:
    """Health-check the server and send a test prompt."""
    url = await serve.get_web_url.aio()

    messages: list[dict[str, str]] = [
        {"role": "user", "content": "Say hello in pirate speak."},
    ]

    async with aiohttp.ClientSession(base_url=url) as session:
        print(f"Running health check for server at {url}")
        async with session.get(
            "/health", timeout=ClientTimeout(total=test_timeout - 1 * MINUTES)
        ) as resp:
            up = resp.status == 200
        assert up, f"Failed health check for server at {url}"
        print(f"Healthy: {url}")

        print(f"Sending test prompt to {url}:")
        await _send_request(session, "gemma-4-31b", messages)


async def _send_request(
    session: aiohttp.ClientSession, model: str, messages: list[dict[str, str]]
) -> None:
    payload: dict[str, Any] = {
        "messages": messages,
        "model": model,
        "stream": True,
    }
    payload["chat_template_kwargs"] = {"enable_thinking": True}

    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    async with session.post(
        "/v1/chat/completions", json=payload, headers=headers
    ) as resp:
        async for raw in resp.content:
            resp.raise_for_status()
            line = raw.decode().strip()
            if not line or line == "data: [DONE]":
                continue
            if line.startswith("data: "):
                line = line[len("data: "):]

            chunk = json.loads(line)
            assert chunk["object"] == "chat.completion.chunk"
            delta = chunk["choices"][0]["delta"]
            content = (
                delta.get("content")
                or delta.get("reasoning")
                or delta.get("reasoning_content")
            )
            if content:
                print(content, end="")
            else:
                print("\n", chunk)
    print()
