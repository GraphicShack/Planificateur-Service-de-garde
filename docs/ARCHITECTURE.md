# Architecture du Planificateur — Service de garde

Le Planificateur — Service de garde est une application de bureau Python 3 / PySide6. Toutes les données sont locales : aucun compte, serveur ni abonnement n'est nécessaire au fonctionnement. Les téléchargements de bibliothèques concernent uniquement la préparation ou la compilation du logiciel.

## Modules

| Module | Responsabilité |
| --- | --- |
| `models.py` | Éducatrices, groupes, effectifs, locaux, quarts, activités, paramètres et journées ; compatibilité des semaines historiques ; conversion JSON contrôlée. |
| `daily.py` | Création et duplication des journées ; extraction conservatrice des semaines historiques. |
| `identity.py` | Palette distincte pour chaque nouvelle éducatrice, étendue au-delà de onze profils. |
| `planning.py` | Préparation d’une journée selon les inscriptions et la taille souhaitée des groupes. |
| `validation.py` | Contraintes obligatoires, avertissements et intervalles de couverture. |
| `optimizer.py` | Proposition par OR-Tools CP-SAT ; conservation des quarts verrouillés et validation finale. |
| `storage.py` | SQLite, versions complètes, duplication, restauration, sauvegarde et import local. |
| `data_paths.py` | Données du dossier portable ou emplacement historique ; déplacement du dossier sans reconfiguration. |
| `pdf.py` | Écriture atomique du PDF quotidien et compatibilité des anciennes fonctions d’export. |
| `pedagogical_pdf.py` | Grille lettre paysage du modèle fourni, huit lignes par page, géométrie exacte et interruptions vides. |
| `ui/calendar.py` | Calendrier quotidien, manipulation graphique et repères d'alertes. |
| `ui/forms.py` | Formulaires simples et réglages détaillés. |
| `ui/day_selector.py` | Sélection unique, grille accessible, navigation au clavier et respect des limites de dates. |
| `ui/flow_layout.py` | Réorganisation des contrôles sans réduire les textes ni leurs zones cliquables. |
| `ui/theme.py` | Palette Atelier commune, styles de sélection et mesure de contraste. |
| `ui/main_window.py` | Coordination de l'interface, annulation, sauvegarde et commandes. |
| `ui/visuals.py` | Logo et pictogrammes SVG locaux, rendus pour les écrans à haute densité. |
| `ui/localization.py` | Locale française et traduction des boutons standard Qt. |
| `app.py` | Démarrage de Qt et gestion du chemin local de la base. |

## Temps et couverture

Les heures sont stockées en minutes entières depuis minuit. Les intervalles sont semi-ouverts : un quart de 7 h 13 à 8 h 55 vaut `535 - 433 = 102` minutes. Les pixels peuvent être fractionnaires pour dessiner le calendrier ; les durées persistées ne le sont jamais.

`Shift.start` et `Shift.end` délimitent la présence. Les buffers avant/après sont inclus à l'intérieur de cette présence. Ils peuvent être rémunérés, mais sont exclus de la couverture des enfants. Les pauses sont également exclues de la couverture. Le calcul du temps rémunéré retire l'union des intervalles non rémunérés afin d'éviter une double soustraction.

Les contraintes sont évaluées à chaque changement d'état de la journée, donc sur tous les intervalles où la couverture peut changer, avec une précision exacte à la minute. Une activité possède ses propres horaires et son propre lieu. Son déplacement ne déplace aucun quart.

## Règles initiales

Le service ouvre à 7 h et ferme à 17 h 30. Deux éducatrices doivent être présentes de 6 h 50 à 7 h pour préparer l'ouverture, et de 17 h 30 à 17 h 35 pour la fermeture. Une relève dans un groupe exige au moins quinze minutes de présence commune. Aucun trou de couverture du service ouvert n'est autorisé. Chaque groupe actif exige `max(2, plafond(effectif / 20))` éducatrices, selon les règles demandées ; le ratio reste configurable et n'est pas présenté comme une disposition réglementaire.

Les effectifs et périodes d'ouverture sont définis par groupe et journée. L’outil de préparation répartit les inscriptions selon une taille de groupe souhaitée, réglable et indépendante du ratio d’encadrement. Les groupes restent ensuite modifiables manuellement ; cette taille souhaitée ne représente pas une limite réglementaire. Le nom personnalisé est stocké dans la photographie de la journée.

