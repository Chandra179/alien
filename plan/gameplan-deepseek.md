
# Alien Obfuscator — HuggingFace Build Small Hackathon Plan

## Concept

An alien intelligence monitors all human communications. Resistance fighters encode messages as riddles drawn from ancient Earth texts — texts the alien cannot understand because they require *cultural context*, not decryption. The alien *sees* the riddle but can't *get* it. Humans can.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                    Gradio App                         │
│                                                       │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────┐  │
│  │  ENCRYPT    │   │    SOLVE     │   │  GAME     │  │
│  │  (Create)   │   │  (Decrypt)   │   │ (Timed)   │  │
│  └──────┬──────┘   └──────┬───────┘   └─────┬─────┘  │
│         │                 │                  │        │
│  ┌──────┴─────────────────┴──────────────────┴──────┐  │
│  │              Riddle Generator (LLM)              │  │
│  │    Prompt + Corpus Excerpt → Riddle + 5 MCQs     │  │
│  └────────────────────────┬────────────────────────┘  │
│                           │                           │
│  ┌────────────────────────┴────────────────────────┐  │
│  │              Corpus Manager                      │  │
│  │  Greek Myth │ Shakespeare │ Grimm │ Poetry │ ... │  │
│  └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## Functional Requirements

### FR-1: Encrypt Mode (Create a Riddle)

**FR-1.1** User inputs a plaintext message (≤100 characters recommended, no hard limit but prompt warns if too long).

**FR-1.2** User selects a source text theme from:
- Greek / Roman Mythology
- Shakespeare
- Grimms' Fairy Tales / Folklore
- Classic Poetry
- Chinese Classics
- *Surprise Me* (randomly selected theme)

**FR-1.3** On clicking "Encrypt", the system:
1. Selects a random excerpt from the chosen theme's corpus (1-2 snippets, ~500 chars each)
2. Constructs a prompt that includes: the source text excerpt(s), the plaintext message, and formatting instructions
3. Calls the LLM to generate a riddle + 5 answer options
4. Returns a structured JSON: `{riddle, options: [5 strings], correct_index: 0-4, theme}`
5. Displays the riddle beautifully in the UI

**FR-1.4** If the LLM response fails to parse as valid JSON, retry once with a stricter prompt. If still failing, show a friendly error with a "try again" button.

**FR-1.5** The generated riddle is presented in a "shareable card" format (styled HTML/Text block) that the user can copy and send anywhere (Discord, WhatsApp, etc.). The card includes:
- The riddle text
- The 5 options (shuffled; correct answer visible to sender for verification)
- A note: "Can you decipher this before the alien does?"

**FR-1.6** A "Copy to Clipboard" button copies the entire riddle card as formatted text.

**FR-1.7** The sender sees the correct answer clearly marked after generation, so they can verify the riddle makes sense before sharing.

### FR-2: Solve Mode (Decrypt a Friend's Riddle)

**FR-2.1** User pastes a shared riddle text (or enters it manually into a text area).

**FR-2.2** App parses the riddle + 5 options from the pasted text and presents them as clickable MCQ buttons.

**FR-2.3** User picks an answer → immediate feedback:
- Correct: Celebration animation/effect, message revealed
- Wrong: Strike indicator, allowed to retry (unlimited attempts, but attempt count is tracked for fun stats).

**FR-2.4** After solving, user sees the original plaintext message.

**FR-2.5** "Decrypt another?" button to clear and start fresh.

### FR-3: Timed Game Mode

**FR-3.1** A "Challenge Mode" separate tab where the app auto-generates riddles from random themes and random plaintext concepts (sourced from a "message bank" — a curated list of common phrases, proverbs, idioms, and concepts drawn from the same source texts).

**FR-3.2** Each round presents one riddle + 5 options. The player has 10 minutes (default, configurable) to solve as many as possible.

**FR-3.3** Timer is visible and counts down. When timer hits zero, game ends and final score is shown.

**FR-3.4** Scoring:
- +10 points per correct answer
- +5 bonus points for answering in under 15 seconds
- +3 point streak bonus (multiplied by consecutive correct streak: 0, 3, 6, 9...)
- No penalty for wrong answers (keeps it fun, not punishing)

**FR-3.5** "New Game" button at the end. High score persisted in browser localStorage.

**FR-3.6** Game configuration (before starting):
- Time limit slider (1–30 minutes, default 10)
- Theme filter (pick specific themes or "All")
- Number of riddles (unlimited by default, or capped at e.g. 20)

### FR-4: Alien Narrative Wrapper

**FR-4.1** The whole app has a dark, sci-fi aesthetic with an "alien invasion" framing.

