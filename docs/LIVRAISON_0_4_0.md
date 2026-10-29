# Livraison 0.4.0 — absences, corrections et préférences

## Périmètre livré

La version réunit les trois améliorations prioritaires retenues et le point 4 :

1. **Absence pour la journée en un clic** dans L’équipe, indépendante du statut actif. Les quarts non verrouillés sont retirés et les alertes se recalculent. Annuler restaure l’état précédent. Les quarts verrouillés restent visibles et bloquants jusqu’à correction manuelle.
2. **Correction ciblée** depuis une alerte de couverture. La recherche ajoute un remplacement ou prolonge un quart voisin non verrouillé, conserve les autres affectations et vérifie les disponibilités, les pauses, les buffers, la relève et les plafonds. Une modification couvrant toute la plage est préférée à plusieurs ajouts fragmentés ; les rangs départagent les remplacements compatibles.
3. **Comparaison avant/après** : quarts ajoutés, retirés ou modifiés, heures rémunérées et écarts par personne, alertes, grilles et explications. Des identifiants techniques différents ne créent pas de fausse modification. La proposition attend une confirmation et son application est annulable.
4. **Préférences individuelles** pour ouvrir, fermer, éviter les horaires coupés et partir à une heure souhaitée. Elles sont facultatives et optimisées rang par rang, après les contraintes, la participation, le coût utile, la continuité et les heures ; une fin plus tôt départage les solutions équivalentes.

Le style Atelier, les thèmes, les animations, le chargement, le PDF unique lettre paysage et le fonctionnement hors ligne sont conservés. Les règles restent : deux personnes au total de 6 h 50 à 7 h et de 17 h à 17 h 35, deux par groupe ouvert de 7 h à 17 h, ratio configurable 1/20, quinze minutes de relève et huit heures rémunérées maximum.

## Vérification

Les nouveaux tests couvrent les absences, la persistance et les dates indépendantes, les anciens snapshots sans nouveaux champs, les objectifs absents, l’annulation, les préférences dans le solveur et les formulaires, les comparaisons, les corrections à une ou plusieurs personnes, les extensions, l’ouverture, la fermeture, les verrous, les limites et la confirmation réelle via un fil de calcul.

Le contrôle du logiciel portable vérifie aussi ces fonctionnalités avec réseau interdit, y compris la correction d’une vraie pause et le dessin du comparateur. Le contrôle de publication exige ce nouveau résultat avant de proposer les ZIP. Les suites locale, Windows et Mac réussissent chacune 307 tests et six sous-cas de pagination. Les dix tests des scripts de publication réussissent également. Les exécutables sont vérifiés trois fois sur chaque plateforme, dont après extraction des ZIP, avec le nouveau contrôle obligatoire `daily_improvements`. La version 0.4.0 est publiée sur GitHub ; les résultats du SHA exact sont consignés dans [État des vérifications](ETAT_VERIFICATION.md).

## Aperçus

- [Planification et action d’absence](apercu-0.4.0.png)
- [Comparaison d’une correction réelle](comparaison-0.4.0.png)
- [Préférences dans le formulaire existant](formulaire-preferences-0.4.0.png)

Les captures Qt6 utilisent des données fictives. La comparaison montre volontairement qu’une correction ciblée peut laisser une autre alerte existante : le bouton précise alors Appliquer au brouillon et la publication reste bloquée.

## Hypothèses et limites

- L’absence rapide concerne une journée entière. Elle ne désactive pas le profil, ne modifie pas les disponibilités habituelles et n’est pas recopiée sur une nouvelle journée. Rendre disponible ne recrée pas les quarts retirés ; Annuler permet leur restauration complète. Les heures cibles et garanties ne sont pas exigées d’une personne absente ce jour-là ; aucune comptabilité de congé rémunéré n’est ajoutée.
- Une correction locale doit supprimer entièrement le déficit sélectionné sans nouvelle erreur bloquante. Elle peut conserver des erreurs préexistantes, signalées explicitement. La recherche gloutonne est limitée en temps et en nombre d’ajouts ; un échec ne démontre pas l’impossibilité de tous les découpages. Les alertes hors couverture restent manuelles.
- Les préférences ne remplacent jamais une disponibilité obligatoire. La génération reste une recherche bornée dans des candidats à minutes exactes ; elle signale une optimisation interrompue. Aucun optimal global n’est promis.
- Les anciens champs restent lisibles grâce aux valeurs par défaut et les archives SQLite ne sont pas réécrites. Une ancienne version du logiciel peut refuser les nouveaux champs enregistrés en 0.4.0 : gardez une copie de `donnees` avant mise à jour pour pouvoir revenir en arrière.
- Les modèles de journée, les sauvegardes automatiques externes, l’assistant de mise à jour et les ajouts d’impression proposés aux points 5 à 8 ne font pas partie du périmètre retenu. Aucun thème sombre, annulation du solveur ou signature/notarisation Mac ajouté. Les essais physiques à l’école restent à faire.

## Fichiers modifiés

- `gardeplan/staff_layout.py` : les personnes absentes ne sont pas proposées à de nouvelles affectations ; leurs quarts verrouillés restent visibles.
- `.github/release-request.json`
- `CHANGELOG.md`
- `README.md`
- `docs/ETAT_VERIFICATION.md`
- `docs/GUIDE.md`
- `docs/LIVRAISON_0_4_0.md`
- `docs/apercu-0.4.0.png`
- `docs/comparaison-0.4.0.png`
- `docs/formulaire-preferences-0.4.0.png`
- `gardeplan/__init__.py`
- `gardeplan/attendance.py`
- `gardeplan/comparison.py`
- `gardeplan/coverage.py`
- `gardeplan/daily.py`
- `gardeplan/installation_check.py`
- `gardeplan/models.py`
- `gardeplan/optimizer.py`
- `gardeplan/optimizer_priorities.py`
- `gardeplan/preferences.py`
- `gardeplan/repairs.py`
- `gardeplan/ui/forms.py`
- `gardeplan/ui/loading.py`
- `gardeplan/ui/main_window.py`
- `gardeplan/ui/proposal.py`
- `gardeplan/validation.py`
- `pyproject.toml`
- `scripts/prepare_release.py`
- `scripts/test_prepare_release.py`
- `tests/test_comparison.py`
- `tests/test_day_absence.py`
- `tests/test_repairs.py`
- `tests/test_shift_preferences.py`
