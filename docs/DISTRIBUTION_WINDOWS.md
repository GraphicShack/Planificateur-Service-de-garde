# Distribution portable Windows

## Fichier à remettre

Le livrable principal est **`Planificateur-SDG-Portable.zip`**. Remettez ce ZIP à la responsable : elle le décompresse dans un dossier ou sur une clé USB où l’écriture est autorisée, puis ouvre **`Planificateur-SDG.exe`**. Il ne faut ni installer un programme ni disposer de Python ou d’Internet sur le poste cible.

Conservez tout le dossier **Planificateur-SDG**, avec ses bibliothèques, son fichier **portable.mode** et le sous-dossier **donnees**. Les horaires, profils, archives et sauvegardes locales restent dans **donnees**, à côté de l’exécutable. Aucune inscription dans le menu Démarrer ni installation dans Program Files n’est effectuée par la version portable. Windows 10 version 1809 ou ultérieure ou Windows 11, en 64 bits, est requis. Le poste doit autoriser l’exécution du logiciel et l’écriture dans le dossier choisi.

Fermez l’application avant de déplacer son dossier ou de retirer la clé USB. Une mise à jour doit conserver le sous-dossier **donnees** ; effectuez aussi une sauvegarde locale avant de remplacer les fichiers du logiciel. Pour changer de plateforme, utilisez l’export puis l’import de sauvegarde locale.

## Télécharger le logiciel prêt à remettre

Utilisez les ZIP de la [dernière release publique](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/latest). Ils sont téléchargeables sans compte GitHub, sans enveloppe ZIP de diagnostic et sans expiration liée à la conservation des artefacts Actions. Choisissez le fichier de votre plateforme ; les archives « Source code » ne contiennent pas le programme compilé.

La publication attend les deux constructions réussies du même code, contrôle les rapports après extraction et fournit les sommes SHA-256. Les artefacts Actions restent des fichiers de diagnostic pour le développement.

## Construire avec GitHub Actions

Lancez **Vérifier et construire Windows** depuis l’onglet **Actions** du dépôt. Après réussite, téléchargez l’artefact **Planificateur-SDG-Portable-Windows**. Il contient le ZIP portable à remettre et les comptes rendus JSON à conserver avec la version livrée. Le workflow fonctionne aussi sur les propositions de modification et les changements de `main` ; les constructions réussies de `main` alimentent ensuite le workflow de publication des [Releases publiques](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/latest).

Le runner utilise Windows et Python 3.12 64 bits pour préparer le logiciel. La construction par défaut ne recherche pas Inno Setup, n’installe pas GardePlan sur le système et ne lance aucun désinstalleur. Ces outils de compilation ne sont pas nécessaires sur le poste d’utilisation.

## Construire localement

Sur le poste Windows de compilation équipé de Python 3.12 64 bits :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

Le téléchargement initial des bibliothèques nécessite Internet. Ajoutez `-UseCurrentPython` pour utiliser le Python 3.12 64 bits déjà sur le PATH. La version est lue dans `pyproject.toml`.

## Contrôles avant livraison

Le script et le workflow exécutent la même séquence :

1. Installation des bibliothèques dans le projet et exécution complète de `pytest`, avec Qt hors écran.
2. Construction PyInstaller dans le dossier technique `dist/GardePlan`, puis contrôle de son véritable exécutable.
3. Copie vers `dist/portable/Planificateur-SDG`, ajout du marqueur **portable.mode** et du dossier **donnees**.
4. Contrôle du binaire dans ce dossier, exigeant le mode portable et une écriture réelle de données SQLite locales.
5. Création du ZIP, extraction dans un dossier temporaire, puis nouveau contrôle de l’exécutable extrait.

Chaque processus dispose de deux minutes. Les contrôles exigent la bonne version, `success: true`, `frozen: true`, `qt_platform: "windows"` et les sept vérifications métier : Qt, couverture et minutes exactes, SQLite/sauvegarde, calendrier Jour/Semaine, PDF/aperçu/impression, génération CP-SAT et opérations réseau interdites. Pour le dossier portable et l’archive extraite, **`portable_mode: true`** et **`checks.portable_data_write: true`** sont également obligatoires.

Les données de diagnostic sont créées temporairement sous le dossier **donnees** du paquet testé puis supprimées. Une base personnelle n’est pas ouverte. Un dossier de fabrication contenant déjà des données fait refuser la reconstruction : déplacez-le ou sauvegardez-le avant de recommencer. Le ZIP livré ne contient aucune donnée de test ni donnée personnelle.

Les anciens rapports et le ZIP de sortie sont retirés avant la préparation ; un échec retire le ZIP en cours. GitHub Actions ne livre l’artefact qu’après réussite.

| Fichier | Rôle |
| --- | --- |
| `dist/Planificateur-SDG-Portable.zip` | ZIP prêt à remettre |
| `dist/verification/bundle.json` | Binaire PyInstaller initial |
| `dist/verification/portable.json` | Binaire dans le dossier portable |
| `dist/verification/portable-archive.json` | Binaire après extraction du ZIP |

Les précédents installateurs Windows ont été construits et vérifiés, mais ils ne constituent plus le format principal demandé. Vérifiez les rapports de la nouvelle exécution portable correspondant à votre version avant de la remettre.

## Installateur facultatif pour d’autres contextes

L’ancienne construction Inno Setup reste accessible uniquement avec **`-BuildInstaller`**. Elle exige Inno Setup 6 et un poste de test sans installation existante : la garde de registre protège l’AppId stable avant tout essai d’installation/désinstallation. Elle produit un installateur supplémentaire et ses contrôles ; elle n’est pas exécutée par le workflow portable par défaut et ne répond pas à un poste cible interdisant les installations.

## Construction vérifiée

Le [workflow portable du 24 octobre 2026](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657387) a réussi 118 tests et les contrôles du binaire, du dossier portable et du ZIP extrait. Le [paquet Windows vérifié](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657387/artifacts/12578819035) contient `Planificateur-SDG-Portable.zip` et ses rapports. Aucun installateur n’a été nécessaire pour cette livraison portable.
