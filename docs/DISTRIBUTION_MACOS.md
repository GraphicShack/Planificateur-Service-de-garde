# Distribution macOS

## Installer sur un Mac

Le livrable est une image disque **`Planificateur-SDG-<version>-macOS-<architecture>.dmg`**. Ouvrez-la, glissez **Planificateur-SDG.app** vers **Applications**, puis ouvrez l’application depuis ce dossier. L’application affichera le nom **Planificateur — Service de garde**. Python et les bibliothèques sont inclus ; aucun téléchargement ni compte n’est nécessaire pendant l’utilisation.

Chaque construction cible une seule architecture : `arm64` pour Apple Silicon ou `x86_64` pour Intel. Le nom du DMG indique l’architecture réellement construite ; ce n’est pas une application universelle. Le numéro majeur de macOS utilisé pour compiler devient la version minimale déclarée par l’application. Le workflow fourni construit et vérifie sur macOS 15 ; pour un autre système ou une autre architecture, utilisez un Mac de compilation correspondant et vérifiez le résultat sur le poste cible.

Les données personnelles restent dans le dossier de données Qt de l’utilisateur, sous **Application Support**, séparément du dossier Applications. Les identifiants internes `GardePlan` et le paquet Python `gardeplan` restent inchangés. Pour transférer une planification entre Windows et macOS, exportez une sauvegarde locale depuis le logiciel source et importez-la sur l’autre poste. Le fichier d’application ne contient pas vos horaires.

## Construire sur votre Mac

Installez Python 3.12 64 bits pour l’architecture de votre Mac. Depuis le dossier du projet :

```bash
bash scripts/build-macos.sh
```

Le script utilise `python3.12`. Si Python se trouve ailleurs :

```bash
PLANIFICATEUR_BUILD_PYTHON=/chemin/vers/python3.12 bash scripts/build-macos.sh
```

Une connexion Internet sert à préparer les bibliothèques. Les outils macOS `hdiutil`, `ditto` et `codesign` sont requis et recherchés avant la construction. Le script refuse une compilation sur Linux ou Windows et refuse de mélanger des architectures Python et Terminal différentes.

Les sorties sont :

| Fichier | Usage |
| --- | --- |
| `dist/Planificateur-SDG.app` | Application autonome macOS |
| `dist/macos/Planificateur-SDG-<version>-macOS-<architecture>.dmg` | Image disque à remettre |
| `dist/verification-macos/macos-app.json` | Contrôle du véritable binaire de l’application |
| `dist/verification-macos/macos-dmg.json` | Contrôle du binaire depuis le DMG monté |

La version provient de `pyproject.toml`. L’identifiant stable du bundle est `ca.planificateur.sdg`. Les ressources visuelles de l’application sont incluses ; aucune icône `.icns` distincte n’est présumée.

## Produire le DMG avec GitHub Actions

Dans l’onglet **Actions** du dépôt, lancez **Vérifier et construire macOS**. Après réussite, téléchargez l’artefact **Planificateur-SDG-macOS-<architecture>**, extrayez le DMG et conservez les deux comptes rendus JSON. Le workflow fonctionne aussi sur les propositions de modification et sur la branche `main`. Il ne publie aucune release automatiquement.

Le runner est `macos-15`. Son architecture n’est pas présumée à partir de son nom : le script mesure celle de Python et la place dans le nom du fichier et de l’artefact. Cette construction ne promet donc pas de fournir simultanément des versions Intel et Apple Silicon.

Le workflow Windows reste disponible séparément. Pour obtenir le fichier Windows depuis un Mac, déclenchez **Vérifier et construire Windows** dans GitHub Actions, puis récupérez son artefact d’installation ; un `.exe` Windows doit être compilé sur un environnement Windows.

## Contrôles avant livraison

Le script local et le workflow exécutent la même suite :

1. Installation des bibliothèques et exécution complète de `pytest` avec Qt hors écran.
2. Construction PyInstaller du bundle `.app`, puis vérification de sa signature locale.
3. Lancement du binaire gelé avec `--check-installation` depuis son propre dossier. Le module Qt natif `cocoa` doit être utilisé.
4. Création d’un DMG contenant l’application et un raccourci vers Applications.
5. Vérification et montage du DMG en lecture seule, puis exécution du même contrôle depuis ce volume.
6. Démontage du volume et suppression des seuls fichiers temporaires de construction.

Chaque contrôle dispose de deux minutes. Il exige un compte rendu de la bonne version avec `success: true`, `frozen: true`, `qt_platform: "cocoa"` et sept vérifications réussies : Qt, couverture et minutes exactes, SQLite/sauvegarde, calendrier Jour/Semaine, PDF/aperçu/impression, génération CP-SAT et opérations avec les sockets réseau interdites. Les données de contrôle sont temporaires ; la base personnelle n’est pas ouverte.

Les anciens rapports et le DMG de cette version et architecture sont retirés au début du pipeline. En cas d’échec, le DMG en cours est supprimé. GitHub Actions ne livre l’artefact qu’après la réussite de toutes les étapes.

## Signature et état réel

PyInstaller applique une signature **ad hoc** pour la construction et les tests locaux, sans abonnement développeur Apple. Pour distribuer l’application à d’autres personnes avec une ouverture reconnue par Gatekeeper, prévoyez une signature **Developer ID** et une **notarisation Apple**. Si Gatekeeper bloque cette version locale, cette préparation de distribution reste à effectuer ; aucun certificat ni identifiant Apple n’est demandé ou utilisé par les scripts fournis.

**Aucune application macOS ni image DMG n’a été compilée ou exécutée dans l’environnement Linux du projet.** La syntaxe et la cohérence des fichiers de construction peuvent y être vérifiées ; seuls les résultats du pipeline macOS permettront d’attester la construction et le fonctionnement du livrable sur Mac.
