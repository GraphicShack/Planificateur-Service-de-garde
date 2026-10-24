# État de vérification — première version

Vérifications effectuées le 24 octobre 2026 dans l'environnement Linux de développement, avec Python 3.12.14. Ce relevé décrit les contrôles réellement exécutés ; il ne constitue pas une validation complète sur Windows.

## Cœur métier, données et PDF : 64 contrôles réussis

Commande exécutée depuis la racine du projet :

```sh
python scripts/check_core_without_pytest.py
```

Sortie observée :

```text
64 contrôles cœur réussis, 0 échecs (Qt6/OR-Tools non exécutés)
```

Ce harnais exécute les fonctions et assertions réelles de `test_domain.py`, `test_planning.py`, `test_storage_pdf.py` et `test_file_safety.py`, avec leurs cas paramétrés. Il utilise un adaptateur local pour les décorateurs et les exceptions attendues de pytest, car pytest n'était pas installé. Il ne modifie aucun paquet Python. Il exige ReportLab et pypdf pour vérifier les PDF ; une dépendance manquante fait échouer le diagnostic.

Les contrôles couvrent notamment les minutes exactes, les quarts de 1 h 42, la couverture à deux, le ratio 1/20, les relèves de quinze minutes, les dix minutes d'ouverture et cinq minutes de fermeture, les pauses et buffers, les activités/locaux, les inscriptions et noms de journées, les versions figées, les sauvegardes/imports, les fichiers verrouillés et la conservation de leurs données. Le test hors ligne interdit les sockets pendant la sauvegarde/réouverture SQLite, la validation, le PDF et la sauvegarde de sécurité.

Les trois exports PDF ont été générés et leur contenu a été extrait : nom de journée, heures exactes 06 h 50 et 17 h 35, total rémunéré 10 h 45. Des exemples sont conservés dans `docs/exemple-horaire-general.pdf` et `docs/exemple-horaire-individuel.pdf`.

## Construction des candidats d'optimisation : 2 tests réussis

Commande exécutée :

```sh
python -m unittest discover -s tests -p test_optimizer_candidates.py -v
```

Sortie finale observée :

```text
Ran 2 tests
OK
```

Ces tests vérifient la construction des profils de relève et la cohérence de leurs prédécesseurs. Ils n'exécutent pas le solveur CP-SAT d'OR-Tools. Ils ne prouvent donc pas la réussite d'une génération automatique complète.

## Contrôle de syntaxe

La compilation des modules et tests a été vérifiée avec `python -m compileall -q gardeplan tests scripts`. Un contrôle de syntaxe ne remplace pas l'exécution des fonctionnalités.

## Contrôle partiel de l'interface

Un essai temporaire de la fenêtre principale a été réalisé avec les bibliothèques Qt5/PySide2 disponibles dans cet environnement, au moyen d'un adaptateur de compatibilité utilisé uniquement pour ce diagnostic. La distribution du **Planificateur — Service de garde** reste fondée sur PySide6/Qt6 ; cet adaptateur n'est pas un mode de fonctionnement livré.

Cet essai a confirmé l'affichage Jour/Semaine, un déplacement de quart de sept minutes, l'annulation et le rétablissement, la sauvegarde, ainsi qu'un déplacement d'activité de treize minutes conservant les heures des quarts. La capture `docs/apercu-interface.png` provient de ce rendu Qt5 de diagnostic.

Cet essai partiel ne valide pas les interactions PySide6/Qt6, tous les formulaires, le glisser-déposer natif Windows ou l'impression.

## Vérifications encore nécessaires

Les bibliothèques PySide6, OR-Tools et pytest n'ont pas pu être installées dans cet environnement. Par conséquent :

- La suite officielle `python -m pytest -q` n'a pas été exécutée.
- Les tests Qt6 de `test_calendar.py`, `test_forms.py` et `test_main_window.py` sont écrits mais n'ont pas été exécutés avec PySide6.
- Les tests CP-SAT de `test_optimizer.py` sont écrits mais n'ont pas été exécutés avec OR-Tools. La génération automatique reste à vérifier avec ce moteur installé.
- La prévisualisation PDF, l'impression et les gestes natifs doivent être essayés sur le poste Windows de destination.
- Aucun exécutable Windows n'a été compilé ou lancé ici. Le script PowerShell, la spécification PyInstaller et le workflow Windows sont fournis pour cette étape.

Pour terminer ces contrôles, suivre `docs/VALIDATION.md`, puis le parcours de prise en main de `docs/EXIGENCES.md`. Une suite qui ignore les tests Qt6 ou CP-SAT faute de bibliothèque ne valide pas ces fonctionnalités.

## Préparation de l'installateur Windows

La livraison prévue est un fichier `Planificateur-SDG-Installation.exe` contenant toutes les bibliothèques, avec installation en français et raccourcis. Le projet inclut le script Inno Setup et une chaîne Windows qui doit contrôler le binaire compilé, l'installer, exécuter le même contrôle sur la version installée, puis vérifier la désinstallation et la conservation d'un fichier témoin dans le dossier des données.

Le diagnostic `--check-installation` exerce réellement le calendrier, SQLite, ReportLab, la prévisualisation PDF Qt et une génération CP-SAT dans un dossier temporaire, avec les sockets Python interdites. Il produit un rapport JSON et un code de sortie non nul en cas d'échec. Les cas « dépendance absente », « ancien rapport de succès », « destination invalide » et « fichier verrouillé » ont été contrôlés dans cet environnement : ils ne produisent aucun faux succès et nettoient leurs fichiers temporaires.

Le diagnostic complet et l'installation/désinstallation ne sont pas exécutables ici, où PySide6, OR-Tools et Windows sont absents. Les fichiers de préparation ne constituent donc toujours pas un installateur déjà compilé et validé. La distribution pourra être remise lorsque la chaîne Windows aura réussi et que le parcours de prise en main aura été effectué.
