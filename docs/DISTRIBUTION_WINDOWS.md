# Distribution Windows

## Fichier à remettre

Le livrable destiné à la responsable du service de garde est **`Planificateur-SDG-Installation.exe`**, qui installe le **Planificateur — Service de garde**. Il contient Python, PySide6, SQLite, OR-Tools, ReportLab et les fichiers du logiciel. Une fois ce fichier reçu, aucune connexion Internet ni installation technique n’est nécessaire sur le poste d’utilisation.

L’installation est en français et vise Windows 10 version 1809 ou ultérieure et Windows 11, en 64 bits. Elle s’effectue pour le compte Windows courant, sans droits administrateur, dans `%LOCALAPPDATA%\Programs\GardePlan`. Un raccourci est ajouté au menu Démarrer ; celui du Bureau est proposé lors de l’installation.

Les données sont conservées séparément dans le dossier local de l’application, déterminé par Qt `AppLocalDataLocation` avec le nom d’organisation et d’application `GardePlan` (normalement `%LOCALAPPDATA%\GardePlan\GardePlan`). Les bases SQLite, copies de sécurité et historiques ne sont pas inclus dans les fichiers à désinstaller. Le dossier technique `Programs\GardePlan`, le dossier de fabrication `dist/GardePlan`, les identifiants Qt `GardePlan/GardePlan` et l’AppId Inno Setup sont volontairement conservés malgré le nouveau nom affiché. Ils permettent aux mises à jour de retrouver l’installation et les données existantes ; le paquet source Python reste `gardeplan`.

**Aucun installateur Windows n’a été compilé ou testé dans l’environnement Linux du projet.** Le pipeline ci-dessous doit réussir sous Windows avant de remettre un `.exe` comme livrable vérifié.

## Produire le livrable avec GitHub Actions

1. Placez le projet dans un dépôt GitHub et ouvrez l’onglet **Actions**.
2. Lancez **Vérifier et construire Windows** avec **Run workflow**. Il s’exécute aussi sur les propositions de modification et les changements de la branche `main`.
3. Attendez la réussite de toutes les étapes.
4. Téléchargez l’artefact **Planificateur-SDG-Installation-Windows**, extrayez son contenu et remettez **Planificateur-SDG-Installation.exe** à la responsable. Conservez les fichiers JSON avec la version livrée.

Le workflow utilise Windows, Python 3.12 64 bits et le compilateur Inno Setup 6 du runner. Il recherche `ISCC.exe` sur le PATH et dans ses emplacements d’installation habituels. S’il est absent, le traitement s’arrête explicitement ; aucun faux installateur n’est produit. Aucun dépôt cible ni release publique n’est créé automatiquement.

## Compiler localement

Utilisez un poste Windows de test vierge ou une machine virtuelle, avec Python 3.12 64 bits et [Inno Setup 6](https://jrsoftware.org/isdl.php) installés. Un accès Internet est nécessaire pour télécharger les bibliothèques lors de la préparation. Depuis le dossier du projet :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

Si `ISCC.exe` se trouve ailleurs :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1 -InnoSetupCompiler "C:\Outils\Inno Setup 6\ISCC.exe"
```

Le script refuse le contrôle automatique lorsqu’une installation portant l’AppId du **Planificateur — Service de garde** existe déjà, en inspectant les clés de désinstallation utilisateur et système dans les vues 32 et 64 bits du registre. Une installation de test avec le même AppId pourrait remplacer l’enregistrement de cette installation réelle, même dans un autre dossier. Utilisez alors le runner GitHub Actions ou un poste de test vierge ; ne désinstallez pas votre logiciel de travail pour compiler.

Le script détermine la version à partir de `pyproject.toml` et la transmet au compilateur Inno Setup. Le fichier `.iss` ne contient aucune autre version codée en dur. Pour utiliser le Python 3.12 64 bits déjà sur le PATH, ajoutez `-UseCurrentPython`.

## Contrôles qui conditionnent la livraison

Le script local et le workflow exécutent la même séquence :

1. Installation des dépendances et exécution complète de `pytest`, avec Qt hors écran.
2. Construction de l’exécutable `dist/GardePlan/Planificateur-SDG.exe` avec PyInstaller.
3. Lancement de **l’exécutable gelé** avec `--check-installation` depuis son propre dossier, avec le module Qt Windows natif. Le processus dispose de deux minutes pour terminer.
4. Création de `dist/installer/Planificateur-SDG-Installation.exe` par Inno Setup.
5. Installation silencieuse dans un dossier temporaire (`RUNNER_TEMP\GardePlanInstalled` sur GitHub Actions).
6. Lancement de **l’exécutable installé**, avec le même contrôle et les mêmes exigences.
7. Désinstallation silencieuse et contrôle de la suppression de l’exécutable et de la conservation d’un fichier témoin unique dans le véritable dossier des données de l’application. Seul ce témoin créé pour le contrôle est ensuite supprimé.

Les deux contrôles de l’application exigent `success: true`, `frozen: true`, la bonne version, `qt_platform: "windows"` et la réussite de sept vérifications : Qt, couverture et minutes exactes, SQLite et sauvegarde, calendrier Jour/Semaine, PDF et modules d’aperçu/impression, génération CP-SAT, opérations avec le réseau interdit. Les données de ces contrôles résident dans des dossiers temporaires ; aucune base personnelle n’est ouverte.

Les anciens comptes rendus et l’ancien installateur de sortie sont supprimés avant la compilation. Un échec des contrôles après compilation retire l’installateur de sortie. Le workflow publie son artefact uniquement après la réussite du pipeline entier.

## Sorties et conservation

Les fichiers attendus après réussite sont :

| Fichier | Rôle |
| --- | --- |
| `dist/installer/Planificateur-SDG-Installation.exe` | Installateur à remettre à l’utilisatrice |
| `dist/verification/portable.json` | Résultat de l’exécutable PyInstaller |
| `dist/verification/installed.json` | Résultat de l’application installée |
| `dist/verification/uninstall.json` | Retrait de l’exécutable et conservation du témoin de données |

Le workflow n’envoie que l’installateur et ces JSON dans son artefact. Pour obtenir aussi une archive portable localement, ajoutez `-PortableArchive` : `dist/Planificateur-SDG-Portable.zip` contient le dossier complet, dont tous les fichiers doivent rester ensemble. L’installateur reste le livrable conseillé pour l’utilisation courante.

Conservez une copie de l’installateur et des comptes rendus de chaque version remise. Les mises à jour réutilisent l’AppId stable et le dossier précédent. La désinstallation conserve les données ; leur transfert ou sauvegarde s’effectue avec la fonction de sauvegarde locale du **Planificateur — Service de garde**.
