"""Fallout / RobCo Terminal UI theme constants for the Alien Obfuscator.

This module holds CSS stylesheets, JavaScript timer/state snippets, and
font-loading HTML that together produce the retro terminal aesthetic.
"""

# ---------------------------------------------------------------------------
# JavaScript timer & localStorage bridge
# ---------------------------------------------------------------------------

TIMER_HTML = """
<script>
(function() {
    function findTimerInput() {
        var el = document.getElementById('timer-display');
        if (!el) return null;
        return el.querySelector('input, textarea');
    }

    window.startGameTimer = function(durationSeconds) {
        window.gameEndTime = Date.now() + durationSeconds * 1000;
        window.riddleStartTime = Date.now();
        if (window.gameTimerInterval) {
            clearInterval(window.gameTimerInterval);
        }

        function updateTimer() {
            var remainingMs = Math.max(0, window.gameEndTime - Date.now());
            var remainingSec = Math.floor(remainingMs / 1000);
            var minutes = Math.floor(remainingSec / 60);
            var seconds = remainingSec % 60;
            var timeStr = (minutes < 10 ? '0' : '') + minutes + ':' + (seconds < 10 ? '0' : '') + seconds;

            var timerInput = findTimerInput();
            if (timerInput) {
                timerInput.value = timeStr;
            }

            if (remainingMs <= 0) {
                clearInterval(window.gameTimerInterval);
                var btn = document.getElementById('game-over-trigger');
                if (btn) {
                    btn.click();
                }
            }
        }

        updateTimer();
        window.gameTimerInterval = setInterval(updateTimer, 500);
    };

    window.stopGameTimer = function() {
        if (window.gameTimerInterval) {
            clearInterval(window.gameTimerInterval);
        }
    };

    window.readGameState = function() {
        return {
            score: parseInt(localStorage.getItem('game_score') || '0'),
            streak: parseInt(localStorage.getItem('game_streak') || '0'),
            time_left: parseInt(localStorage.getItem('game_time_left') || '0'),
            correct_index: parseInt(localStorage.getItem('game_correct_index') || '0'),
            theme: localStorage.getItem('game_theme') || 'All',
            riddle_start_time: parseInt(localStorage.getItem('game_riddle_start_time') || '0'),
            active: localStorage.getItem('game_active') === 'true'
        };
    };

    window.writeGameState = function(st) {
        for (var key in st) {
            localStorage.setItem('game_' + key, String(st[key]));
        }
    };
})();
</script>
"""

# ---------------------------------------------------------------------------
# Main Fallout / RobCo terminal CSS
# ---------------------------------------------------------------------------

FALLOUT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');

:root {
    --terminal-color: #33ff33;
    --terminal-color-glow: rgba(51, 255, 51, 0.8);
    --terminal-color-glow-low: rgba(51, 255, 51, 0.5);
    --terminal-color-glow-container: rgba(51, 255, 51, 0.25);
    --terminal-color-glow-container-outer: rgba(51, 255, 51, 0.15);
    --terminal-bg-glow: #0d1f0d;
    --terminal-bg: #030703;
    --terminal-placeholder: #1a5c1a;
    --terminal-disabled-bg: #010301;
    --terminal-disabled-color: #114411;
    --terminal-border-dim: #22aa22;
}

/* Apply VT323 retro font and scanline styles to all components */
body, .gradio-container, .gradio-container * {
    font-family: 'VT323', 'Courier New', Courier, monospace !important;
    font-size: 1.25rem !important;
    border-radius: 0px !important;
    box-shadow: none !important;
    line-height: 1.3 !important;
}

body {
    background-color: var(--terminal-bg) !important;
    color: var(--terminal-color) !important;
    margin: 0;
    padding: 0;
}

/* Subtle scanlines overlay simulating CRT screen */
body::before {
    content: " ";
    display: block;
    position: fixed;
    top: 0; left: 0; bottom: 0; right: 0;
    background: linear-gradient(
        rgba(18, 16, 16, 0) 50%,
        rgba(0, 0, 0, 0.22) 50%
    );
    background-size: 100% 4px;
    z-index: 99999;
    pointer-events: none;
}

/* Container framing with classic terminal border and CRT glow */
.gradio-container {
    background-color: var(--terminal-bg) !important;
    border: 3px solid var(--terminal-color) !important;
    box-shadow: 0 0 25px var(--terminal-color-glow-container) inset, 0 0 15px var(--terminal-color-glow-container-outer) !important;
    max-width: 950px !important;
    margin: 40px auto !important;
    padding: 25px !important;
}

/* Headers with glow effects */
h1, h2, h3, h4, h5, h6 {
    color: var(--terminal-color) !important;
    text-shadow: 0 0 8px var(--terminal-color-glow) !important;
    font-weight: bold !important;
    text-transform: uppercase !important;
}
h1 { font-size: 2.4rem !important; }
h2 { font-size: 1.9rem !important; }
h3 { font-size: 1.6rem !important; }

/* Plain text and label adjustments */
p, span, li {
    color: var(--terminal-color) !important;
    text-shadow: 0 0 3px var(--terminal-color-glow-low) !important;
}

