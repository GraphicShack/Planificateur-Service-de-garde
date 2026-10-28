"""Locate a bundle's original path without changing macOS security settings.

Security.framework owns the mapping from AppTranslocation to the downloaded
bundle. Its lookup is optional: if unavailable, startup asks the user to locate
the portable folder rather than guessing a path or using an unrelated database.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys


def is_translocated_path(path: Path) -> bool:
    parts = Path(path).parts
    return any(parts[i] == "AppTranslocation" and parts[i + 2] == "d"
               for i in range(len(parts) - 2))


def original_bundle_path(bundle: Path) -> Path | None:
    """Return only the original path provided by macOS, or None on failure."""
    if sys.platform != "darwin":
        return None
    references = []
    core = None
    try:
        core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        core.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                                                ctypes.c_long, ctypes.c_bool]
        core.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        core.CFURLGetFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_bool,
                                                         ctypes.c_void_p, ctypes.c_long]
        core.CFURLGetFileSystemRepresentation.restype = ctypes.c_bool
        core.CFRelease.argtypes = [ctypes.c_void_p]
        core.CFRelease.restype = None
        security.SecTranslocateCreateOriginalPathForURL.argtypes = [ctypes.c_void_p,
                                                                  ctypes.POINTER(ctypes.c_void_p)]
        security.SecTranslocateCreateOriginalPathForURL.restype = ctypes.c_void_p
        encoded = os.fsencode(bundle)
        url = core.CFURLCreateFromFileSystemRepresentation(None, encoded, len(encoded), True)
        if not url:
            return None
        references.append(url)
        error = ctypes.c_void_p()
        original = security.SecTranslocateCreateOriginalPathForURL(url, ctypes.byref(error))
        if error.value:
            references.append(error.value)
        if not original:
            return None
        references.append(original)
        buffer = ctypes.create_string_buffer(32768)
        if not core.CFURLGetFileSystemRepresentation(original, True, buffer, len(buffer)):
            return None
        result = Path(os.fsdecode(buffer.value)).resolve()
        return result if result != bundle.resolve() and result.is_dir() else None
    except (OSError, AttributeError, ValueError):
        return None
    finally:
        if core is not None:
            for reference in reversed(references):
                core.CFRelease(reference)
