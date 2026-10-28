"""Publish only portable archives whose native, extracted-binary checks passed.

Runs on the release runner; never downloads dependencies or changes user data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile


def prepare(source: Path, destination: Path, version: str) -> list[Path]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Version invalide")
    required_checks = (
        "qt_application", "coverage_and_exact_minutes", "sqlite_save_reopen_backup",
        "dashboard_day_and_week", "pdf_export_preview_print_modules",
        "ortools_cp_sat_generation", "offline_operations", "portable_data_write",
    )
    validated = []
    for folder, platform, report_name, archive_name, executable in (
        ("windows", "windows", "portable-archive.json", "Planificateur-SDG-Portable.zip", "Planificateur-SDG.exe"),
        ("macos", "cocoa", "macos-portable-archive.json", f"Planificateur-SDG-{version}-macOS-arm64-Portable.zip", "Planificateur-SDG.app/Contents/MacOS/Planificateur-SDG"),
    ):
        root = source / folder
        reports = list(root.rglob(report_name))
        archives = list(root.rglob(archive_name))
        if len(reports) != 1 or len(archives) != 1:
            raise ValueError(f"Archive ou rapport manquant/ambigu pour {folder}")
        report = json.loads(reports[0].read_text(encoding="utf-8-sig"))
        if any(report.get(key) is not True for key in ("success", "frozen", "portable_mode")):
            raise ValueError(f"Contrôle portable échoué : {folder}")
        if report.get("version") != version or report.get("qt_platform") != platform:
            raise ValueError(f"Version ou plateforme incorrecte : {folder}")
        if any(report.get("checks", {}).get(key) is not True for key in required_checks):
            raise ValueError(f"Contrôle natif incomplet : {folder}")
        with zipfile.ZipFile(archives[0]) as archive:
            names = set(archive.namelist())
            if not {f"Planificateur-SDG/{executable}", "Planificateur-SDG/portable.mode"} <= names:
                raise ValueError(f"Contenu portable incomplet : {folder}")
            if archive.testzip() is not None:
                raise ValueError(f"ZIP corrompu : {folder}")
        suffix = "Windows-x64" if folder == "windows" else "macOS-arm64"
        validated.append((archives[0], f"Planificateur-SDG-{version}-{suffix}-Portable.zip", reports[0], f"verification-{suffix}.json"))
    # Validate both platforms before producing any deliverable.
    destination.mkdir(parents=True, exist_ok=False)
    outputs = []
    for archive, name, report, report_name in validated:
        for source_path, output_name in ((archive, name), (report, report_name)):
            output = destination / output_name
            shutil.copyfile(source_path, output)
            outputs.append(output)
    checksums = []
    for output in outputs:
        with output.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        checksums.append(f"{digest}  {output.name}\n")
    (destination / "SHA256SUMS.txt").write_text("".join(checksums), encoding="utf-8")
    return outputs


if __name__ == "__main__":
    prepare(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3])
