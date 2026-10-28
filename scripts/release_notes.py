"""Extract the reviewed notes for the exact version being published."""
import re
from pathlib import Path


def version_notes(changelog, version):
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):
        raise ValueError('Version invalide pour les notes de publication.')
    text=Path(changelog).read_text(encoding='utf-8')
    match=re.search(r'^## \['+re.escape(version)+r'\][^\n]*\n(.*?)(?=^## |\Z)',text,re.M|re.S)
    if not match or not match.group(1).strip():
        raise ValueError(f'Ajoutez les notes de la version {version} dans CHANGELOG.md avant de publier.')
    return match.group(1).strip()


def build_release_notes(changelog,version,repository,windows_run,macos_run):
    notes=version_notes(changelog,version)
    return notes+f'''

### Téléchargement et mise à jour

Logiciel portable en français, entièrement hors ligne. Aucun installateur ni Python requis.

- **Windows 64 bits** : téléchargez le ZIP Windows.
- **Mac Apple Silicon, macOS 15 ou plus récent** : téléchargez le ZIP macOS-arm64.

Décompressez le dossier complet dans un emplacement accessible en écriture,
puis ouvrez Planificateur-SDG.exe ou Planificateur-SDG.app. Gardez tous les fichiers ensemble.
Si Mac demande le dossier portable d’origine, sélectionnez le dossier extrait
qui contient Planificateur-SDG.app et portable.mode.

**Mise à jour** : fermez le logiciel, sauvegardez votre ancien dossier `donnees`,
puis transférez ce dossier dans la nouvelle version extraite. Ne le remplacez pas par un dossier vide.

Les ZIP proviennent des constructions natives réussies du même code, avec contrôle après extraction.
[Contrôle Windows](https://github.com/{repository}/actions/runs/{windows_run}) · [Contrôle Mac](https://github.com/{repository}/actions/runs/{macos_run}).

Le fichier SHA256SUMS permet de vérifier les téléchargements.
'''
