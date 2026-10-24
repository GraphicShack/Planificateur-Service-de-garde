# État des vérifications

Les constructions et les contrôles natifs s’exécutent sur GitHub Actions. Les fichiers à remettre sont les ZIP portables d’une exécution réussie correspondant au code voulu. Une sortie compilée dont le contrôle échoue n’est pas livrée.

## Application et interface modernisée

La version modernisée a réussi **110 tests sur Windows et 110 tests sur macOS 15 Apple Silicon**, avec Qt6/PySide6 et OR-Tools réellement installés. Le calendrier Jour/Semaine, le déplacement et redimensionnement à la minute, les formulaires, la recherche, l’annulation, les relèves, l’ouverture/fermeture, SQLite, les archives, les PDF et le solveur font partie des tests.

Premières exécutions natives réussies de cette interface :

- [Windows — 110 tests, compilation, installation et désinstallation](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40140615626).
- [Mac — 110 tests, application et ancien DMG](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40140615627).

Ces anciens installateur et DMG ne constituent plus le mode de livraison principal : le poste cible ne permettant pas d’installation, la distribution a été convertie en dossiers portables.

## Livraison portable sans installation

Le marqueur `portable.mode` détermine automatiquement le stockage dans `donnees`, à côté du programme. Le bundle Mac déclare également cette intention dans son fichier Info.plist ; les données ne sont jamais écrites à l’intérieur de l’application signée. Les versions historiques sans mode portable conservent leur emplacement de profil antérieur.

Sept tests locaux supplémentaires ont vérifié les chemins Windows/Mac, le profil historique, le choix explicite d’une base, le mode source et le déplacement du dossier complet avec réouverture de la même base SQLite. Les chemins temporaires sont normalisés pour les liens macOS et les noms courts Windows. La traduction des boutons standard Qt en français fait aussi l’objet d’un test.

Les deux distributions portables ont réussi **118 tests chacune**, puis les contrôles natifs du paquet préparé et de son ZIP extrait :

- [Windows — exécution portable réussie](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657387), [ZIP et rapports](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657387/artifacts/12578819035).
- [macOS 15 Apple Silicon — exécution portable réussie](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657434), [ZIP arm64 et rapports](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657434/artifacts/12579051978).

Ces résultats correspondent au code `373592c5eed4ba02e8dbc800a59a041d26e491e9`. La construction Windows par défaut n’a utilisé aucun installateur ni Inno Setup ; la construction Mac n’a pas copié l’application dans Applications. Les trois rapports de chaque plateforme confirment le mode portable et l’écriture réelle dans le dossier du logiciel.

Chaque contrôle du paquet portable doit confirmer :

- la bonne version, le binaire gelé et le moteur Qt natif Windows ou cocoa ;
- le logo SVG et la traduction française inclus ;
- la couverture à la minute et le calendrier dessiné ;
- une véritable sauvegarde/réouverture SQLite et une copie de sécurité ;
- les PDF ReportLab ouverts et rendus par Qt, et la disponibilité des modules d’impression ;
- une véritable génération CP-SAT, contrôlée par le validateur ;
- les opérations avec les sockets Python interdites ;
- l’écriture des données dans le dossier portable ;
- les mêmes contrôles après extraction du ZIP dans un nouvel emplacement.

Les données de vérification sont temporaires puis supprimées. Un dossier de fabrication contenant des données personnelles est refusé avant repackaging.

## Vérifications de développement

Le harnais `python scripts/check_core_without_pytest.py` a réussi 64 contrôles cœur avec Python3.12 sous Linux avant la disponibilité des runners natifs. Les deux tests `python -m unittest discover -s tests -p test_optimizer_candidates.py -v` ont aussi réussi. Ces résultats historiques sont désormais complétés par les suites pytest natives.

Le rendu de `docs/apercu-interface.png` a été produit à partir du véritable code de l’interface avec un adaptateur Qt5/PySide2 temporaire, disponible dans l’environnement Linux. Cet adaptateur n’est pas livré. La validation Qt6 provient des exécutions natives indiquées ci-dessus.

## Prise en main sur le poste cible

La souris, la lisibilité à la résolution du poste, l’imprimante physique et les autorisations d’exécution/écriture doivent encore être essayées dans l’école. Les tests d’impression chargent les modules et rendent les PDF ; ils n’utilisent pas d’imprimante physique.

Le ZIP portable n’installe aucun programme sur le système. Le poste doit néanmoins autoriser son exécution. Le paquet Mac est signé localement ; une distribution externe reconnue par Gatekeeper nécessite une signature DeveloperID et une notarisation appropriées.
