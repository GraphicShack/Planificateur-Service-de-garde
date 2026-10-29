#!/bin/bash
# Native portable .app folder + ZIP. No installation or Applications copy.
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
    printf '%s\n' 'La création du logiciel macOS nécessite un Mac.' >&2
    exit 1
fi
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
BOOTSTRAP_PYTHON="${PLANIFICATEUR_BUILD_PYTHON:-python3.12}"
if ! command -v "$BOOTSTRAP_PYTHON" >/dev/null 2>&1; then
    printf '%s\n' 'Installez Python 3.12 sur le Mac de compilation, ou indiquez son chemin avec PLANIFICATEUR_BUILD_PYTHON.' >&2
    exit 1
fi
for required_tool in ditto codesign; do
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
STAGE="$PROJECT_ROOT/dist/portable-macos/Planificateur-SDG"
ARCHIVE="$ARTIFACT_DIRECTORY/Planificateur-SDG-${VERSION}-macOS-${ARCHITECTURE}-Portable.zip"
mkdir -p "$ARTIFACT_DIRECTORY" "$VERIFICATION_DIRECTORY"
rm -f "$ARCHIVE" "$VERIFICATION_DIRECTORY/macos-app.json" "$VERIFICATION_DIRECTORY/macos-portable.json" "$VERIFICATION_DIRECTORY/macos-portable-archive.json" "$VERIFICATION_DIRECTORY/macos-dmg.json"
TEMPORARY_DIRECTORY="$(mktemp -d "${TMPDIR:-/tmp}/planificateur-portable.XXXXXX")"
BUILD_SUCCEEDED=0
cleanup() {
    local status=$?
    trap - EXIT
    if [ "$BUILD_SUCCEEDED" -ne 1 ]; then rm -f "$ARCHIVE"; fi
    rm -rf "$TEMPORARY_DIRECTORY"
    exit "$status"
}
trap cleanup EXIT

"$BOOTSTRAP_PYTHON" -m venv .venv
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e '.[dev]'

check_frozen_application() {
    local executable="$1"
    local report="$2"
    local expected_portable="$3"
    local update_archive="${4:-}"
    if [ ! -x "$executable" ]; then
        printf 'Exécutable absent : %s\n' "$executable" >&2
        return 1
    fi
    "$PYTHON" - "$executable" "$report" "$VERSION" "$expected_portable" "$update_archive" <<'PY'
from pathlib import Path
import json
import subprocess
import sys
executable, report_path, version = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
expected_portable = sys.argv[4] == 'true'

def fail(message):
    # The report contains only synthetic test data, not the personal database.
    if report_path.is_file():
        try:
            print(report_path.read_text(encoding='utf-8', errors='replace'), file=sys.stderr)
        except OSError:
            print(f'Compte rendu illisible : {report_path}', file=sys.stderr)
    raise SystemExit(message)

report_path.unlink(missing_ok=True)
print(f'Contrôle réel : {executable}', flush=True)
command=[str(executable), '--check-installation', str(report_path)]
if sys.argv[5]:command+=['--check-update-archive',sys.argv[5]]
process = subprocess.Popen(command, cwd=executable.parent)
try:
    code = process.wait(timeout=120)
except subprocess.TimeoutExpired:
    process.kill()
    process.wait(timeout=10)
    fail('Le contrôle de l’application a dépassé deux minutes.')
if code:
    fail(f'Le contrôle a échoué (code {code}). Consultez {report_path}.')
if not report_path.is_file():
    fail(f'Compte rendu JSON absent : {report_path}')
try:
    report = json.loads(report_path.read_text(encoding='utf-8'))
except (OSError, ValueError) as exc:
    fail(f'Compte rendu JSON invalide : {exc}')
if not isinstance(report, dict):
    fail('Le compte rendu doit être un objet JSON.')
if report.get('success') is not True or report.get('frozen') is not True or report.get('version') != version:
    fail('Le contrôle ne confirme pas une application gelée valide de la bonne version.')
if report.get('qt_platform') != 'cocoa':
    fail('Le module Qt natif macOS cocoa n’a pas été chargé.')
if report.get('portable_mode') is not expected_portable:
    fail('Le mode de données ne correspond pas au paquet testé.')
if expected_portable and report.get('checks', {}).get('portable_data_write') is not True:
    fail('L’écriture réelle des données à côté du logiciel portable n’a pas été confirmée.')
required = ('qt_application', 'coverage_and_exact_minutes', 'sqlite_save_reopen_backup',
            'dashboard_day', 'pdf_export_preview_print_modules',
            'ortools_cp_sat_generation', 'offline_operations')
for name in required:
    if report.get('checks', {}).get(name) is not True:
        fail(f'Contrôle absent ou en échec : {name}')
PY
}

