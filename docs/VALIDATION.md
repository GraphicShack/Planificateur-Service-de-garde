# Validation de cette livraison

## Exécuter les tests

Depuis la racine du projet :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest -q
```

Les modules Qt et OR-Tools sont ignorés par pytest si leur bibliothèque est absente. Une livraison finale complète doit donc être testée avec les dépendances installées ; un rapport comportant des tests ignorés ne valide pas les fonctions correspondantes.

## Couverture des essais

| Cas obligatoire | Test |
| --- | --- |
| Quart de 1 h 42 | `test_shift_one_hour_forty_two_minutes` |
| Déplacement conservant la durée | `test_move_preserves_exact_duration_and_break_position` et Qt `test_move_exact_minutes_keeps_duration` |
| Redimensionnement à la minute | `test_resize_to_arbitrary_minute` et Qt `test_resize_top_by_one_minute_emits_exact_change` |
| Deux éducatrices dans le même groupe | `test_valid_continuous_day_with_two_educators` |
| Une seule éducatrice | `test_one_educator_is_blocking` |
| Dépassement du ratio 1/20 | `test_ratio_twenty_requires_third_educator_at_41` |
| Conflit de local et capacité | `test_room_conflict_capacity_and_unavailable` |
| Activité extérieure | `test_outdoor_activity_location_changes_leave_shifts_exact` |
| Activité indépendante des horaires | Test précédent et Qt `test_activity_move_is_independent` |
| Pause provoquant un manque | `test_pause_creates_coverage_gap` |
| Buffer rémunéré hors couverture | `test_paid_preparation_is_not_pupil_coverage` |
| Génération impossible | `test_impossible_generation_explains_failure` |
| Génération valide et verrouillage | `test_generation_has_real_validated_proposal`, `test_locked_shifts_unchanged` |
| Sauvegarde et réouverture | `test_save_reopen_exact_minutes_and_named_day` |
| Archivage et restauration | `test_archival_and_restore_create_new_version` |
| Exports PDF réels | `test_all_pdf_exports_are_real_pdf_documents` |
| Fonctionnement hors ligne | `test_core_operations_work_with_network_disabled` |
| Ouverture/fermeture à deux | `test_opening_and_closing_require_two` |
| Aucun trou dans la journée | `test_no_school_coverage_hole` |
| Quinze minutes de relève | `test_replacement_needs_fifteen_minutes_shared_presence` |
| Journée avec nom personnalisé | `test_named_day_roundtrip`, `test_pdf_contains_named_day_and_exact_times` |
| Nombre de groupes selon inscriptions | `test_daily_registrations_create_groups_without_touching_other_days` |
| Formulaires réellement acceptés | `test_forms.py`, clic sur le bouton Enregistrer et résultat vérifié |
| Refus des valeurs invalides | Tests de minutes non entières, périodes chevauchées, absence de groupe/lieu et buffers invalides |
| Conservation en cas de fichier verrouillé | `test_file_safety.py` |
| Protection des anciennes versions | Tests des déclencheurs SQLite et d'import de photographie altérée |

## Vérification sur le poste de destination

Exécuter aussi le parcours de prise en main de `EXIGENCES.md` avec souris et imprimante. Vérifier spécialement la lisibilité du calendrier avec le nombre réel de groupes et d'éducatrices, les PDF en noir et blanc, la sauvegarde sur le dossier choisi et les messages lorsque le PDF est déjà ouvert.

L'exécutable Windows est produit par `scripts/build-windows.ps1` ou le workflow fourni. Il doit être lancé et essayé sur Windows avant d'être présenté comme testé sur cette plateforme.
