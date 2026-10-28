# Livraison 0.3.2

## Changements

1. Plafond de 8 h rémunérées par personne et par jour : validation, génération, compteurs et formulaires. Les versions historiques conservent leurs règles ; les brouillons adoptent les règles actuelles.
2. Génération de tous les groupes, sans fusion dans le solveur. Le minimum de deux éducateurs et le ratio propre à chaque groupe restent obligatoires ; les alertes distinguent les groupes et le résumé signale aussi une mauvaise répartition malgré un total suffisant.
3. Retrait des annotations superposées à la grille vide.
4. Attribution d’heures au plus grand nombre de personnes possible ; limitation des heures inutiles ; priorité aux rangs 1, 2, etc. pour les quarts continus, davantage d’heures et une fin plus tôt. Les profils équivalents reçoivent obligatoirement les horaires dans cet ordre, même si la recherche n’achève pas toutes ses optimisations.
5. Bouton Supprimer pour chaque journée de l’accueil. Confirmation, historique conservé, suppression persistante dans les sauvegardes et accès aux profils après suppression de la dernière journée.
6. Scénarios de vérification adaptés au nouveau plafond ; diagnostic du logiciel compilé étendu aux groupes, à l’équipe, à l’ordre des rangs et aux huit heures.

7. Correction de la date devenue invisible avec NoButtons et un style Qt 6.12.
8. Application de la dernière précision : deux éducateurs par groupe à tout moment, y compris préparation/fermeture ; aperçu Inscriptions aligné sur ce calcul.

9. Amorçage du solveur par une proposition vérifiée dans le cas de deux équipes continues par groupe ; le budget d’heures de la meilleure proposition reste conservé si une phase dépasse son délai.

Chaque étape correspond à un commit. La préparation de la release et la consignation des preuves sont des commits distincts.

## Hypothèses retenues

- « 8 h par jour » signifie 480 minutes rémunérées cumulées : buffers payés et pauses payées compris ; pauses non rémunérées déduites. La présence entre début et fin peut donc dépasser huit heures uniquement si des interruptions non payées sont saisies.
- Minimum strict de deux éducateurs par groupe ouvert, préparation et fermeture incluses. Le ratio initial de 1/20 ou un minimum configuré plus élevé peut imposer davantage de personnes. Deux groupes ouverts toute la journée nécessitent quatre personnes simultanées ; quatre salariés limités à huit heures ne peuvent donc pas suffire sur 6 h 50–17 h 35.
- Les rangs peuvent être non consécutifs. La priorité porte sur des horaires réalisables : disponibilités, garanties, maximums, pauses, couverture et quarts verrouillés passent avant les préférences.
- La participation est optimisée sans créer un droit à un nombre fixe d’heures. Les personnes sans heures sont nommées ; l’interface précise si le délai ne permet pas de prouver l’optimalité des préférences.
- Supprimer retire une date de la liste sans effacer ses snapshots. Une création explicite à cette date ou une restauration réactive la date. Modifier les profils ne réactive pas une journée supprimée.
- SQLite passe au format 3 avec copie de sécurité des formats 1/2 avant migration. Les suppressions sont conservées à l’import/export. Utilisez la nouvelle application pour ouvrir la base migrée.

## Vérification et limites

La suite Qt6/OR-Tools réussit 260 tests et six sous-cas de pagination, localement ainsi que sur Windows et Mac. Les exécutables compilés sont aussi contrôlés après extraction des ZIP. Dix tests contrôlent la préparation de release et les notes de version. Les résultats natifs et le SHA exact sont consignés dans [État des vérifications](ETAT_VERIFICATION.md) avant la livraison publique.

Les nouvelles vérifications portent sur les 480/481 minutes, les horaires coupés, les pauses payées/non payées, la couverture de chaque groupe, les groupes et quarts verrouillés conservés, la participation, les rangs libres, les indisponibilités, l’impossibilité avec huit heures, la suppression, la restauration, les sauvegardes et la migration.

Le solveur travaille sur des candidats à bornes métier exactes et à départs intermédiaires ; il ne prouve pas l’impossibilité de tous les découpages imaginables à la minute. Un délai peut laisser des préférences non optimales, ce qui est signalé. Aucune proposition comportant une erreur bloquante n’est appliquée.

Aucune mise à jour automatique ni signature DeveloperID/notarisation Mac n’est ajoutée. Les essais sur le poste de l’école, le lecteur d’écran et l’imprimante physique restent à réaliser. La mise en page du PDF est conservée ; son exemple est renouvelé avec les nouvelles règles.

## Fichiers modifiés depuis 0.3.1

- `.github/release-request.json`
- `CHANGELOG.md`
- `README.md`
- `docs/ETAT_VERIFICATION.md`
- `docs/GUIDE.md`
- `docs/LIVRAISON_0_3_2.md`
- `docs/accueil.png`
- `docs/apercu-interface.png`
- `docs/exemple-horaire-pedagogique.pdf`
- `docs/planification-0.3.2.png`
- `gardeplan/__init__.py`
- `gardeplan/alerts.py`
- `gardeplan/coverage.py`
- `gardeplan/daily.py`
- `gardeplan/hours.py`
- `gardeplan/installation_check.py`
- `gardeplan/models.py`
- `gardeplan/optimizer.py`
- `gardeplan/optimizer_priorities.py`
- `gardeplan/planning.py`
- `gardeplan/staffing.py`
- `gardeplan/storage.py`
- `gardeplan/ui/calendar.py`
- `gardeplan/ui/date_field.py`
- `gardeplan/ui/enrolment.py`
- `gardeplan/ui/forms.py`
- `gardeplan/ui/home.py`
- `gardeplan/ui/main_window.py`
- `gardeplan/validation.py`
- `pyproject.toml`
- `scripts/prepare_release.py`
- `scripts/test_prepare_release.py`
- `tests/test_coverage.py`
- `tests/test_daily.py`
- `tests/test_daily_limit.py`
- `tests/test_daily_ui.py`
- `tests/test_date_field.py`
- `tests/test_day_deletion.py`
- `tests/test_generation_priorities.py`
- `tests/test_group_generation.py`
- `tests/test_home_data.py`
- `tests/test_schedule_ui.py`
- `tests/test_staffing_policy.py`
- `tests/test_two_per_group.py`
