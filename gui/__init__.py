"""
Temporary compatibility shim for gui imports.
This will be removed in the next release.
"""

import warnings
warnings.warn(
    "Import 'gui' is deprecated; use 'srt_translator.gui'. "
    "This compatibility shim will be removed in the next release.",
    DeprecationWarning,
    stacklevel=2
)

# Import everything from the new location
from srt_translator.gui import *  # noqa