## Versions et fichiers

La distribution principale est un dossier portable avec son exécutable, ses bibliothèques, un marqueur `portable.mode` et un sous-dossier `donnees`. Le lancement détecte automatiquement ce mode ; il conserve SQLite, l'historique et les sauvegardes dans `donnees`, sans installation ni enregistrement système par l'application. Sur macOS, le bundle déclare aussi son intention portable dans `Info.plist` ; les données restent à côté du `.app`, jamais à l'intérieur du bundle signé. Les anciens chemins de profil sont conservés pour les installations historiques qui n'utilisent pas le mode portable.

Chaque sauvegarde conserve une photographie complète de la journée, incluant les profils et paramètres. Une publication reste consultable dans l'historique même lorsque de nouveaux brouillons sont enregistrés. Une restauration produit une nouvelle version. La sauvegarde de sécurité utilise l'API de sauvegarde SQLite ; l'import vérifie la base avant remplacement et conserve une copie de sécurité de l'ancienne base.

## Limites d'optimisation

La génération cherche une solution dans un ensemble de quarts candidats. Elle optimise les contraintes et pondérations implémentées, puis vérifie la proposition avec le moteur de validation. Un échec de recherche dans ces candidats ne prouve pas l'impossibilité mathématique de tous les horaires imaginables. L'interface affiche l'explication du moteur et permet l'édition manuelle. La proposition ne remplace l'horaire qu'après acceptation.

## Vérification et livraison

Les tests contrôlent les minutes, les contraintes de couverture, les lieux, les sauvegardes, les versions et les PDF. Les opérations locales sont également exécutées avec l'accès aux sockets désactivé. Les tests d'interface utilisent le moteur Qt hors écran. Une exécution hors écran ne remplace pas un essai avec souris et imprimante sur un poste Windows.

Les scripts `scripts/build-windows.ps1` et `scripts/build-macos.sh` compilent nativement avec PyInstaller. Ils contrôlent l'exécutable préparé puis le même logiciel après extraction du ZIP, avec le moteur Qt natif, SQLite, PDF et CP-SAT. Ils exigent une écriture réelle des données à côté du programme. Le dossier portable doit rester complet.

## Dates et compatibilité (0.2)

`Week` reste le nom interne de l’enveloppe pour lire les anciennes sauvegardes. Un horaire quotidien possède `planning_date` et utilise exclusivement l’indice local 0 pour tous ses blocs, périodes et absences ; la date peut être n’importe quel jour civil. `active_days` limite validation, génération et PDF à cette seule journée. La date affichée vient de `planning_date`, jamais du nom historique du champ `monday`.

La clé SQLite d’une journée est `day:AAAA-MM-JJ`, distincte de celle d’une ancienne semaine. Les versions, statuts, duplications et restaurations sont ainsi indépendants. Le schéma 2 conserve sans modification les contenus/checksums des anciennes versions. La migration crée une copie SQLite au format 1 avant de mettre à jour les métadonnées ; l’import accepte les deux formats et conserve sa copie de sécurité habituelle.

Les profils d’une nouvelle journée reprennent leurs objectifs journaliers si le modèle était quotidien. Un objectif hebdomadaire historique n’est jamais divisé ou réinterprété implicitement : sa cible journalière reste à définir. Les rangs quotidiens sont limités à 1–11 ; aucune contiguïté ni présence de tous les rangs n’est requise. Les couleurs existantes ne sont pas réattribuées lors d’une édition ou d’un changement de date.

## PDF unique selon la référence

Le parcours utilisateur expose un export général unique. Les anciennes fonctions d’export restent lisibles par les tests de compatibilité et ne sont plus proposées dans l’interface. Le rendu quotidien utilise Canvas/ReportLab, des éléments vectoriels et des polices embarquées. Arial du système est utilisé s’il est disponible ; sinon une police libre compatible avec ses métriques est incluse, dérivée de Liberation Sans et renommée Planificateur Sans, avec sa licence SIL-OFL.

Les coordonnées reprennent la référence : page 792 × 612 pt, marges de 30 pt, colonne des noms de 163 pt, grille de 569 pt et huit lignes. Les durées entières sont converties en positions PDF uniquement au dessin. `working_intervals` retire toutes les pauses, même rémunérées ; aucun objet de légende ni libellé de pause n’est dessiné. La palette du modèle identifie les groupes sur toutes les pages, indépendamment de la couleur personnelle des éducatrices.

