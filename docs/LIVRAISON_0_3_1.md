# Livraison 0.3.1

Un accueil ouvre l’application : journées récentes cliquables, résumé d’aujourd’hui, équipe et création avec inscriptions. L’icône Accueil reste disponible depuis la grille.

La grille affiche un groupe au-dessus des sous-colonnes de ses éducatrices.
Équipe, Inscriptions et Vérification partagent le panneau gauche. Le ratio
reste une bande masquable ; ses données et les alertes ne sont pas imprimées.
Les dîners restent calculés, sans être affichés dans les blocs.
Annuler/Rétablir partagent la ligne du nom de la journée. La navigation présente
Accueil, Planning, Équipe, Inscriptions, Ratio et Vérification en haut ; Dossier et
Réglages sont regroupés en bas.

## Règles retenues

- Présence de 6 h 50 à 17 h 35, accueil des enfants de 7 h à 17 h 30.
- Minimum d’une personne de 6 h 50 à 7 h et de 17 h 20 à 17 h 35 ; deux entre ces plages.
- Le ratio configuré, initialement 1/20, s’applique pendant tout l’accueil. Avec 21 enfants encore présents à 17 h 20, deux personnes sont nécessaires.
- Les effectifs par période se règlent dans les groupes ; les inscriptions sont préparées par groupes de vingt sans supprimer les affectations existantes.
- Le calcul quotidien du besoin reste global au service. La génération conserve les groupes, les profils et les quarts verrouillés ; la proposition reste modifiable avant confirmation.
- Les dix minutes d’ouverture et les cinq de fermeture restent du temps de présence, distinct de la couverture des enfants. Les pauses payées ou non sont exclues de la couverture. Les relèves gardent quinze minutes communes.
- Si les heures configurées changent, l’allègement suit l’ouverture aux enfants et les quinze dernières minutes de présence.
- Les règles portent un numéro dans les snapshots. Les anciens brouillons adoptent les règles actuelles dans une nouvelle version ; les versions historiques publiées/archivées restent figées. Une modification ou duplication crée un brouillon aux règles actuelles.

## Vérifications

Les tests ciblés vérifient les bornes 6 h 50, 7 h et 17 h 20, un déficit d’une minute juste avant 17 h 20, le maintien du ratio avec 21 enfants, les pauses, les snapshots historiques, la génération avec une seule personne aux extrémités et les groupes/verrous conservés.
Les contrôles d’interface vérifient la position des commandes et l’adoption des règles uniquement dans les versions de travail. Les résultats natifs et les sources exactes approuvées sont consignés dans [État des vérifications](ETAT_VERIFICATION.md).
Les aperçus du dépôt sont des rendus du code réel avec données fictives et un adaptateur Qt5 local non livré. Un aperçu supplémentaire a été inspecté sous Qt6 réel, en grand et petit formats. Les distributions passent les suites Qt6 et OR-Tools natives : 238 tests et six sous-cas de pagination par plateforme, puis les contrôles du ZIP extrait.

## Hypothèses propres à l’accueil

- Une seule journée est conservée par date. Une création visant une date existante ouvre la journée sans écraser ses données.
- Le tri porte sur la date de la journée, et non sa dernière modification. Les journées futures sont incluses.
- Les enfants et le minimum d’éducatrices affichés sont les maxima de la journée ; les heures sont rémunérées et le nombre d’éducatrices compte les personnes actives affectées au moins une fois.
- Les badges reprennent les erreurs et avertissements de Vérifier, avec le même regroupement. Les profils proviennent du dernier snapshot enregistré, sans ajouter un second registre d’équipe. Une modification crée une version de travail ; une base vide utilise le brouillon du jour.
- Les journées historiques sont résumées en mémoire sans migration ni création de journées pendant le simple affichage de la liste.
- Les notes de version sont centralisées dans CHANGELOG.md. La publication refuse une version dont la section est absente ou vide.

## Limites

Aucun service distant ni compte utilisateur n’est ajouté. Il n’y a pas de mise à jour automatique ni de notarisation DeveloperID Mac. Les essais avec le lecteur d’écran, l’imprimante physique et le poste de l’école restent à réaliser. Les ZIP se remplacent en conservant une copie du dossier `donnees`.

## Fichiers modifiés depuis 0.3.0

- `.github/release-request.json`
- `.github/workflows/publish-portable.yml`
- `CHANGELOG.md`
- `README.md`
- `docs/ETAT_VERIFICATION.md`
- `docs/GUIDE.md`
- `docs/LIVRAISON_0_3_1.md`
- `docs/accueil.png`
- `docs/apercu-interface.png`
- `docs/couverture-journee.png`
- `gardeplan/__init__.py`
- `gardeplan/alerts.py`
- `gardeplan/app.py`
- `gardeplan/coverage.py`
- `gardeplan/daily.py`
- `gardeplan/home_data.py`
- `gardeplan/installation_check.py`
- `gardeplan/models.py`
- `gardeplan/optimizer.py`
- `gardeplan/staff_layout.py`
- `gardeplan/staffing.py`
- `gardeplan/ui/calendar.py`
- `gardeplan/ui/enrolment.py`
- `gardeplan/ui/forms.py`
- `gardeplan/ui/home.py`
- `gardeplan/ui/main_window.py`
- `gardeplan/ui/visuals.py`
- `gardeplan/validation.py`
- `pyproject.toml`
- `scripts/prepare_release.py`
- `scripts/release_notes.py`
- `scripts/test_prepare_release.py`
- `scripts/test_release_notes.py`
- `tests/test_coverage.py`
- `tests/test_daily_ui.py`
- `tests/test_home_data.py`
- `tests/test_home_ui.py`
- `tests/test_main_window.py`
- `tests/test_portable_startup.py`
- `tests/test_schedule_ui.py`
- `tests/test_staff_layout.py`
- `tests/test_staffing_policy.py`
