"""Emplacements des données, partagés par le lancement et les contrôles portables."""
from pathlib import Path
import plistlib
import sys

from gardeplan.macos_paths import is_translocated_path, original_bundle_path

PORTABLE_MARKER = "portable.mode"
DATA_FOLDER = "donnees"


def portable_root(*, force=False, executable=None, frozen=None, source_root=None):
    """Le marqueur reste à côté du .exe ou du .app, jamais dans un bundle signé."""
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if frozen:
        binary = Path(executable or sys.executable).resolve()
        root = binary.parent
        for parent in binary.parents:
            if parent.suffix.casefold() == ".app":
                root = parent.parent
                if is_translocated_path(parent):
                    original = original_bundle_path(parent)
                    if original is not None and original.name == parent.name and (original.parent / PORTABLE_MARKER).is_file():
                        root = original.parent
                try:
                    with (parent / "Contents" / "Info.plist").open("rb") as handle:
                        if plistlib.load(handle).get("PlanificateurPortable") is True:
                            return root
                except (OSError, ValueError, plistlib.InvalidFileException):
                    pass
                break
    else:
        root = Path(source_root or Path(__file__).resolve().parent.parent).resolve()
    return root if force or (root / PORTABLE_MARKER).is_file() else None


def database_path(normal_directory, *, database=None, example=False, force_portable=False,
                  executable=None, frozen=None, source_root=None, portable_directory=None):
    if database is not None:
        return Path(database).expanduser().resolve()
    root = (Path(portable_directory).resolve() if portable_directory is not None else
            portable_root(force=force_portable, executable=executable,
                          frozen=frozen, source_root=source_root))
    folder = root / DATA_FOLDER if root is not None else Path(normal_directory)
    return (folder / ("exemple.sqlite" if example else "gardeplan.sqlite")).resolve()
