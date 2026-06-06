## Summary

This is a promising seed for *Thousand Token Wood*: the tension between an all-powerful digital adversary and fragile, analog human creativity is conceptually strong. However, to turn “Alien Obfuscator” from a premise into a shippable, joyful Gradio experience in a single weekend, we need to resolve several ambiguities in the gameplay loop, the cryptographic fiction, and the AI’s role. Below are targeted clarifying questions followed by a concrete, scoped implementation checklist.

---

## Section 1: Clarifying Questions

### A) Gameplay & User Experience

**Q1. Is the experience single-player or asymmetric two-player?**  
Will one user write a secret, receive a riddle, and then decode it themselves later (a creative toy), or is the app designed for a hot-seat / shareable link where a friend acts as the human decoder? This choice determines whether you need session persistence, a “passcode” sharing mechanic, or simply a copy-to-clipboard riddle.

**Q2. What is the exact turn-by-turn interaction flow?**  
Walk me through one full round: does the user type plaintext → the LLM generates a riddle → an “Alien AI” immediately attempts to crack it on-screen → the user sees a verdict? Or does a human recipient manually enter their guess into a second text box? Clarifying this flow is essential because it dictates how many Gradio components you need and where the dramatic pause lives.

**Q3. How do you define “winning” a round?**  
Is victory achieved when the human recipient successfully recovers the original message, when the Alien AI fails to guess it, when the generated riddle satisfies a hidden “poetry score,” or some combination? A clear win condition gives the user a reason to replay and provides you with a progress hook for the UI.

### B) Encryption & Narrative Logic

**Q4. Mechanically, how does the riddle function as encryption?**  
Is the plaintext literally the semantic answer to the riddle (meaning the generator LLM inherently knows the secret), or is the message hidden via a user-supplied passphrase that deterministically seeds a thematic cipher? If the riddle is pure paraphrase, the “encryption” is fictional rather than functional, which is fine—but you need to know which fiction you are selling.

**Q5. What prevents the Alien from solving its own generated riddle?**  
If the Alien is simulated by the same underlying model (or a clone with the same weights and prompts), it already “knows” the answer because it generated it. Will you introduce asymmetry through a private user passphrase that biases generation, or will the Alien be played by a separately prompted instance that is deliberately denied the passphrase or forced into a comically overconfident persona?

**Q6. Are the “ancient and pre-internet texts” retrieved or invented?**  
Do you plan to ground riddles in a real curated corpus (e.g., Project Gutenberg excerpts) via retrieval, or are they purely LLM-synthesized pastiches of ancient styles? If retrieval-based, how will you integrate a vector store without exceeding your weekend scope and parameter budget?

### C) Tone & Delight

**Q7. How will you reconcile a “dire situation” with joyful whimsy?**  
The track explicitly judges on delight. Will the tone be campy B-movie sci-fi—complete with a melodramatic Alien who rage-quits when stumped—rather than dystopian survival? The framing wrapper can turn grim lore into playful anachronism, but that choice needs to be intentional.

**Q8. In what way is the AI doing the fun thing, not just building the tool?**  
The rules state that the AI must be load-bearing for the experience. Beyond generating text, will the LLM embody a theatrical role—such as an Ancient Librarian who argues about meter, or an Alien Decoder that live-streams its flawed reasoning in a dramatic monologue? The model needs to be a performer, not just a compiler.

### D) Technical & Model Architecture

**Q9. Will you use one model with prompt switching or multiple models?**  
Do you plan to run a single small LLM (e.g., 7B–9B parameters) that swaps system prompts between the Ancient Scribe and the Alien Decoder, or will you run two separate smaller models (e.g., two 4B models) to maintain stricter narrative separation? This decision directly impacts your parameter budget and inference latency.

