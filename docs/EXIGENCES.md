# Vérification des exigences

Ce document distingue les contrôles automatisables du contrôle de prise en main sur un poste Windows. Un fichier de test présent dans le projet n'est pas une preuve de réussite : consulter le résultat de `python -m pytest -q` pour l'exécution concernée.

| Demande | Mise en œuvre / contrôle |
| --- | --- |
| Application locale sans compte ni serveur | Application Qt et base SQLite ; test d'opérations avec sockets bloqués. |
| Architecture modulaire et maintenable | Modèles, validation, optimisation, stockage, PDF et interface séparés ; `ARCHITECTURE.md`. |
| Interface entièrement en français | Fenêtre principale, calendrier, formulaires et messages ; prise en main à contrôler sous Windows. |
| Barre supérieure et statuts | Sélection de semaine, Jour/Semaine et commandes dans la fenêtre principale. |
| Panneau permanent des éducatrices | Profils, heures et progression dans la fenêtre principale ; panneau réductible. |
| Profil complet | Ancienneté, heures cibles/garanties/maximales, disponibilité/absence, préférences, notes, couleur, activité. |
| Calendrier quotidien continu | Groupes en colonnes, axe horaire et blocs proportionnels dans `ui/calendar.py`. |
| Plusieurs éducatrices dans un groupe | Couloirs parallèles dans le calendrier ; contrôle de couverture avec deux éducatrices. |
| Quarts à n'importe quelle minute | Stockage entier ; tests du quart de 1 h 42, déplacement et redimensionnement. |
| Glisser depuis le panneau | MIME local ; test Qt de dépôt à la minute exacte. |
| Déplacement vertical/horizontal | Signaux de modification avec heures et groupe ; gestes à vérifier sous Windows. |
| Redimensionnement haut/bas | Poignées du bloc ; test Qt du bord supérieur d'une minute. |
| Double-clic précis et infobulles | Formulaire du bloc et infobulle horaire ; contrôle de prise en main. |
| Magnétisme 1/5/15/sans et zoom | Options du calendrier ; durées entières même sans magnétisme. |
| Vue des cinq jours | Vue Semaine et sélection d'un jour ; test Qt de sélection. |
| Nom personnalisé d'une journée | Stocké dans la semaine ; affiché dans les vues/PDF ; tests de persistance et extraction PDF. |
| Groupes et effectifs variables | Périodes quotidiennes avec effectif ; ratio et minimum configurables. |
| Ratio 1/20, minimum deux | `max(2, plafond(effectif/ratio))` ; test 40/41 enfants et groupe fermé. |
| Nombre de groupes selon les inscriptions | Préparation automatique selon les inscriptions et la taille souhaitée, puis modification manuelle ; tests `test_planning.py`.  |
| Ouverture à deux à 6 h 50 | Contrôle obligatoire de présence avant ouverture de 7 h. |
| Fermeture à deux à 17 h 35 | Contrôle obligatoire de présence après fermeture de 17 h 30. |
| Aucun trou dans la journée | Contrôle de continuité du service et de chaque groupe actif. |
| Relève de quinze minutes | Contrôle de présence commune de la personne entrante et d'une personne sortante ; test d'échec sans chevauchement. |
| Activités indépendantes des quarts | Modèles/blocs distincts ; tests de changement de lieu et de déplacement d'activité. |
| Locaux personnalisables | Capacité, partage, disponibilité et intérieur/extérieur. |
| Conflits d'activité et local | Validation d'incompatibilité, capacité, indisponibilité et couverture. |
| Buffers et pauses exacts | Présence, rémunération et couverture séparées ; union des temps non rémunérés. |
| Heures recalculées et écarts | `totals` et rafraîchissement de l'interface après modification. |
| Erreurs et avertissements lisibles | Issues avec journée/intervalle/groupe et conseil ; bandes et bordures d'erreur dans le calendrier. |
| Publication refusée en cas d'erreur | Vérification à l'enregistrement de l'état publié ; brouillon invalide autorisé. |
| Génération réelle sous contraintes | CP-SAT, candidats, quarts verrouillés et validation finale ; tests faisable/impossible/verrouillage. |
| Proposition avant remplacement | Acceptation dans l'interface ; aucune mutation de la semaine par `generate`. |
| Ancienneté et préférences | Pondérations configurables et avertissements ; politique locale à préciser dans les paramètres. |
| Sauvegarde et réouverture | SQLite, test de photographie exacte et nom de journée. |
| Versions et publication figée | Photographies complètes, déclencheurs empêchant UPDATE/DELETE ; tests de conservation. |
| Duplication, archive et restauration | Versions nouvelles ; tests d'archivage/duplication/restauration. |
| Export/import de sauvegardes | Sauvegarde SQLite contrôlée ; test de rejet de corruption et de checksum modifié. |
| PDF général, individuel, tous et regroupé | Export ReportLab ; vérification de documents PDF et extraction de contenu. |
| Aperçu et impression | Accès dans l'interface ; vérifier la prévisualisation et l'impression sur le poste cible. |
| Noir et blanc | Horaires et noms restent présents dans les tableaux sans dépendre uniquement des couleurs. |
| Annuler une action | Commandes d'annulation de la fenêtre principale ; essai de prise en main nécessaire. |
| Exécutable Windows sans installation | ZIP portable avec `Planificateur-SDG.exe`, bibliothèques incluses et données à côté ; contrôle du dossier et du ZIP extrait. |
| Construction Mac | Workflow et script natifs, application `.app` dans un ZIP portable, données hors du bundle signé. |
| Interface modernisée et logo choisi | Identité visuelle locale, pictogrammes SVG, recherche des éducatrices, commandes regroupées et calendrier sauge ; tests Qt6 natifs. |