**FR-4.2** An "Alien Threat Monitor" element somewhere in the UI — purely cosmetic, shows the alien "scanning" with fake activity/glitch effects.

**FR-4.3** In Encrypt mode: flavor text like "Message scrambled. The alien will see gibberish."

**FR-4.4** In Game mode: flavor text like "The alien is listening. How many can you get past it?"

**FR-4.5** Alien defeat/surprise reaction when player does well (e.g., "ALIEN CONFUSION DETECTED — IT CANNOT PARSE CULTURAL CONTEXT").

### FR-5: Modular LLM Backend

**FR-5.1** All LLM calls go through a single `generate(prompt)` function that abstracts the backend.

**FR-5.2** Support for at least two backends, selectable via config/env:
- Hugging Face Inference API (serverless)
- Local Transformers pipeline (for running on GPU Spaces)
- Extensible to add more (OpenAI-compatible APIs, etc.)

**FR-5.3** The prompt template is parameterized — swapping models should only require adjusting the prompt format, not the core logic.

**FR-5.4** All generated riddle JSON is validated with a schema before being returned to the UI.

---

## Non-Functional Requirements

### NFR-1: Performance
- Riddle generation should return within 10–15 seconds (Inference API) or 5–10 seconds (local GPU).
- Show a loading animation/spinner during generation to hide latency.
- Pre-warm the model on Space startup if using local inference.

### NFR-2: Polish
- Gradio app must look intentionally styled, not default Gradio.
- Custom CSS — dark theme, sci-fi fonts, glitch effects.
- Responsive layout (works on desktop and mobile browsers).
- Smooth transitions between modes.

### NFR-3: Robustness
- Graceful handling of LLM errors (timeouts, malformed JSON, rate limits).
- Retry logic with exponential backoff for API calls.
- Input validation (empty messages, very long messages, pasting invalid riddle text).

### NFR-4: Hackathon-Ready Deliverables
- App runs as a Hugging Face Space (Gradio SDK).
- `requirements.txt` pinned to exact versions.
- Demo video script/storyboard (to be filmed after build).
- Social media post draft (to be posted with demo).
- `README.md` with: description, how to run, how to play.

---

## Corpus Content Plan

Each theme contains 8–12 curated excerpts (200–800 characters each) from public domain works. Each excerpt is a self-contained nugget of wisdom, a vivid scene, or a memorable phrase — perfect fodder for a riddle.

| Theme | Source Texts | Example Content |
|-------|-------------|-----------------|
| Greek/Roman Myth | Ovid's Metamorphoses, Homeric Hymns, Bullfinch's Mythology | "Icarus flew too close to the sun..." |
| Shakespeare | Hamlet, Macbeth, A Midsummer Night's Dream, Sonnets | "To thine own self be true..." |
| Grimms' Fairy Tales | Household Tales, Hans Christian Andersen | "Mirror mirror on the wall..." |
| Classic Poetry | Emily Dickinson, William Blake, Walt Whitman | "Because I could not stop for Death..." |
| Chinese Classics | Sun Tzu's Art of War, Tao Te Ching, Analects | "The supreme art of war is to subdue the enemy without fighting." |

**Message Bank** (plaintext concepts to auto-riddle in game mode) — 30–50 items like:
"patience is a virtue", "don't count your chickens", "a rolling stone gathers no moss",
"the lion's share", "Achilles' heel", "Pandora's box", "star-crossed lovers", etc.

---

## Prompt Engineering Strategy

### System Prompt

```
You are a mischievous alien archaeologist who has spent centuries studying ancient
human texts. You craft riddles in the voice of [THEME_DESCRIPTION].

Generate a riddle whose ANSWER is: [PLAINTEXT]

Rules:
- The riddle must be solvable by a human familiar with [THEME_NAME], but confusing
  to anyone without cultural context.
- The riddle should be 2–4 sentences, poetic, and contain at least one clever twist.
- Generate exactly 5 answer options: 1 correct (the PLAINTEXT itself), 4 plausible distractors.
- Distractors should be thematically adjacent (same domain, same era, similar concepts).
- Output ONLY valid JSON.
```

### Expected Output Format

```json
{
  "riddle": "string (2-4 sentences)",
  "options": ["correct_answer", "distractor1", "distractor2", "distractor3", "distractor4"],
  "correct_index": 0,
  "theme": "greek_myth"
}
```

Note: The options array is always shuffled so the correct answer appears in a random position. The `correct_index` tells us which one it is. The UI displays them in a fixed A-E order.

---

## Gradio UI Layout

