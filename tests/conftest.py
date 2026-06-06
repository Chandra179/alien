"""Pytest configuration and shared fixtures.

This module adds the ``src/`` directory to ``sys.path`` so that test files can
import ``alien_obfuscator`` without needing to install the package.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
