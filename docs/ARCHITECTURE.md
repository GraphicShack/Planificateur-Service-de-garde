# Architecture du Planificateur — Service de garde

Le Planificateur — Service de garde est une application de bureau Python 3 / PySide6. Toutes les données sont locales : aucun compte, serveur ni abonnement n'est nécessaire au fonctionnement. Les téléchargements de bibliothèques concernent uniquement la préparation ou la compilation du logiciel.

## Modules

| Module | Responsabilité |
| --- | --- |
| `models.py` | Éducatrices, groupes, effectifs, locaux, quarts, activités, paramètres et semaines ; conversion JSON contrôlée. |
| `planning.py` | Préparation d’une journée selon les inscriptions et la taille souhaitée des groupes. |
| `validation.py` | Contraintes obligatoires, avertissements et intervalles de couverture. |
| `optimizer.py` | Proposition par OR-Tools CP-SAT ; conservation des quarts verrouillés et validation finale. |
| `storage.py` | SQLite, versions complètes, duplication, restauration, sauvegarde et import local. |
| `data_paths.py` | Données du dossier portable ou emplacement historique ; déplacement du dossier sans reconfiguration. |
| `pdf.py` | PDF général, individuel et regroupé avec ReportLab. |
| `ui/calendar.py` | Calendriers Jour/Semaine, manipulation graphique et repères d'alertes. |
| `ui/forms.py` | Formulaires simples et réglages détaillés. |
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

Les effectifs et périodes d'ouverture sont définis par groupe et journée. L’outil de préparation répartit les inscriptions selon une taille de groupe souhaitée, réglable et indépendante du ratio d’encadrement. Les groupes restent ensuite modifiables manuellement ; cette taille souhaitée ne représente pas une limite réglementaire. Le nom personnalisé d'une journée est stocké avec la semaine.

## Versions et fichiers

La distribution principale est un dossier portable avec son exécutable, ses bibliothèques, un marqueur `portable.mode` et un sous-dossier `donnees`. Le lancement détecte automatiquement ce mode ; il conserve SQLite, l'historique et les sauvegardes dans `donnees`, sans installation ni enregistrement système par l'application. Sur macOS, le bundle déclare aussi son intention portable dans `Info.plist` ; les données restent à côté du `.app`, jamais à l'intérieur du bundle signé. Les anciens chemins de profil sont conservés pour les installations historiques qui n'utilisent pas le mode portable.

Chaque sauvegarde conserve une photographie complète de la semaine, incluant les profils et paramètres. Une publication reste consultable dans l'historique même lorsque de nouveaux brouillons sont enregistrés. Une restauration produit une nouvelle version. La sauvegarde de sécurité utilise l'API de sauvegarde SQLite ; l'import vérifie la base avant remplacement et conserve une copie de sécurité de l'ancienne base.

## Limites d'optimisation

La génération cherche une solution dans un ensemble de quarts candidats. Elle optimise les contraintes et pondérations implémentées, puis vérifie la proposition avec le moteur de validation. Un échec de recherche dans ces candidats ne prouve pas l'impossibilité mathématique de tous les horaires imaginables. L'interface affiche l'explication du moteur et permet l'édition manuelle. La proposition ne remplace l'horaire qu'après acceptation.

## Vérification et livraison

Les tests contrôlent les minutes, les contraintes de couverture, les lieux, les sauvegardes, les versions et les PDF. Les opérations locales sont également exécutées avec l'accès aux sockets désactivé. Les tests d'interface utilisent le moteur Qt hors écran. Une exécution hors écran ne remplace pas un essai avec souris et imprimante sur un poste Windows.

Les scripts `scripts/build-windows.ps1` et `scripts/build-macos.sh` compilent nativement avec PyInstaller. Ils contrôlent l'exécutable préparé puis le même logiciel après extraction du ZIP, avec le moteur Qt natif, SQLite, PDF et CP-SAT. Ils exigent une écriture réelle des données à côté du programme. Le dossier portable doit rester complet.
