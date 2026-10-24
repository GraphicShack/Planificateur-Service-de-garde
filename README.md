# Planificateur — Service de garde

Application de bureau en français pour planifier un service de garde scolaire au Québec. Les données demeurent sur le poste, dans SQLite. Aucun compte, serveur ou abonnement ; aucun accès réseau dans l'application.

## Première version

![Aperçu du tableau de planification](docs/apercu-interface.png)

- Calendrier Jour/Semaine, groupes en colonnes, quarts à la minute, glisser-déposer et redimensionnement.
- Profils des éducatrices, heures, ancienneté, disponibilités, absences et préférences.
- Journées nommées et répartition des inscriptions en groupes de taille configurable.
- Activités et locaux indépendants des quarts ; alertes de couverture et de conflits.
- Validation continue, proposition automatique CP-SAT, quarts verrouillés et annulation.
- Historique immuable, archives, duplication, restauration et sauvegardes locales.
- PDF général, individuel et regroupé, avec heures exactes et aperçu.

Les règles initiales sont : ouverture à 7 h avec deux éducatrices dès 6 h 50, fermeture à 17 h 30 avec deux jusqu'à 17 h 35, relève de quinze minutes, couverture continue et ratio de 1/20 avec au moins deux éducatrices par groupe actif. Le ratio et les paramètres restent configurables. Les buffers rémunérés n'assurent pas automatiquement la couverture des enfants.

## Lancer depuis les sources

Python 3.11 ou 3.12 recommandé. Le téléchargement des dépendances nécessite Internet une première fois ; l'utilisation est ensuite hors ligne.

Sous Windows, double-cliquer sur `scripts/lancer-windows.bat`, ou dans PowerShell depuis le dossier du projet :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m gardeplan
```

Sous Linux :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m gardeplan
```

`python -m gardeplan --example` ouvre une base d'exemple distincte, contenant des noms fictifs. Sans cet argument, l'application démarre avec vos données ou une semaine vide. `--database chemin.sqlite` permet de choisir un autre emplacement. Les fichiers SQLite personnels sont exclus de Git.


## Construire sur Mac

Sur un Mac équipé de Python 3.12, depuis le dossier du projet :

```bash
bash scripts/build-macos.sh
```

Le script exécute les tests, crée **`Planificateur-SDG.app`**, vérifie le binaire avec Qt natif macOS puis produit un **DMG** avec le raccourci Applications. L’application livrée contient ses bibliothèques et fonctionne hors ligne. Le DMG est nommé selon sa version et son architecture réelle (`arm64` ou `x86_64`) ; une construction cible une seule architecture.

Vous pouvez aussi lancer **« Vérifier et construire macOS »** dans GitHub Actions et récupérer l’artefact **`Planificateur-SDG-macOS-<architecture>`** après réussite. Depuis votre Mac, le workflow **Windows** permet séparément de construire l’installateur `.exe` sur un runner Windows.

Le détail des sorties, des contrôles et de la signature de distribution se trouve dans la [procédure macOS](docs/DISTRIBUTION_MACOS.md). **La compilation macOS n’a pas été exécutée dans l’environnement Linux du projet.**

## Construire pour Windows

Le fichier à remettre à la responsable est **`Planificateur-SDG-Installation.exe`**. Elle l’ouvre, suit l’installation en français, puis lance le **Planificateur — Service de garde** depuis son Bureau ou le menu Démarrer. Son poste n’a besoin ni de Python ni d’Internet. L’installation se fait pour son compte Windows, sans droits administrateur ; les données et historiques restent conservés après une mise à jour ou une désinstallation. Windows 10 (version 1809 ou ultérieure) ou Windows 11, en 64 bits, est requis.

Pour produire ce fichier, lancez le workflow GitHub Actions **« Vérifier et construire Windows »**. Lorsque le traitement réussit, récupérez l’artefact **`Planificateur-SDG-Installation-Windows`** : il contient l’installateur et les trois comptes rendus JSON. Le workflow ne publie aucune release automatiquement.

Une compilation locale exige Windows, Python 3.12 64 bits et Inno Setup 6 :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

Le script exécute tous les tests, vérifie l’exécutable PyInstaller, construit l’installateur, l’installe dans un dossier temporaire, vérifie l’application installée puis contrôle sa désinstallation et la conservation des données. La sortie livrable est `dist/installer/Planificateur-SDG-Installation.exe`. Pour protéger une installation existante, ce contrôle exige un poste Windows de test vierge ou le runner GitHub Actions. Le détail figure dans la [procédure de distribution Windows](docs/DISTRIBUTION_WINDOWS.md).

Les installateurs vérifiés sont disponibles dans les artefacts des [exécutions Windows réussies](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/workflows/build-windows.yml). La première construction a réussi les tests, l'installation et la désinstallation. Vérifiez que l'exécution correspond à la version à remettre ; voir les [résultats réellement vérifiés](docs/ETAT_VERIFICATION.md).

## Tests et documentation

```sh
python -m pytest -q
```

Pour les tests graphiques sans écran, définir `QT_QPA_PLATFORM=offscreen`.

- [Guide d'utilisation](docs/GUIDE.md)
- [Architecture et conventions](docs/ARCHITECTURE.md)
- [Matrice des exigences et limites](docs/EXIGENCES.md)
- [Résultats réellement vérifiés et contrôles restants](docs/ETAT_VERIFICATION.md)
- [Exemple PDF général](docs/exemple-horaire-general.pdf)
- [Exemple PDF individuel](docs/exemple-horaire-individuel.pdf)

Le solveur choisit parmi des quarts candidats : un échec de cette recherche n'est pas une preuve universelle d'impossibilité. Les restrictions écrites en notes libres ne sont pas interprétées ; saisir les contraintes obligatoires dans les champs structurés. Toute proposition est validée avant acceptation et toute publication comportant une erreur est refusée.
