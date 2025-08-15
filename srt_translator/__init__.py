"""
SRT Translator Package

A tool for translating SRT subtitle files using AI services.
"""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("srt-translator")
except PackageNotFoundError:
    __version__ = "1.0.0"