printf '%s\n' 'Tests complets de l’application...'
export QT_QPA_PLATFORM=offscreen
"$PYTHON" -m pytest -q
unset QT_QPA_PLATFORM
printf '%s\n' 'Création de l’application macOS autonome...'
"$PYTHON" -m PyInstaller --noconfirm --clean Planificateur-macOS.spec
codesign --verify --deep --strict "$APP"
check_frozen_application "$APP/Contents/MacOS/Planificateur-SDG" "$VERIFICATION_DIRECTORY/macos-app.json" true

# Never repack a staging folder that someone has started using for real data.
if [ -d "$STAGE/donnees" ] && [ -n "$(ls -A "$STAGE/donnees")" ]; then
    printf 'Conservez ou déplacez le dossier contenant vos données avant de compiler : %s\n' "$STAGE" >&2
    exit 1
fi
if [ -e "$STAGE" ]; then rm -rf "$STAGE"; fi
mkdir -p "$STAGE/donnees"
ditto "$APP" "$STAGE/Planificateur-SDG.app"
# Marker and writable data stay OUTSIDE the signed bundle.
printf '%s\n' 'portable' > "$STAGE/portable.mode"
cat > "$STAGE/LIRE-MOI.txt" <<'GUIDE'
PLANIFICATEUR — SERVICE DE GARDE : VERSION PORTABLE

1. Décompressez le dossier complet sur une clé USB ou dans un dossier où vous pouvez écrire.
2. Ouvrez Planificateur-SDG.app depuis ce dossier. Aucun déplacement vers Applications.
3. Vos horaires restent dans le sous-dossier donnees. Gardez aussi portable.mode et tous les fichiers.

Pour une mise à jour, sauvegardez puis conservez le sous-dossier donnees.
GUIDE
codesign --verify --deep --strict "$STAGE/Planificateur-SDG.app"
"$PYTHON" -m gardeplan.portable_package manifest "$STAGE" "$VERSION"
check_frozen_application "$STAGE/Planificateur-SDG.app/Contents/MacOS/Planificateur-SDG" "$VERIFICATION_DIRECTORY/macos-portable.json" true
if [ -n "$(ls -A "$STAGE/donnees")" ]; then
    printf '%s\n' 'Le contrôle portable doit nettoyer ses données de test avant de créer le ZIP.' >&2
    exit 1
fi
printf '%s\n' 'Création et contrôle de l’archive portable...'
"$PYTHON" -m gardeplan.portable_package archive "$STAGE" "$ARCHIVE"
EXTRACTION="$TEMPORARY_DIRECTORY/extracted"
mkdir -p "$EXTRACTION"
ditto -x -k "$ARCHIVE" "$EXTRACTION"
check_frozen_application "$EXTRACTION/Planificateur-SDG/Planificateur-SDG.app/Contents/MacOS/Planificateur-SDG" "$VERIFICATION_DIRECTORY/macos-portable-archive.json" true "$ARCHIVE"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    printf 'architecture=%s\n' "$ARCHITECTURE" >> "$GITHUB_OUTPUT"
fi
printf 'Logiciel portable vérifié, sans installation : %s\n' "$ARCHIVE"
printf 'Comptes rendus : %s\n' "$VERIFICATION_DIRECTORY"
BUILD_SUCCEEDED=1
