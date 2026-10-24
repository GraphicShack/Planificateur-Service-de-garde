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


## Version prête à utiliser, sans installation

La livraison principale est un **ZIP portable**. Décompressez le dossier complet dans un emplacement autorisé en écriture ou sur une clé USB, puis ouvrez **`Planificateur-SDG.exe`** sous Windows ou **`Planificateur-SDG.app`** sous macOS. Aucun programme d’installation, Python, compte ni connexion Internet n’est nécessaire sur le poste cible. Gardez le dossier complet : les horaires et sauvegardes restent dans son sous-dossier **`donnees`**.

Les contrôles de construction vérifient le mode portable et l’écriture réelle des données à côté du logiciel, puis refont le contrôle après extraction du ZIP. Le poste doit permettre l’exécution de ce logiciel portable et l’écriture dans le dossier choisi.

## Construire sur Mac

Sur un Mac de compilation équipé de Python 3.12 :

```bash
bash scripts/build-macos.sh
```

Le résultat est `dist/macos/Planificateur-SDG-<version>-macOS-<architecture>-Portable.zip`. Une construction cible `arm64` ou `x86_64`, selon le Python natif utilisé. L’application reste dans son dossier portable ; aucun déplacement vers Applications n’est demandé. Voir la [procédure macOS](docs/DISTRIBUTION_MACOS.md).

Vous pouvez aussi lancer **« Vérifier et construire macOS »** dans GitHub Actions et récupérer l’artefact **`Planificateur-SDG-Portable-macOS-<architecture>`** après réussite. Depuis votre Mac, le workflow **Windows** construit séparément le ZIP `.exe` sur un runner Windows.

## Construire pour Windows

Sur un poste de compilation Windows avec Python 3.12 64 bits :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

Le résultat principal est **`dist/Planificateur-SDG-Portable.zip`**. Le script par défaut ne dépend pas d’Inno Setup et n’exécute aucune installation ou désinstallation système. Il teste le binaire, le dossier portable et l’archive extraite. Le workflow **« Vérifier et construire Windows »** remet l’artefact **`Planificateur-SDG-Portable-Windows`** contenant le ZIP et ses comptes rendus. Voir la [procédure Windows](docs/DISTRIBUTION_WINDOWS.md).

Les versions natives antérieures ont été compilées et testées sur GitHub Actions ; la validation du nouveau format portable doit être confirmée par les rapports de l’exécution correspondant à la version remise. Les [résultats réellement vérifiés](docs/ETAT_VERIFICATION.md) distinguent ces étapes. Aucune release n’est publiée automatiquement.

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
