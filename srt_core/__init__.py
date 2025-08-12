"""
Temporary compatibility shim for srt_core imports.
This will be removed in the next release.
"""

import warnings
warnings.warn(
    "Import 'srt_core' is deprecated; use 'srt_translator.core'. "
    "This compatibility shim will be removed in the next release.",
    DeprecationWarning,
    stacklevel=2
)

# Import everything from the new location
from srt_translator.core import *  # noqa
