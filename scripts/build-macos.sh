#!/bin/bash
# Native .app + DMG. Requires macOS, Python 3.12 and Apple's system hdiutil.
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
    printf '%s\n' 'La création du logiciel macOS nécessite un Mac.' >&2
    exit 1
fi
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
BOOTSTRAP_PYTHON="${PLANIFICATEUR_BUILD_PYTHON:-python3.12}"
if ! command -v "$BOOTSTRAP_PYTHON" >/dev/null 2>&1; then
    printf '%s\n' 'Installez Python 3.12, ou indiquez son chemin avec PLANIFICATEUR_BUILD_PYTHON.' >&2
    exit 1
fi
for required_tool in hdiutil ditto codesign; do
    if ! command -v "$required_tool" >/dev/null 2>&1; then
        printf 'Outil macOS manquant : %s\n' "$required_tool" >&2
        exit 1
    fi
done
"$BOOTSTRAP_PYTHON" - <<'PY'
import platform, struct, subprocess, sys
if sys.version_info[:2] != (3, 12) or struct.calcsize('P') != 8:
    raise SystemExit('Python 3.12 64 bits est requis.')
architecture = platform.machine()
if architecture not in ('arm64', 'x86_64'):
    raise SystemExit(f'Architecture non prise en charge : {architecture}')
if architecture != subprocess.check_output(['uname', '-m'], text=True).strip():
    raise SystemExit('Le Terminal et Python doivent utiliser la même architecture (Intel ou Apple Silicon).')
PY
VERSION="$("$BOOTSTRAP_PYTHON" - <<'PYVERSION'
import re, tomllib
with open('pyproject.toml', 'rb') as handle:
    version = tomllib.load(handle)['project']['version']
if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
    raise SystemExit('La version du projet doit contenir trois nombres, par exemple 0.1.0.')
print(version)
PYVERSION
)"
ARCHITECTURE="$("$BOOTSTRAP_PYTHON" -c 'import platform; print(platform.machine())')"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
ARTIFACT_DIRECTORY="$PROJECT_ROOT/dist/macos"
VERIFICATION_DIRECTORY="$PROJECT_ROOT/dist/verification-macos"
APP="$PROJECT_ROOT/dist/Planificateur-SDG.app"
DMG="$ARTIFACT_DIRECTORY/Planificateur-SDG-${VERSION}-macOS-${ARCHITECTURE}.dmg"
mkdir -p "$ARTIFACT_DIRECTORY" "$VERIFICATION_DIRECTORY"
# Delete only this pipeline's outputs; do not retain stale success reports.
rm -f "$DMG" "$VERIFICATION_DIRECTORY/macos-app.json" "$VERIFICATION_DIRECTORY/macos-dmg.json"
TEMPORARY_DIRECTORY="$(mktemp -d "${TMPDIR:-/tmp}/planificateur-dmg.XXXXXX")"
MOUNT_DIRECTORY="$TEMPORARY_DIRECTORY/mounted"
IMAGE_MOUNTED=0
BUILD_SUCCEEDED=0
cleanup() {
    local status=$?
    trap - EXIT
    if [ "$IMAGE_MOUNTED" -eq 1 ]; then
        if ! hdiutil detach "$MOUNT_DIRECTORY" -quiet; then
            printf 'Démontez manuellement le volume de contrôle : %s\n' "$MOUNT_DIRECTORY" >&2
            # Preserve a mounted directory rather than deleting through a mount.
            if [ "$BUILD_SUCCEEDED" -eq 1 ]; then status=1; fi
            BUILD_SUCCEEDED=0
        else
            IMAGE_MOUNTED=0
        fi
    fi
    if [ "$BUILD_SUCCEEDED" -ne 1 ]; then rm -f "$DMG"; fi
    if [ "$IMAGE_MOUNTED" -eq 0 ]; then rm -rf "$TEMPORARY_DIRECTORY"; fi
    exit "$status"
}
trap cleanup EXIT

