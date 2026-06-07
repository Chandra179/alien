# Alien Obfuscator — Build Todo

## Phase 0: Foundation
- [x] Create todo.md tracker
- [x] Scaffold project structure (corpus/, assets/, tests/)
- [x] Write requirements.txt with pinned versions
- [x] Write config.py (model settings, paths, constants)
- [x] Implement corpus/manager.py + 5 theme text files
- [x] Write riddle_generator.py with LLM abstraction layer
- [x] Add mock LLM backend for offline testing
- [x] Write unit tests for corpus loading and prompt templating

## Phase 1: Encrypt Mode
- [x] Build Gradio Encrypt tab (message input + theme dropdown)
- [x] Implement prompt builder (corpus excerpt + plaintext + formatting)
- [x] Add JSON response parser + schema validation
- [x] Implement retry logic for malformed JSON
- [x] Build riddle card display (riddle + 5 options + correct answer)
- [x] Add "Copy to Clipboard" button
- [x] Test end-to-end with mock LLM

## Phase 2: Solve Mode
- [x] Build Gradio Solve tab (paste text area)
- [x] Implement riddle parser from pasted text
- [x] Build MCQ UI with clickable buttons
- [x] Add correct/wrong feedback animations
- [x] Display original plaintext after solving
- [x] Add "Decrypt another?" reset button
- [x] Test with hardcoded riddle data

## Phase 3: Challenge Mode
- [x] Build game_engine.py (timer, scoring, streaks)
- [x] Add game configuration UI (time slider, theme filter, riddle count)
- [x] Implement countdown timer (real-time `gr.Timer` tick every second, auto game-over at 0)
- [x] Build scoring system (+10 base, +5 speed bonus, +3 streak bonus)
- [x] Add high score persistence (localStorage)
- [x] Test with mocked riddle generator
- [ ] Fix game timer not counting down when the browser's tab is not active.

## Phase 4: Polish & Integration
- [x] Add custom CSS (dark sci-fi theme, alien monitor)
- [x] Implement Alien Threat Monitor cosmetic element
- [x] Add flavor text across all modes
- [x] Wire real LLM backend into all three modes
- [x] Add timeout guards + fallback error messages
- [x] Test mobile responsiveness (CSS media queries for <768px, stacked columns, full-width buttons)
- [x] Write README.md
- [ ] Record demo video + social post

## Phase 5: Final Checks
- [x] Run full test suite (make test) — 29/29 passing
- [x] Run lint + type check (make lint, make ty)
- [x] Verify parameter budget in README
- [ ] Deploy to Hugging Face Space
- [ ] Submit demo + social post