**Q10. Which specific model and serving stack fit under the 32B ceiling?**  
Which checkpoint are you leaning toward—*Qwen2.5-7B-Instruct*, *Llama-3.1-8B*, *Gemma-2-9B*, or another—and will you serve it via raw `transformers`, `vLLM`, or the Hugging Face Inference API inside the Gradio Space? You need to confirm that your total parameter count satisfies

$$
\sum_{i} P_i \;\leq\; 32 \times 10^{9}
$$

where $P_i$ is the parameter count of every load-bearing model (including any auxiliary embedders or classifiers).

---

## Section 2: Implementation Requirements

The checklist below is scoped for a single weekend. Treat each bullet as a binary deliverable: done or not done.

### Creative / Game Design

- **Finalize the narrative wrapper in one paragraph.** Write a campy backstory: the Alien Overlord “Decrypto” has hacked all digital signals, so the Resistance resorts to pre-internet poetic ciphers. Print this lore on the Gradio landing page to set expectations immediately.
- **Draft a Tone Bible (one page).** List allowed humor (anachronism, dramatic irony), forbidden topics (graphic violence, genuine warfare trauma), and a vocabulary glossary (e.g., “The Signal,” “The Codex,” “The Interceptor”). This prevents the LLM from drifting into grimdark territory during the demo.
- **Design the core loop as a four-phase state machine:**  
  1. **INPUT** — User enters plaintext and selects an ancient theme.  
  2. **ENCODING** — LLM Scribe generates a riddle.  
  3. **INTERCEPTION** — Alien AI attempts a decode.  
  4. **REVEAL** — Verdict screen shows human vs. alien success.  
  Map each phase to a distinct Gradio visibility state.
- **Freeze your system prompts.** Write and version-control the final prompts for the Ancient Scribe, Alien Decoder, and Arbiter personas. Test each with at least 10 diverse inputs to verify consistency and to catch prompt-injection risks.
- **Define scoring logic.** For example: *Human Victory* = Alien guess has cosine similarity $< 0.75$ to plaintext AND the human can recover the message; *Style Bonus* = riddle contains the chosen historical theme without repeating keywords from the secret.
- **Build a JSON fallback bank.** Hand-write 5 riddles covering common demo inputs (e.g., “Attack at dawn,” “I love you,” “Pizza is ready”). If the LLM timeouts during the demo, serve a fallback instantly.
- **Cap the input scope.** Limit plaintext to 10–20 words to keep generation latency under 5 seconds and to ensure the riddle remains coherent on a small model.

### Technical / Backend

- **Scaffold the Hugging Face Space.** Initialize the repo with Gradio SDK, a pinned `requirements.txt`, and a modular `app.py`. Do not rely on unpinned dependencies during a hackathon weekend.
- **Manage session state with `gr.State`.** Track the current phase, plaintext, generated riddle, and alien guess across button clicks without introducing a database.
- **Implement deterministic asymmetry (optional but recommended).** If using a user-supplied passphrase, hash it with a deterministic function (e.g., `hashlib.sha256`) and inject the hash as a random seed or thematic keyword into the Scribe prompt. Strip that seed from the Alien prompt so the same model cannot trivially reverse the riddle.
- **Add timeout guards.** Wrap every LLM call in a `try/except` with a 10–15 second timeout. On failure, seamlessly swap to the JSON fallback bank and flash a “Signal Interference” warning in the UI.
- **Create a community gallery endpoint.** Append successfully obfuscated riddles (with plaintext redacted) to a lightweight `gallery.json` or markdown file inside the Space so visitors immediately see the creative output of previous players.

### Model / AI

