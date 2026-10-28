# Distribution portable macOS

## Ouvrir sur le Mac cible

Le livrable est **`Planificateur-SDG-<version>-macOS-<architecture>-Portable.zip`**. Décompressez-le dans un dossier ou sur une clé USB autorisant l’écriture, puis ouvrez **Planificateur-SDG.app** dans le dossier extrait. Aucun déplacement vers Applications ni installation de Python n’est demandé. L’application et ses bibliothèques sont incluses pour fonctionner hors ligne.

Gardez le dossier complet **Planificateur-SDG** : le fichier **portable.mode** et le sous-dossier **donnees** restent à côté de l’application, à l’extérieur du bundle signé `.app`. Vos horaires, archives et sauvegardes locales sont conservés dans **donnees**. Ne lancez pas cette version depuis une image disque en lecture seule. Fermez l’application avant de déplacer le dossier ou de retirer une clé USB.

Chaque construction cible une seule architecture : `arm64` pour Apple Silicon ou `x86_64` pour Intel. Le nom du ZIP indique l’architecture construite ; l’application n’est pas universelle. Le numéro majeur de macOS utilisé pour compiler devient la version minimale déclarée. Le workflow fourni utilise macOS 15 ; un autre système ou une autre architecture exige une construction et un essai correspondants.

Les identifiants techniques historiques `GardePlan`, le paquet Python `gardeplan` et le bundle ID `ca.planificateur.sdg` restent stables. Le mode portable stocke toutefois les données à côté de l’application. Pour transférer une planification entre Windows et macOS, utilisez l’export puis l’import d’une sauvegarde locale.

## Construire sur votre Mac

Sur un Mac de compilation équipé de Python 3.12 64 bits :

```bash
bash scripts/build-macos.sh
```

Pour choisir le chemin de Python :

```bash
PLANIFICATEUR_BUILD_PYTHON=/chemin/vers/python3.12 bash scripts/build-macos.sh
```

Le téléchargement initial des bibliothèques nécessite Internet. Les outils macOS `ditto` et `codesign` sont recherchés avant la construction. Le script refuse Linux/Windows et refuse de mélanger des architectures Terminal/Python différentes. Ces outils de préparation ne sont pas nécessaires sur le poste final.

La version provient de `pyproject.toml`. Les ressources visuelles de l’application sont incluses ; aucune icône `.icns` distincte n’est présumée. Le marqueur `PlanificateurPortable` est placé dans Info.plist avant la signature : une application déplacée par macOS vers un volume temporaire ne doit pas retomber silencieusement vers un profil système pour ses données. Si l’emplacement n’autorise pas l’écriture, l’application doit demander un dossier complet accessible.

## Télécharger le logiciel prêt à remettre

Utilisez les ZIP de la [dernière release publique](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/latest). Ils sont téléchargeables sans compte GitHub, sans enveloppe ZIP de diagnostic et sans expiration liée à la conservation des artefacts Actions. Choisissez le fichier de votre plateforme ; les archives « Source code » ne contiennent pas le programme compilé.

La publication attend les deux constructions réussies du même code, contrôle les rapports après extraction et fournit les sommes SHA-256. Les artefacts Actions restent des fichiers de diagnostic pour le développement.

## Construire avec GitHub Actions

Lancez **Vérifier et construire macOS**. Après réussite, récupérez l’artefact **Planificateur-SDG-Portable-macOS-<architecture>**, remettez le ZIP portable qu’il contient et conservez les trois rapports JSON. Le runner est `macos-15` ; le suffixe d’architecture est mesuré sur le Python utilisé. Le workflow ne promet pas deux architectures simultanément. Les constructions réussies de `main` alimentent ensuite le workflow de publication des [Releases publiques](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/latest).

Depuis votre Mac, le workflow **Vérifier et construire Windows** produit séparément le ZIP Windows sur un runner Windows. Le poste cible n’a pas besoin d’installer les outils de compilation.

## Contrôles avant livraison

1. Installation des bibliothèques dans le projet et exécution complète de `pytest`, avec Qt hors écran.
2. Construction PyInstaller du `.app`, contrôle de sa signature et exécution de son véritable binaire.
3. Copie du bundle dans le dossier portable, sans modification de son contenu signé ; ajout de **portable.mode**, **donnees** et d’un mode d’emploi à côté.
4. Contrôle natif de l’application dans ce dossier, avec écriture réelle de données locales.
5. Création du ZIP avec `ditto`, en conservant permissions, liens et ressources ; extraction et nouveau contrôle de l’application extraite.

Chaque processus dispose de deux minutes. Les trois contrôles exigent la bonne version, `success: true`, `frozen: true`, `qt_platform: "cocoa"`, **`portable_mode: true`**, **`checks.portable_data_write: true`** et sept vérifications métier : Qt, couverture/minutes exactes, SQLite/sauvegarde, calendrier Jour/Semaine, PDF/aperçu/impression, génération CP-SAT et opérations réseau interdites.

Les données du diagnostic sont temporaires sous **donnees** et sont supprimées avant la création du ZIP ; aucune base personnelle n’est ouverte. Une reconstruction refuse d’effacer un dossier de fabrication contenant déjà des données. En cas d’échec, le ZIP en cours est retiré ; GitHub Actions ne livre l’artefact qu’après réussite.

| Fichier | Rôle |
| --- | --- |
| `dist/macos/Planificateur-SDG-<version>-macOS-<architecture>-Portable.zip` | Paquet prêt à remettre |
| `dist/verification-macos/macos-app.json` | Application PyInstaller initiale |
| `dist/verification-macos/macos-portable.json` | Application dans son dossier portable |
| `dist/verification-macos/macos-portable-archive.json` | Application après extraction du ZIP |

## Signature et résultats

La construction locale utilise une signature **ad hoc**. Pour distribuer à d’autres personnes avec une ouverture reconnue par Gatekeeper, la signature **Developer ID** et la **notarisation Apple** restent à préparer. Un paquet portable ne contourne pas les autorisations d’exécution du poste ; aucun certificat ni identifiant Apple n’est demandé par le script.

Une construction native précédente a réussi sur macOS 15 Apple Silicon avec 110 tests et contrôle du DMG. Le nouveau format principal est le ZIP portable : vérifiez les rapports de son exécution correspondante avant livraison. Les anciennes consignes de déplacement vers Applications ne s’appliquent plus à ce format.

## Construction vérifiée

Le [workflow portable du 24 octobre 2026](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657434) a réussi 118 tests, la signature locale et les trois contrôles natifs. Le [ZIP arm64 vérifié](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657434/artifacts/12579051978) cible macOS 15 et versions ultérieures. Il est distinct de l’ancien DMG : aucun déplacement dans Applications n’est demandé.