```
┌──────────────────────────────────────────────┐
│        [ALIEN OBFUSCATOR v1.0]               │
│    [Encrypt] [Solve] [Challenge] [About]      │  ← Tabs
├──────────────────────────────────────────────┤
│                                               │
│  ┌─────────────────────────────────┐  ┌────┐ │
│  │ Message to encrypt:             │  │    │ │  ← Alien monitor
│  │ [_____________________________] │  │ 👽  │ │     (sidebar)
│  │                                 │  │    │ │
│  │ Theme: [dropdown ▼]            │  │    │ │
│  │                                 │  │    │ │
│  │       [ENCRYPT]                │  │    │ │
│  └─────────────────────────────────┘  └────┘ │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │           GENERATED RIDDLE               │  │
│  │  ┌─────────────────────────────────┐    │  │
│  │  │ "I am the heel that doomed a    │    │  │
│  │  │  hero, the box that scattered   │    │  │
│  │  │  hope..."                       │    │  │
│  │  └─────────────────────────────────┘    │  │
│  │                                         │  │
│  │  A) Achilles' weakness                  │  │
│  │  B) Sisyphus' boulder                   │  │
│  │  C) Pandora's curiosity  ← correct      │  │
│  │  D) Icarus' ambition                    │  │
│  │  E) Hercules' madness                   │  │
│  │                                         │  │
│  │     [Copy to Clipboard]                 │  │
│  └─────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

---

## File Structure

```
alien-obfuscator/
├── app.py                  # Gradio UI (tabs, layout, CSS)
├── config.py               # Constants, model settings, paths
├── corpus/
│   ├── __init__.py
│   ├── manager.py          # Loads, selects, caches excerpts
│   ├── greek_myth.txt      # Curated excerpts
│   ├── shakespeare.txt
│   ├── grimm.txt
│   ├── poetry.txt
│   └── chinese_classics.txt
├── riddle_generator.py     # Prompt builder + LLM abstraction
├── game_engine.py          # Timer, scoring, game state
├── ui_components.py        # Reusable Gradio blocks (riddle card, timer, etc.)
├── utils.py                # Clipboard, JSON validation, retry
├── requirements.txt
├── README.md
└── assets/
    └── custom.css          # Dark sci-fi theme
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| LLM generates incorrect JSON | Schema validation + retry (up to 2) + fallback error message |
| LLM hallucinates wrong answer | The correct answer IS the plaintext — we force it in the JSON by construction; only distractors are creative |
| HF Inference API slow/cold-start | Use local Transformers + quantized model if on GPU Space; pre-warm on startup |
| Gradio limits for real-time timer | Use JavaScript injection for client-side countdown; server validates final time |
| Sharing riddles via copy-paste is fragile | Provide both "Copy Card" (formatted) and optional URL-encoded share link |

---

## Hackathon Timeline (Suggested)

| Phase | What | Time |
|-------|------|------|
| Hour 0–2 | Set up HF Space, Gradio skeleton, corpus loading, LLM backend | Foundation |
| Hour 2–5 | Build Encrypt tab: prompt engineering, riddle generation, riddle display | Core Feature 1 |
| Hour 5–8 | Build Solve tab: paste parser, MCQ UI, feedback animations | Core Feature 2 |
| Hour 8–12 | Build Challenge Mode: game engine, timer, scoring, config | Core Feature 3 |
| Hour 12–14 | Polish: CSS theming, alien aesthetic, animations, flavor text | Delight |
| Hour 14–16 | Testing, bug fixes, edge cases, error handling | Robustness |
| Hour 16–18 | Demo video + social post + README | Submission |

---

## Model Target

- **Primary**: Gemma 4 31B (≤32B limit)
- **Fallback**: Gemma 4 26B-A4B (MoE, lower VRAM)
- Code is modular — swap model via config/env variable.

---

## Decisions Made

1. The riddle **IS** the encryption. Solving the riddle *is* decrypting. No separate cipher layer.
2. The LLM generates the riddle + 1 correct answer + 4 plausible distractors (5 total MCQ options).
3. The LLM composes riddles using random excerpts from a curated public domain corpus (hybrid approach — real texts used as creative springboard).
4. Corpus themes: Greek/Roman Mythology, Shakespeare, Grimms' Fairy Tales, Classic Poetry, Chinese Classics. No religious texts.
5. Sender sees the correct answer highlighted after generation for verification.
6. Solver gets unlimited retry attempts on a friend's riddle; attempt count tracked for fun.
7. Challenge mode: 10-minute default timer, customizable 1–30 minutes.
8. Sharable riddle format: copy-paste text card. URL-encoded share link as stretch goal.
9. High scores persisted in localStorage (stateless, no database needed).
