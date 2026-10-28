# Livraison 0.3.4 — apparence et fluidité

## Changements

1. Transitions de navigation de 160 ms, contours de boutons de 120 ms. Les pages changent immédiatement : les clics et le focus ne sont jamais bloqués par l’image de transition. Une navigation rapide interrompt le fondu précédent ; redimensionner ou masquer la vue libère la capture.
2. Intégration à l’accueil, à la planification et aux panneaux du côté gauche. Les heures et la géométrie des quarts restent immédiates.
3. Thèmes Forêt, Bleu, Prune et Ardoise, accent personnalisé et désactivation des animations dans Réglages → Affichage. Application immédiate aux surfaces de navigation, formulaires, dates, boutons et sélections. Les couleurs d’alerte, d’éducatrice, de groupe et du PDF conservent leur rôle.
4. Préférences locales dans `interface.json`, à côté de la base : écriture atomique, tolérance à un fichier endommagé, explication si l’écriture est impossible. Les préférences n’altèrent aucune version d’horaire. Les options d’affichage défilent sur les petits écrans ; Fermer reste hors de la zone défilante.

5. Nettoyage des effets quand une fenêtre est masquée, réactivation à la réouverture et suppression de la modification des styles depuis un événement d’affichage. Cette dernière pouvait réentrer dans le moteur de styles Qt après des ouvertures répétées.

Chaque étape possède son commit. Les notes de version sont reprises automatiquement dans la release GitHub depuis [CHANGELOG.md](../CHANGELOG.md).

## Vérifications

Neuf nouveaux tests ciblés vérifient la navigation immédiate, les clics pendant une transition, le focus, les changements rapides, le redimensionnement, la désactivation, le contraste, la conservation et la restauration des préférences, les erreurs de couleur et d’écriture et l’absence de modification des horaires. Le test des contrôles d’affichage existants suit leur déplacement dans la zone défilante. La suite complète et les contrôles portables natifs restent obligatoires avant publication ; leurs résultats sont consignés dans [État des vérifications](ETAT_VERIFICATION.md).

L’aperçu est capturé dans l’application Qt6 avec des données fictives. [Options d’apparence](themes-interface.png).

## Hypothèses et limites

- « Thème personnalisé » signifie une couleur d’accent personnalisée, avec surfaces claires et textes foncés. Les accents trop clairs sont foncés automatiquement pour assurer au moins 4,5:1 avec le texte blanc ; la couleur appliquée est affichée. Aucun thème sombre ni éditeur de feuille de styles n’est ajouté.
- Le logo conserve son identité. Les couleurs du personnel et des groupes, les alertes de sécurité et le PDF sont indépendants du thème.
- Les préférences sont conservées dans le dossier `donnees` du logiciel portable. Elles suivent la copie de ce dossier et restent séparées des exports/imports de sauvegardes SQLite.
- Les animations sont activées initialement et peuvent être désactivées manuellement. La détection automatique du réglage de réduction des mouvements du système n’est pas ajoutée.
- Aucun changement aux règles de couverture, au plafond de huit heures, aux rangs ou au solveur. Aucune mise à jour automatique, signature/notarisation Mac ou installation sur le poste de l’école ajoutée. Les essais physiques sur les machines de l’école restent à faire.

## Fichiers modifiés

- `gardeplan/ui/motion.py`
- `gardeplan/ui/appearance.py`
- `gardeplan/ui/main_window.py`
- `gardeplan/ui/calendar.py`
- `gardeplan/ui/date_field.py`
- `gardeplan/ui/enrolment.py`
- `gardeplan/ui/forms.py`
- `gardeplan/ui/home.py`
- `gardeplan/ui/inline_name.py`
- `gardeplan/ui/theme.py`
- `tests/test_motion.py`
- `tests/test_appearance.py`
- `tests/test_main_window.py`
- `gardeplan/__init__.py`, `pyproject.toml`
- `CHANGELOG.md`, `README.md`, `docs/GUIDE.md`
- `docs/LIVRAISON_0_3_4.md`, `docs/themes-interface.png`, `docs/ETAT_VERIFICATION.md`
- `.github/release-request.json`
