# Livraison 0.3.3 — accueil commun

## Règle appliquée

| Plage initiale | Minimum |
| --- | --- |
| 6 h 50 à 7 h | Deux personnes au total, tous groupes confondus |
| 7 h à 17 h | Deux éducateurs par groupe ouvert |
| 17 h à 17 h 35 | Deux personnes au total, tous groupes confondus |

Le ratio de 1/20, configurable, reste obligatoire pendant l’accueil des enfants. Tous les enfants présents sont comptés ensemble pendant l’accueil commun ; avec 60 enfants encore présents, trois personnes sont nécessaires. En présence de ratios de groupe différents, le ratio le plus strict est retenu pour la période commune. La plage du matin reste bien 6 h 50–7 h, conformément à la précision du responsable.

Les quarts gardent leurs groupes : la présence collective suffit pendant les plages communes, sans déplacer toutes les affectations dans un même groupe. Les pauses, payées ou non, ne couvrent pas les enfants ; les buffers ne sont pas de la couverture. La préparation avant l’ouverture et la fermeture après le départ utilisent la présence réelle. Les quinze minutes de relève sont conservées, y compris une transmission entre éducateurs de groupes différents pendant l’accueil commun.

## Changements et vérification

1. Moteur partagé de règle et calculs à la minute ; validation, ratio, alertes et solveur utilisent les mêmes bornes. Les profils actifs sont comptés une seule fois. L’amorçage de génération tient compte des deux ouvertures et des deux fermetures collectives.
2. Explications dans Inscriptions et Paramètres. La bande et les alertes portent le libellé « Tous les groupes ». Le contrôle du logiciel portable vérifie deux personnes au total aux extrémités.
3. Version 0.3.3, notes de version, aperçus Qt6 et PDF d’exemple actualisés. Chaque étape possède un commit distinct.

Les suites locale, Windows et Mac réussissent chacune 267 tests et six sous-cas de pagination, dont sept nouveaux tests de plages communes. Les exécutables compilés sont contrôlés dans leur dossier portable puis après extraction des ZIP. Dix tests supplémentaires vérifient la préparation de la release et ses notes. Le diagnostic source Qt6/OR-Tools vérifie aussi les extrémités collectives. Les résultats Windows/Mac et le SHA exact sont consignés dans [État des vérifications](ETAT_VERIFICATION.md) avant publication.

## Hypothèses et limites

- Il s’agit d’un minimum de deux, pas d’un plafond : le ratio, les relèves ou les quarts verrouillés peuvent nécessiter davantage de personnes.
- Les plages suivent les paramètres d’ouverture : préparation avant l’arrivée des enfants, puis accueil commun à partir de trente minutes avant la fermeture aux enfants jusqu’à la fin de la fermeture de l’école. Les heures initiales restent 6 h 50–17 h 35.
- Les nouveaux brouillons adoptent la version 4 des règles ; les horaires publiés/archivés conservent leurs règles historiques. Les snapshots et le format SQLite 3 sont conservés.
- Les huit heures rémunérées maximum, les disponibilités, les pauses, les rangs et les verrous restent applicables.
- Un délai peut interrompre l’optimisation des préférences ; le logiciel le signale et n’applique aucune proposition invalide. La recherche reste limitée à des candidats à bornes métier exactes.
- Aucun changement du modèle PDF, aucune installation requise, aucune mise à jour automatique ni notarisation DeveloperID Mac ajoutée. Les essais sur le poste de l’école, l’imprimante physique et le lecteur d’écran restent à faire.

## Fichiers modifiés depuis 0.3.2

- `.github/release-request.json`
- `CHANGELOG.md`
- `README.md`
- `docs/ETAT_VERIFICATION.md`
- `docs/GUIDE.md`
- `docs/LIVRAISON_0_3_3.md`
- `docs/accueil.png`
- `docs/apercu-interface.png`
- `docs/exemple-horaire-pedagogique.pdf`
- `docs/planification-0.3.3.png`
- `gardeplan/__init__.py`
- `gardeplan/alerts.py`
- `gardeplan/coverage.py`
- `gardeplan/installation_check.py`
- `gardeplan/models.py`
- `gardeplan/optimizer.py`
- `gardeplan/optimizer_priorities.py`
- `gardeplan/staffing.py`
- `gardeplan/ui/enrolment.py`
- `gardeplan/ui/forms.py`
- `gardeplan/validation.py`
- `pyproject.toml`
- `scripts/prepare_release.py`
- `scripts/test_prepare_release.py`
- `tests/test_daily_limit.py`
- `tests/test_schedule_ui.py`
- `tests/test_shared_staffing.py`
- `tests/test_staffing_policy.py`
- `tests/test_two_per_group.py`