- **Select a single base model $\leq 9$B parameters.** Recommended candidates for instruction-following and creative writing: `Qwen2.5-7B-Instruct`, `Meta-Llama-3.1-8B-Instruct`, or `google/gemma-2-9b-it`. Staying well under the 32B limit leaves headroom for weekend experimentation and avoids container memory issues on HF Spaces.
- **Quantize aggressively.** Load the model in 4-bit (NF4 via `bitsandbytes` or AWQ) or 8-bit to fit inside a free-tier Space GPU/CPU. Verify the memory footprint in a Colab test notebook *before* Friday evening.
- **Choose the inference engine.** Use the `transformers` pipeline for simplicity; only upgrade to `vLLM` if you need batched generation for a separate Alien instance. Avoid TGI unless you have provisioned dedicated HF hardware.
- **Pipeline the two-step generation.** Step 1 generates the riddle (and stores the plaintext answer server-side in `gr.State` only). Step 2 sends *only* the riddle to the Alien Decoder persona to simulate interception, ensuring the decoder prompt never sees the original plaintext.
- **Add a lightweight semantic judge.** Use a small sentence-transformer embedder (e.g., `all-MiniLM-L6-v2`) to compare the Alien’s guess against the original plaintext. The embedder is only tens of millions of parameters, so it does not threaten the 32B budget.
- **Document the parameter budget in the README.** Explicitly state: *Primary LLM = 7B parameters; Embedder judge = 22M parameters; Total = 7.022B $\leq$ 32B limit.*

### Gradio / UI Polish

- **Theme the interface with custom CSS.** Use a dark “transmission” aesthetic (monospace amber text, faint CRT scanlines) for the military side; a parchment texture with serif fonts for the riddle reveal; and a glitchy neon-green terminal for the Alien intercept screen. Consistent visual storytelling is a judging criterion.
- **Use a stepped wizard layout, not a chatbot.** Control visibility with `gr.Column(visible=...)` or `gr.Tab` so the user is guided through Encode → Intercept → Decode without cognitive overload.
- **Add micro-interactions.** Include a “Poetry Meter” progress bar while the Scribe writes, a “Panic Scramble” animation if the Alien wins, and copy-to-clipboard buttons for the riddle and a shareable markdown snippet.
- **Provide instant-play examples.** Pre-load 3 buttons with sample secrets so judges can experience the delight without typing.
- **Ensure mobile responsiveness.** Test `gr.Row` and `gr.Column` scaling on a phone browser Sunday morning; vertical layouts often demo better on social media.
- **Polish error states.** If the model fails, show a diegetic message such as *“The Codex is too dusty to read… switching to emergency analog backup.”* Never expose a raw Python traceback to the user.

### Demo & Social / Video

- **Script a 45-second demo video.** Structure it as: Hook (5s: “The Aliens hacked our language models!”), Setup (10s: user types a mundane secret), Twist (15s: the LLM transforms it into a bizarre ancient riddle), Climax (10s: the Alien AI confidently guesses something absurdly wrong), Payoff (5s: human victory screen). Record with OBS or Loom at 1080p.
- **Produce a vertical 15-second social cut.** Export a fast-paced MP4 (≤ 20 MB) for Twitter/X or LinkedIn: quick cuts of the UI, a funny Alien failure line, and the final riddle reveal.
- **Write the social-media post copy.** Draft a 280-character hook plus a thread with the Space URL, a screenshot of the funniest generated riddle, and the hashtags `#BuildSmallHackathon` and `@huggingface`.
- **Polish the README.** Include a one-paragraph elevator pitch, an embedded GIF of the demo, a “How to Play” section, a model-card reference, and a prominent “Try it Live” badge linking to the Space.
- **Prepare a 2-minute director’s commentary.** Write a short voiceover script explaining why the AI is load-bearing (the Alien is a character, not a tool) in case judges ask for a walkthrough on Discord or during office hours.

---

> **Core Insight:** The winning version of this idea is less about realistic cryptography and more about theatrical asymmetry. If the LLM is simultaneously the Ancient Poet *and* the bumbling Alien antagonist, the joy comes from watching the same small model defeat itself with style. Nail that performance, wrap it in a polished three-step Gradio wizard, and you will have a genuinely delightful demo.

Good luck shipping it—now go make that Alien rage-quit in iambic pentameter.