## Interface centrée sur les horaires (0.2.1)

Le bouton Dossier réutilise les commandes transactionnelles existantes. Les activités et les locaux historiques restent dans les photographies ; ils ne sont plus exposés dans la planification quotidienne et n’interviennent plus dans sa validation ou sa génération. Le composant de calendrier conserve son mode historique pour les anciens tests et interfaces internes, mais la fenêtre principale masque ces blocs.

Le sélecteur remplace le QDateEdit principal en conservant une API de date et un signal dateChanged. La sélection ne change qu’à la confirmation d’un jour. La navigation des mois/années ne charge pas de planning ; une erreur de sauvegarde rétablit la date affichée. Les limites 1752–9999 et la sélection simple restent conservées. Les fenêtres réduites utilisent la réorganisation et le défilement plutôt que des polices plus petites.

La présence quotidienne doit rester dans la plage définie par l’ouverture moins son buffer et la fermeture plus son buffer, soit 6 h 50–17 h 35 avec les paramètres demandés. Le calendrier n’arrondit plus ces bornes aux heures entières ; le PDF les affiche explicitement.

## Mise à jour portable (0.5.0)

`portable_package.py` décrit le format `version-portable.json` (schéma 1) : identité de l’application, version, plateforme, architecture, exécutable, empreintes des fichiers et liens internes Mac. La fabrication écrit cet inventaire après la signature locale du bundle, puis produit un ZIP canonique. Le manifeste et les données restent hors du bundle signé. L’analyse refuse les chemins ambigus, les traversées, les liens externes, les fichiers personnels, les plateformes incompatibles et les versions non supérieures. L’extraction vérifie le ZIP choisi et chaque fichier, dans un dossier temporaire situé sur le volume de destination ; un renommage termine la préparation.

`updater.py` copie la base avec l’API SQLite de sauvegarde, les préférences et les dossiers de sauvegarde connus. `retour-avant-maj` conserve un état vérifié ; `mise-a-jour.json` conserve la provenance et l’état d’activation. Aucun fichier de l’ancienne version n’est remplacé. Tant que l’activation reste en attente, le premier démarrage reprend en lecture seule la dernière base source après acquisition de ses verrous. Cette étape évite de perdre un travail effectué après une préparation laissée pour plus tard. Les dossiers frères peuvent être déplacés ensemble. Après activation, les versions utilisent des bases indépendantes.

Le retour vérifie l’inventaire de l’ancien programme et l’empreinte de l’état sauvegardé, puis prépare encore un dossier séparé. Le travail plus récent est conservé et sauvegardé séparément ; aucune migration inverse ni fusion n’est tentée. L’interface `ui/update.py` exécute l’analyse et la copie dans un fil de travail. Le redémarrage détaché utilise un environnement PyInstaller indépendant et n’est demandé qu’après une action explicite. Un échec de lancement conserve l’application courante ouverte.

`update_check.py` contrôle le vrai ZIP extrait sur les deux plateformes : préparation, changement de la source après préparation, lancement de la copie compilée, restauration et lancement de celle-ci. `prepare_release.py` exige ce résultat avant publication. L’intégrité par empreinte ne remplace pas une signature d’éditeur. Le logiciel ne recherche ni ne télécharge des mises à jour sur Internet.

## Bilan, session et continuité (0.5.0)

`proposal_summary.py` réutilise les alertes visibles, la couverture, les heures rémunérées et les souhaits du planificateur. Le bilan ne possède pas sa propre interprétation des ratios. Une interruption sépare deux intervalles de présence fusionnés ; les pauses internes ne deviennent pas des horaires coupés. Les personnes absentes à la journée sont exclues des personnes sans heures. `session_user.py` fournit uniquement un nom local nettoyé pour l’accueil, affiché en texte brut.

Pour une journée, `optimizer_priorities.py` privilégie désormais la participation, puis le nombre de personnes avec un horaire coupé et la durée des interruptions, avant le coût rémunéré et les objectifs rang par rang. `preferences.cp_interruptions` utilise les mêmes intervalles de présence : des affectations adjacentes dans deux groupes ne créent pas de trou, et une pause dans un quart reste une pause. La continuité est un objectif souple ; les disponibilités, les verrous et les plafonds restent des contraintes. Les limites de temps sont toujours signalées et aucune proposition n’est appliquée sans confirmation.