## Points à garder explicites

- La taille souhaitée d’un groupe dans l’outil d’inscriptions est indépendante du ratio élèves/éducatrice. La valeur par défaut peut être ajustée selon l’organisation du service.
- Le moteur automatique choisit parmi des candidats. Un échec de cette recherche ne prouve pas l'impossibilité de tout horaire théorique ; les diagnostics le distinguent.
- Une règle inscrite uniquement comme note libre dans les « restrictions particulières » n'est pas interprétée automatiquement. Les contraintes que le moteur applique doivent être saisies dans les champs structurés de disponibilité, absence, limites, buffers et pauses.
- La politique de pause n'est pas présumée conventionnelle ou réglementaire. La durée requise et son seuil sont configurables ; une durée à zéro désactive cette règle.
- La version conserve les profils et paramètres de la semaine. Pour une ancienne semaine, les profils archivés sont ceux de cette photographie.
- Les premières versions natives Windows et Mac ont été compilées et vérifiées sur GitHub Actions. Les ZIP portables doivent provenir de leur propre exécution réussie ; les résultats sont détaillés dans `ETAT_VERIFICATION.md`. La prise en main sur le poste de l’école reste nécessaire.

## Contrôle de prise en main sur Windows

1. Ouvrir une nouvelle semaine, nommer une journée et créer un groupe avec ses effectifs.
2. Ajouter deux éducatrices, puis les glisser dans le même groupe ; vérifier leurs deux blocs visibles.
3. Régler un quart à 7 h 13–8 h 55, déplacer son début d'une minute et vérifier son total.
4. Changer le groupe par glissement et annuler l'action.
5. Créer une relève insuffisante, lire l'alerte et corriger le chevauchement à quinze minutes.
6. Ajouter une pause et vérifier l'apparition d'un manque de couverture.
7. Déplacer une activité entre deux locaux sans changement des heures de travail.
8. Consulter la vue Semaine, choisir une journée et agrandir le calendrier.
9. Générer une proposition, la refuser, puis en accepter une autre ; vérifier les quarts verrouillés.
10. Sauvegarder, fermer, rouvrir, consulter une archive et restaurer une ancienne version.
11. Exporter et imprimer un horaire général et individuel en noir et blanc.
12. Déconnecter le réseau et répéter la sauvegarde, la génération et les exports.