/* Flat solid terminal panels for all Gradio blocks */
.block, .form, .panel, .gr-box, .gr-panel, .gr-block {
    background-color: #000000 !important;
    border: 1px solid var(--terminal-color) !important;
    padding: 15px !important;
    margin-bottom: 12px !important;
}

/* Text Inputs, textareas, and select menus */
input, textarea, select, .gr-input, .gr-textarea {
    background-color: #000000 !important;
    color: var(--terminal-color) !important;
    border: 1px solid var(--terminal-color) !important;
    font-family: 'VT323', monospace !important;
    padding: 8px !important;
    text-shadow: 0 0 3px var(--terminal-color-glow-low) !important;
}
input::placeholder, textarea::placeholder {
    color: var(--terminal-placeholder) !important;
    text-shadow: none !important;
}
input:focus, textarea:focus, select:focus {
    border-color: var(--terminal-color) !important;
    box-shadow: 0 0 10px var(--terminal-color-glow) !important;
    outline: none !important;
}

/* Dropdown menus & wrappers */
.dropdown-menu, .options, .select-wrap, .dropdown, select {
    background-color: #000000 !important;
    color: var(--terminal-color) !important;
    border: 1px solid var(--terminal-color) !important;
}

/* Retro buttons with glowing hover state */
button, .gr-button {
    background-color: var(--terminal-bg-glow) !important;
    color: var(--terminal-color) !important;
    border: 1px solid var(--terminal-color) !important;
    text-transform: uppercase !important;
    font-weight: bold !important;
    font-family: 'VT323', monospace !important;
    padding: 8px 16px !important;
    cursor: pointer !important;
    transition: all 0.15s ease-in-out !important;
    text-shadow: 0 0 3px var(--terminal-color-glow-low) !important;
}
button:hover, .gr-button:hover {
    background-color: var(--terminal-color) !important;
    color: #000000 !important;
    box-shadow: 0 0 12px var(--terminal-color-glow) !important;
    text-shadow: none !important;
}
button:disabled, .gr-button:disabled {
    background-color: var(--terminal-disabled-bg) !important;
    color: var(--terminal-disabled-color) !important;
    border-color: var(--terminal-disabled-color) !important;
    cursor: not-allowed !important;
    text-shadow: none !important;
}

/* Tab bar customization */
.tab-nav, [role="tablist"], .tabs {
    border-bottom: 2px solid var(--terminal-color) !important;
    background-color: #000000 !important;
    margin-bottom: 15px !important;
}
.tab-nav button, [role="tab"], .tabs button {
    background-color: transparent !important;
    color: var(--terminal-border-dim) !important;
    border: none !important;
    font-size: 1.5rem !important;
    padding: 10px 18px !important;
}
.tab-nav button:hover, [role="tab"]:hover, .tabs button:hover {
    color: var(--terminal-color) !important;
}
.tab-nav button.selected, [aria-selected="true"], .tabs button.selected, .tabitem.selected {
    color: var(--terminal-color) !important;
    border: 1px solid var(--terminal-color) !important;
    border-bottom: 1px solid var(--terminal-bg) !important;
    background-color: var(--terminal-bg-glow) !important;
    text-shadow: 0 0 6px var(--terminal-color-glow) !important;
}

/* Header style specifically for terminal branding */
.terminal-header {
    border-bottom: 2px dashed var(--terminal-color) !important;
    margin-bottom: 20px !important;
    padding-bottom: 10px !important;
}
.terminal-header-text {
    font-family: 'VT323', monospace !important;
    color: var(--terminal-color) !important;
    text-shadow: 0 0 5px var(--terminal-color-glow) !important;
    line-height: 1.2 !important;
    white-space: pre;
}

/* Text labels on panels and widgets */
.block-label, .gr-block-label, label, label span {
    background-color: #000000 !important;
    color: var(--terminal-color) !important;
    font-family: 'VT323', monospace !important;
    text-transform: uppercase !important;
    font-weight: bold !important;
}

/* Custom styles for checkboxes and radios */
.gr-radio, input[type="radio"], input[type="checkbox"] {
    accent-color: var(--terminal-color) !important;
}
.gr-radio label, .radio-group label {
    border: 1px solid var(--terminal-border-dim) !important;
    color: var(--terminal-border-dim) !important;
    background-color: #000000 !important;
}
.gr-radio label.selected, .radio-group label.selected {
    border-color: var(--terminal-color) !important;
    color: var(--terminal-color) !important;
    background-color: var(--terminal-bg-glow) !important;
    text-shadow: 0 0 4px var(--terminal-color-glow-low) !important;
}

/* Inner elements for custom look */
.copy-btn, button.svelte-custom {
    background-color: var(--terminal-bg-glow) !important;
    border: 1px solid var(--terminal-color) !important;
    color: var(--terminal-color) !important;
}

"""

# ---------------------------------------------------------------------------
# Google Font preconnect / load
# ---------------------------------------------------------------------------

GOOGLE_FONT_HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
"""

# ---------------------------------------------------------------------------
# Inline CSS used inside the Gradio Blocks constructor
# ---------------------------------------------------------------------------

DISABLED_RADIO_CSS = """
input[type="radio"]:disabled {
    opacity: 0.35;
}
"""
