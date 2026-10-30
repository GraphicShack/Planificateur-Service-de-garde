# Livraison 0.5.2 — retours au survol

## Modifications

1. Commandes et cartes : survol visible des boutons, actions principales, journées récentes, champs, onglets et cartes d’équipe. Un curseur indique le clic ou le glisser-déposer ; les commandes désactivées restent neutres. Les boutons pleins gardent un focus blanc visible au clavier.
2. Grille : contour et ombre accentués, poignée visée remplie, infobulle d’action et curseur cohérent sur toute la zone de redimensionnement. Le survol s’efface au départ de la souris, au défilement et lors d’une nouvelle disposition. La bande de ratio utilise un contour pointillé au survol, distinct de la sélection.

Les effets réutilisent les couleurs des thèmes et la transition existante de 120 ms. Les cartes et boutons ne changent pas de dimensions. Les règles, les données, les heures, les exports PDF et le moteur de génération restent identiques.

## Aperçus

- [Journée récente survolée](survol-accueil-0.5.2.png).
- [Grille sans survol de quart](survol-grille-avant-0.5.2.png).
- [Poignée de quart survolée](survol-grille-0.5.2.png).

Captures Qt6 réelles avec des données fictives. Le scénario vérifie que l’horaire et son état de sauvegarde restent identiques après survol.

## Vérification

Les 62 tests ciblés de la grille, des commandes, du tableau de bord, des thèmes, de l’accueil et des animations réussissent. Le nouveau cas vérifie que le curseur de la poignée correspond à sa zone réellement cliquable, puis qu’un glissement ajuste la fin d’une minute sans modifier directement le modèle. Les cas existants vérifient le verrouillage, la consultation, le clavier, les thèmes et les mouvements réduits. Les contrôles natifs requis par la distribution sont exécutés avant publication ; les preuves figurent dans [État des vérifications](ETAT_VERIFICATION.md).

## Hypothèses et limites

- Les retours sont discrets : fond, contour, poignée et curseur. Aucun agrandissement des cartes ou déplacement animé des contrôles.
- Les informations essentielles restent affichées ou accessibles au clavier. Les infobulles complètent les libellés ; elles ne remplacent pas les heures et les alertes.
- L’option de désactivation des animations supprime les transitions, avec conservation du retour statique au survol et du focus. Aucun nouveau réglage ajouté.
- Aucune modification des ratios, pauses, disponibilités, rangs, maximums, sauvegardes ou PDF. Les essais physiques avec souris et lecteur d’écran sur le poste de l’école restent à réaliser.

## Fichiers modifiés

- Interface : `gardeplan/app.py`, `gardeplan/ui/motion.py`, `gardeplan/ui/theme.py`, `gardeplan/ui/home.py`, `gardeplan/ui/main_window.py`, `gardeplan/ui/calendar.py`, `gardeplan/ui/coverage_band.py`.
- Vérification : `tests/test_calendar.py`, `tests/test_motion.py`.
- Version et documentation : `gardeplan/__init__.py`, `pyproject.toml`, `CHANGELOG.md`, `README.md`, `docs/GUIDE.md`, ce rapport, `docs/ETAT_VERIFICATION.md`, les trois captures et `.github/release-request.json`.
