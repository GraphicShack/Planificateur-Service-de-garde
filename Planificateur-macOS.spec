"""Build natively on macOS; each app targets its Python process architecture."""
from pathlib import Path
import platform
import sys
import tomllib

from PyInstaller.utils.hooks import collect_all

if sys.platform != 'darwin':
    raise SystemExit('La création de Planificateur-SDG.app doit se faire sur macOS.')

project_root = Path(SPECPATH)
with (project_root / 'pyproject.toml').open('rb') as handle:
    version = tomllib.load(handle)['project']['version']
architecture = platform.machine()
if architecture not in ('arm64', 'x86_64'):
    raise SystemExit(f'Architecture macOS non prise en charge : {architecture}')
# Do not promise support for earlier macOS releases than the build host.
minimum_macos = platform.mac_ver()[0].split('.')[0] + '.0'

datas, binaries, hiddenimports = [], [], []
# The approved SVG is displayed by the app; no custom .icns is assumed.
datas.append((str(project_root / 'gardeplan' / 'assets'), 'gardeplan/assets'))
for package in ('ortools', 'reportlab'):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

analysis = Analysis(
    [str(project_root / 'run.py')], pathex=[str(project_root)],
    binaries=binaries, datas=datas, hiddenimports=hiddenimports,
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'IPython'], noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, [], exclude_binaries=True, name='Planificateur-SDG',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=architecture,
    # PyInstaller applies ad-hoc signing when no Developer ID is supplied.
    codesign_identity=None, entitlements_file=None,
)
collection = COLLECT(
    exe, analysis.binaries, analysis.datas, strip=False, upx=False,
    name='Planificateur-macOS',
)
application = BUNDLE(
    collection, name='Planificateur-SDG.app', version=version,
    icon=str(project_root / 'gardeplan' / 'assets' / 'logo.png'),
    bundle_identifier='ca.planificateur.sdg',
    info_plist={
        'CFBundleName': 'Planificateur — Service de garde',
        'CFBundleDisplayName': 'Planificateur — Service de garde',
        'CFBundleShortVersionString': version,
        'PlanificateurPortable': True,
        # Keep data beside the bundle even if Gatekeeper translocates it.
        'PlanificateurPortable': True,
        'NSHighResolutionCapable': True,
        'LSApplicationCategoryType': 'public.app-category.productivity',
        'LSMinimumSystemVersion': minimum_macos,
    },
)
