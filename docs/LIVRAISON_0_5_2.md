# Livraison 0.5.2 — survol, FAQ et accès aux sections

## Modifications

1. Commandes et cartes : survol visible des boutons, actions principales, journées récentes, champs, onglets et cartes d’équipe. Un curseur indique le clic ou le glisser-déposer ; les commandes désactivées restent neutres. Les boutons pleins gardent un focus blanc visible au clavier.
2. Grille : contour et ombre accentués, poignée visée remplie, infobulle d’action et curseur cohérent sur toute la zone de redimensionnement. Le survol s’efface au départ de la souris, au défilement et lors d’une nouvelle disposition. La bande de ratio utilise un contour pointillé au survol, distinct de la sélection.

3. FAQ : 17 réponses locales avec recherche sans distinction d’accents, accordéons utilisables avec Entrée ou Espace, accès par l’icône ? et F1. La recherche se rejoint avec Ctrl+F ou Cmd+F.
4. Navigation : barre latérale commune et défilable, cibles d’au moins 44 px, suivi du focus au clavier et accès direct aux panneaux depuis l’accueil. Le premier clic sur Ratio ouvre sa couverture.
5. FAQ illustrée : 14 captures Qt avec des données fictives, légendes et vue agrandie avec zoom, taille réelle et adaptation à la fenêtre. Les images suivent la largeur disponible, restent locales et se chargent à l’ouverture d’une réponse. Un fichier absent laisse l’aide utilisable. Un script permet de les régénérer sans ouvrir les données personnelles.

Les effets réutilisent les couleurs des thèmes et la transition existante de 120 ms. Les cartes et boutons ne changent pas de dimensions. Les règles, les données, les heures, les exports PDF et le moteur de génération restent identiques.

## Aperçus

- [Journée récente survolée](survol-accueil-0.5.2.png).
- [Grille sans survol de quart](survol-grille-avant-0.5.2.png).
- [Poignée de quart survolée](survol-grille-0.5.2.png).

- [FAQ intégrée](faq-0.5.2.png).
- [Recherche dans la FAQ](faq-recherche-0.5.2.png).
- [Accueil et icônes](accueil-navigation-0.5.2.png).
- [FAQ et barre latérale sur petit écran](faq-petit-ecran-0.5.2.png).
- [FAQ avec capture intégrée](faq-illustree-0.5.2.png).
- [Capture agrandie](faq-capture-agrandie-0.5.2.png).

Captures Qt6 réelles avec des données fictives. Le scénario vérifie que l’horaire et son état de sauvegarde restent identiques après survol.

## Vérification

Après ajout des images, les contrôles ciblés FAQ, accueil et préparation de release réussissent **23 tests et trois sous-cas**. Six nouveaux tests vérifient les 14 fichiers décodables, leur association aux réponses, le chargement à la demande, une largeur de 480 px sans défilement horizontal, l’agrandissement au clavier, le zoom et le comportement en cas de fichier absent. Le diagnostic réel Qt6 hors ligne réussit avec `faq_screenshots`. Le paquet Python construit contient les 14 PNG ; les deux fichiers PyInstaller incluent déjà récursivement le dossier des ressources. Les nouveaux exécutables Windows et Mac n’ont pas été compilés localement.

La suite complète locale réussit **346 tests et six sous-cas** en 141,33 s. Les dix contrôles de publication réussissent aussi. Le diagnostic Qt6 hors ligne confirme `faq_navigation` et les opérations habituelles SQLite, PDF et génération. Les comptes rendus des exécutables compilés seront joints à la [release 0.5.2](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/tag/v0.5.2), qui reste conditionnée aux deux constructions natives du même code.

Les 62 tests ciblés de la grille, des commandes, du tableau de bord, des thèmes, de l’accueil et des animations réussissent. Le nouveau cas vérifie que le curseur de la poignée correspond à sa zone réellement cliquable, puis qu’un glissement ajuste la fin d’une minute sans modifier directement le modèle. Les cas existants vérifient le verrouillage, la consultation, le clavier, les thèmes et les mouvements réduits. Les cinq nouveaux tests de FAQ et de navigation vérifient la recherche, les réponses, le clavier, les raccourcis, les sections depuis l’accueil, les cibles visibles sur une fenêtre de 640 × 480 et la conservation d’une modification non enregistrée. Le contrôle du logiciel compilé vérifie aussi l’ouverture de la FAQ, sa recherche, le retour à l’accueil et l’icône Ratio, avec le réseau interdit et sans modification de la journée. La publication exige désormais le contrôle `faq_navigation`. Les contrôles natifs requis par la distribution sont exécutés avant publication ; les preuves sont jointes à la release et référencées dans [État des vérifications](ETAT_VERIFICATION.md).

## Hypothèses et limites

- Les retours sont discrets : fond, contour, poignée et curseur. Aucun agrandissement des cartes ou déplacement animé des contrôles.
- Les informations essentielles restent affichées ou accessibles au clavier. Les infobulles complètent les libellés ; elles ne remplacent pas les heures et les alertes.
- L’option de désactivation des animations supprime les transitions, avec conservation du retour statique au survol et du focus. Aucun nouveau réglage ajouté.
- Aucune modification des ratios, pauses, disponibilités, rangs, maximums, sauvegardes ou PDF. Les essais physiques avec souris et lecteur d’écran sur le poste de l’école restent à réaliser.
- Les captures sont des exemples fixes du thème clair et de la journée fictive du 2 novembre 2026 ; elles ne représentent pas les données courantes de la personne qui lit la FAQ. Les légendes et les réponses restent consultables indépendamment des images. Les captures ne sont pas traduites en illustrations vectorielles et ne suivent pas la couleur du thème choisi.

## Fichiers modifiés

- Interface : `gardeplan/app.py`, `gardeplan/ui/motion.py`, `gardeplan/ui/theme.py`, `gardeplan/ui/home.py`, `gardeplan/ui/main_window.py`, `gardeplan/ui/calendar.py`, `gardeplan/ui/coverage_band.py`, `gardeplan/ui/faq.py`, `gardeplan/ui/visuals.py`.
- Vérification : `tests/test_calendar.py`, `tests/test_motion.py`, `tests/test_faq.py`, `tests/test_schedule_ui.py`, `gardeplan/installation_check.py`, `scripts/prepare_release.py`, `scripts/test_prepare_release.py`.
- Version et documentation : `gardeplan/__init__.py`, `pyproject.toml`, `CHANGELOG.md`, `README.md`, `docs/GUIDE.md`, ce rapport, `docs/ETAT_VERIFICATION.md`, les sept captures et `.github/release-request.json`.
- FAQ illustrée : `gardeplan/ui/faq_media.py`, `gardeplan/assets/faq/` (14 PNG et leur provenance), `scripts/capture_faq.py`, `tests/test_faq_media.py`, les deux nouveaux aperçus et les compléments aux fichiers FAQ, diagnostic, paquet et publication cités ci-dessus.
