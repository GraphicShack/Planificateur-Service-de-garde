# Planificateur — Service de garde

Application de bureau en français pour planifier **une journée pédagogique à la fois** dans un service de garde scolaire au Québec. Les données demeurent sur le poste, dans SQLite. Aucun compte, serveur ou abonnement ; aucun accès réseau dans l'application.

## Version 0.2.0 — planification d’une journée pédagogique

![Aperçu du tableau de planification](docs/apercu-interface.png)

- Écran inspiré de la référence fournie : navigation vert foncé, calendrier blanc et blocs pastel, fiches avec initiales.
- Une date et un nom facultatif par journée ; aucune vue hebdomadaire dans le parcours de planification.
- Calendrier quotidien, groupes en colonnes, quarts à la minute, glisser-déposer et redimensionnement.
- Couleur distincte attribuée à chaque création d’éducatrice, modifiable ; rang choisi de **1 à 11**, avec rangs intermédiaires libres.
- Heures cibles/garanties/maximales, disponibilités, absences et préférences **pour la journée**.
- Journées nommées et répartition des inscriptions en groupes de taille configurable.
- Activités et locaux indépendants des quarts ; alertes de couverture et de conflits.
- Validation continue, proposition automatique CP-SAT, quarts verrouillés et annulation.
- Historique, statut, archives et duplication indépendants pour chaque date ; sauvegardes locales. Les anciennes semaines restent conservées et consultables par journée.
- **Un seul PDF général**, lettre paysage, selon le modèle fourni : huit éducateurs par page, grille 7 h–18 h, couleurs par groupe, coupures et interruptions laissées vides.

Les règles initiales sont : ouverture à 7 h avec deux éducatrices dès 6 h 50, fermeture à 17 h 30 avec deux jusqu'à 17 h 35, relève de quinze minutes, couverture continue et ratio de 1/20 avec au moins deux éducatrices par groupe actif. Le ratio et les paramètres restent configurables. Les buffers rémunérés n'assurent pas automatiquement la couverture des enfants.

## Version prête à utiliser, sans installation

La version **0.2.0** regroupe la planification quotidienne, les couleurs automatiques, les rangs de 1 à 11 et le nouveau PDF unique. La publication de cette livraison a été autorisée explicitement par le responsable du projet.

La livraison principale est un **ZIP portable**, disponible dans les [téléchargements publics du projet](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/latest). **Aucune connexion GitHub n'est nécessaire.**

- [Télécharger pour Windows 64 bits](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/download/v0.2.0/Planificateur-SDG-0.2.0-Windows-x64-Portable.zip).
- [Télécharger pour Mac Apple Silicon, macOS 15+](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/download/v0.2.0/Planificateur-SDG-0.2.0-macOS-arm64-Portable.zip).

Décompressez le dossier complet dans un emplacement autorisé en écriture ou sur une clé USB, puis ouvrez **`Planificateur-SDG.exe`** sous Windows ou **`Planificateur-SDG.app`** sous macOS. Aucun programme d’installation, Python, compte ni connexion Internet n’est nécessaire sur le poste cible. Gardez le dossier complet : les horaires et sauvegardes restent dans son sous-dossier **`donnees`**. Les liens GitHub Actions servent aux diagnostics de compilation et peuvent exiger une connexion ; les utilisateurs téléchargent les ZIP de la section **Releases**.

Depuis la version **0.1.2**, le démarrage Mac gère les copies temporaires AppTranslocation : il retrouve le dossier portable d’origine ou vous demande de le sélectionner, puis rouvre les données de ce dossier. Aucun réglage de sécurité n’est modifié.

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

Les versions **0.2.0** ont réussi **158 tests chacune**, ainsi que les contrôles natifs après extraction du ZIP. Les [résultats réellement vérifiés](docs/ETAT_VERIFICATION.md) donnent les exécutions et rapports correspondants. La publication exige l’accord du responsable pour un SHA précis, enregistré dans `.github/release-request.json`, ou une confirmation manuelle avec ce SHA. Les changements ordinaires du code ne sont pas publiés automatiquement. Le workflow **Publier les téléchargements portables** exige les deux constructions réussies du code approuvé et les rapports natifs. Chaque livraison contient les ZIP directement utilisables, les rapports et les sommes SHA-256. Augmentez la version avant de publier une nouvelle livraison ; une version publiée reste figée.

## Développement : lancer depuis les sources

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

`python -m gardeplan --example` ouvre une base d'exemple distincte, contenant des noms fictifs. Sans cet argument, l'application démarre avec la dernière journée sauvegardée ou une journée vide. `--database chemin.sqlite` permet de choisir un autre emplacement. Les fichiers SQLite personnels sont exclus de Git.

## Tests et documentation

```sh
python -m pytest -q
```

Pour les tests graphiques sans écran, définir `QT_QPA_PLATFORM=offscreen`.

- [Guide d'utilisation](docs/GUIDE.md)
- [Architecture et conventions](docs/ARCHITECTURE.md)
- [Matrice des exigences et limites](docs/EXIGENCES.md)
- [Résultats réellement vérifiés et contrôles restants](docs/ETAT_VERIFICATION.md)
- [Exemple du PDF unique (deux pages)](docs/exemple-horaire-pedagogique.pdf)

Le solveur choisit parmi des quarts candidats : un échec de cette recherche n'est pas une preuve universelle d'impossibilité. Les restrictions écrites en notes libres ne sont pas interprétées ; saisir les contraintes obligatoires dans les champs structurés. Toute proposition est validée avant acceptation et toute publication comportant une erreur est refusée.