"$BOOTSTRAP_PYTHON" -m venv .venv
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e '.[dev]'

check_frozen_application() {
    local executable="$1"
    local report="$2"
    if [ ! -x "$executable" ]; then
        printf 'Exécutable absent : %s\n' "$executable" >&2
        return 1
    fi
    "$PYTHON" - "$executable" "$report" "$VERSION" <<'PY'
from pathlib import Path
import json
import subprocess
import sys
executable, report_path, version = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
report_path.unlink(missing_ok=True)
print(f'Contrôle réel : {executable}', flush=True)
process = subprocess.Popen([str(executable), '--check-installation', str(report_path)], cwd=executable.parent)
try:
    code = process.wait(timeout=120)
except subprocess.TimeoutExpired:
    process.kill()
    process.wait(timeout=10)
    raise SystemExit('Le contrôle de l’application a dépassé deux minutes.')
if code:
    raise SystemExit(f'Le contrôle a échoué (code {code}). Consultez {report_path}.')
if not report_path.is_file():
    raise SystemExit(f'Compte rendu JSON absent : {report_path}')
report = json.loads(report_path.read_text(encoding='utf-8'))
if report.get('success') is not True or report.get('frozen') is not True or report.get('version') != version:
    raise SystemExit('Le contrôle ne confirme pas une application gelée valide de la bonne version.')
if report.get('qt_platform') != 'cocoa':
    raise SystemExit('Le module Qt natif macOS cocoa n’a pas été chargé.')
required = ('qt_application', 'coverage_and_exact_minutes', 'sqlite_save_reopen_backup',
            'dashboard_day_and_week', 'pdf_export_preview_print_modules',
            'ortools_cp_sat_generation', 'offline_operations')
for name in required:
    if report.get('checks', {}).get(name) is not True:
        raise SystemExit(f'Contrôle absent ou en échec : {name}')
PY
}

printf '%s\n' 'Tests complets de l’application...'
export QT_QPA_PLATFORM=offscreen
"$PYTHON" -m pytest -q
unset QT_QPA_PLATFORM
printf '%s\n' 'Création de l’application macOS autonome...'
"$PYTHON" -m PyInstaller --noconfirm --clean Planificateur-macOS.spec
codesign --verify --deep --strict "$APP"
check_frozen_application "$APP/Contents/MacOS/Planificateur-SDG" "$VERIFICATION_DIRECTORY/macos-app.json"

STAGING_DIRECTORY="$TEMPORARY_DIRECTORY/content"
mkdir -p "$STAGING_DIRECTORY" "$MOUNT_DIRECTORY"
ditto "$APP" "$STAGING_DIRECTORY/Planificateur-SDG.app"
ln -s /Applications "$STAGING_DIRECTORY/Applications"
printf '%s\n' 'Création et contrôle de l’image disque...'
hdiutil create -volname 'Planificateur SDG' -srcfolder "$STAGING_DIRECTORY" -fs HFS+ -format UDZO -ov "$DMG"
hdiutil verify "$DMG"
hdiutil attach "$DMG" -readonly -nobrowse -mountpoint "$MOUNT_DIRECTORY" -quiet
IMAGE_MOUNTED=1
check_frozen_application "$MOUNT_DIRECTORY/Planificateur-SDG.app/Contents/MacOS/Planificateur-SDG" "$VERIFICATION_DIRECTORY/macos-dmg.json"
hdiutil detach "$MOUNT_DIRECTORY" -quiet
IMAGE_MOUNTED=0
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    printf 'architecture=%s\n' "$ARCHITECTURE" >> "$GITHUB_OUTPUT"
fi
printf 'Livrable vérifié : %s\n' "$DMG"
printf 'Comptes rendus : %s\n' "$VERIFICATION_DIRECTORY"
BUILD_SUCCEEDED=1
