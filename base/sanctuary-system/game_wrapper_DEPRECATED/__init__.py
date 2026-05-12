"""DEPRECATED: game_wrapper has moved to sanctuary-revolution.

Import from sanctuary_revolution instead:

    from sanctuary_revolution import PAIAHarness, HarnessConfig, EventRouter
    from sanctuary_revolution import CourseState, OmnisancPhase, get_phase

This directory is kept for historical reference only.
"""

import warnings
warnings.warn(
    "game_wrapper has moved to sanctuary_revolution.harness. "
    "Import from sanctuary_revolution instead.",
    DeprecationWarning,
    stacklevel=2
)
