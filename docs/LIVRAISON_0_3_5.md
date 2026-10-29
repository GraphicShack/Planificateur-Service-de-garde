# Livraison 0.3.5 — chargement de la génération

Le bouton **Générer l’horaire** ouvre maintenant une fenêtre de chargement avec un cercle animé, un message clair et le temps écoulé. Le cercle adopte l’accent du thème. L’option Animations discrètes est respectée ; sans mouvement, le texte et le compteur confirment que le calcul est en cours.

Le fil de génération existant reste indépendant de l’interface. La fenêtre se ferme à la réception d’une proposition, d’une impossibilité ou d’une erreur, puis ses animations et son compteur sont arrêtés. L’application attend la fin du fil pour réactiver les commandes. Aucune proposition n’est appliquée sans la confirmation existante.

## Vérification

Cinq tests ciblés couvrent l’animation active, sa désactivation, les trois issues de génération, la conservation de l’horaire et le nettoyage des minuteurs. Les tests existants d’acceptation/refus de proposition et d’annulation restent applicables. L’aperçu est capturé pendant une génération réelle dans l’application Qt6, avec des données fictives. Les résultats de la suite complète et des contrôles Windows/Mac sont consignés dans [État des vérifications](ETAT_VERIFICATION.md).

## Hypothèses et limites

- Le solveur ne fournit pas de pourcentage fiable ; seul le temps réellement écoulé est affiché. Aucun faux avancement ou résultat simulé n’est ajouté.
- Aucun bouton d’annulation n’est ajouté au solveur. La fenêtre ne se ferme pas avec Échap pendant le calcul, afin de garder son état visible.
- Les règles métier, les horaires existants, le PDF et les préférences de thème restent inchangés. Les données personnelles ne sont pas utilisées dans l’aperçu.
- Les essais physiques sur le poste de l’école et l’annulation coopérative du solveur restent hors de cette modification.

## Fichiers modifiés

- `gardeplan/ui/loading.py`
- `gardeplan/ui/main_window.py`
- `tests/test_loading.py`
- `scripts/test_release_notes.py` : le contrôle exige des changements documentés pour la version courante, sans imposer le mot « Accueil » à chaque nouvelle release.
- `gardeplan/__init__.py`, `pyproject.toml`
- `CHANGELOG.md`, `README.md`, `docs/GUIDE.md`
- `docs/chargement-horaire.png`, `docs/LIVRAISON_0_3_5.md`, `docs/ETAT_VERIFICATION.md`
- `.github/release-request.json`
