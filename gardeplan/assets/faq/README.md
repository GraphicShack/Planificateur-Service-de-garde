# Captures de la FAQ

Ces 14 images proviennent des vrais écrans Qt de l’application. Les noms, les
effectifs et la journée du 2 novembre 2026 sont fictifs. Aucune base personnelle
n’est ouverte pour les produire. La journée est générée puis validée avec le
moteur existant ; les alertes sont illustrées avec une pause non payée ajoutée
uniquement à une copie temporaire.

Depuis la racine du projet, avec les dépendances de développement installées :

```bash
QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=1.5 python scripts/capture_faq.py
```

Le script utilise une base SQLite temporaire et remplace les PNG de ce dossier.
Il peut prendre une trentaine de secondes pour générer la journée d’exemple.
Une proposition peut varier entre deux exécutions du moteur d’optimisation.

Les images montrent l’accueil, les inscriptions, la grille, le formulaire de
quart, les pauses, le profil, la proposition, le bilan, les alertes, une carte
d’équipe, le menu Dossier, l’aperçu PDF, la mise à jour et les réglages
d’affichage. Les légendes et leur association aux questions se trouvent dans
`gardeplan/ui/faq_media.py` et `gardeplan/ui/faq.py`.

Les PNG sont inclus dans le paquet Python et dans les constructions portables
Windows et Mac. Leur consultation ne nécessite ni navigateur ni connexion.
