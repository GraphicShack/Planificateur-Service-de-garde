# Guide d'utilisation

## Un écran simple

L’équipe reste à gauche et le calendrier occupe le reste de l’écran. Les commandes courantes sont **Générer**, **Exporter PDF**, **Inscriptions**, **Ajouter** et **Vérifier**. La sauvegarde est automatique ; le bas de l’écran confirme son état.

- **Ajouter** propose un quart ou une activité.
- **Vérifier** ouvre le détail des alertes ; **Fermer** redonne toute la place au calendrier. La validation continue même lorsque ce panneau est fermé.
- **Menu → Organisation** contient les groupes, locaux, profils et règles.
- **Menu → Affichage** permet de régler le zoom, le magnétisme et la visibilité du panneau de l’équipe.
- **Menu** regroupe aussi l’annulation, la sauvegarde manuelle, le statut, l’historique et les sauvegardes locales.

## Préparer une journée pédagogique

1. Choisissez la **date exacte** avec les flèches, le calendrier ou Aujourd’hui. Chaque date possède son propre horaire, même si deux journées tombent dans la même semaine.
2. Cliquez sur le **+ de L’équipe**. Une couleur encore inutilisée est proposée automatiquement ; vous pouvez la changer dans le profil. Choisissez le **rang de 1 à 11** : le rang 1 est le plus ancien, et des rangs peuvent rester libres (1, 4, 9, par exemple). Aucun profil n’est renuméroté automatiquement.
3. Saisissez les heures cibles, garanties et maximales **pour cette journée**. Une cible de zéro signifie « à définir ». Précisez les disponibilités et absences si nécessaire.
4. Cliquez sur **Inscriptions** : indiquez le nombre d’enfants, la taille souhaitée des groupes et le nom facultatif de la journée. Les groupes sont préparés pour cette seule date. Le minimum de deux éducatrices et le ratio configuré restent contrôlés.
5. Ajoutez les locaux depuis l’icône de lieu à gauche si vous prévoyez des activités.

Une nouvelle date reprend les profils et paramètres utiles. Ses inscriptions, quarts et activités restent vides ; les absences de l’ancienne date ne sont pas recopiées. Pour reprendre aussi un horaire complet, utilisez **Menu → Journées et historique → Dupliquer cette journée** et choisissez une date vide.

## Planifier dans le calendrier

Glissez une éducatrice depuis l’équipe vers un groupe et l’heure souhaitée. Déplacez son bloc pour changer l’heure ou le groupe ; tirez son bord supérieur ou inférieur pour régler sa durée. Le double-clic ouvre les heures exactes, les buffers et les pauses. Saisir 7 h 13 à 8 h 55 produit 1 h 42, sans arrondi automatique.

Les couleurs pastel des blocs identifient les groupes ; les initiales colorées identifient les éducatrices. Le rang est visible dans chaque fiche de l’équipe et reste modifiable dans le profil.

**Menu → Affichage** propose le zoom, la journée entière et le magnétisme de 1, 5 ou 15 minutes, ou libre. Le calendrier affiche uniquement la journée choisie. Les objectifs et les totaux d’heures concernent cette journée.

Un quart verrouillé est conservé pendant la génération ; déverrouillez-le dans son formulaire pour le modifier.

## Ouverture, fermeture et relève

Pour une journée ouverte de 7 h à 17 h 30, prévoyez deux éducatrices dès 6 h 50 et deux jusqu'à 17 h 35. Les dix minutes de préparation avant l'ouverture et les cinq minutes après la fermeture sont des temps de présence rémunérés. Ils ne constituent pas de la couverture d'enfants.

Pour une relève à 12 h 30, l'éducatrice entrante peut commencer sa présence à 12 h 15 avec quinze minutes de préparation avant sa couverture de 12 h 30. L'éducatrice sortante reste présente pendant ces quinze minutes. Le besoin de couverture du groupe doit rester satisfait, même pendant les pauses et les relèves.

## Activités et locaux

Une activité se planifie séparément des quarts. Changer « Jeux extérieurs » de la cour au parc ne modifie pas les heures des éducatrices. Les conflits de lieu, capacités et disponibilités apparaissent dans les alertes. La responsabilité et la couverture découlent des affectations réellement présentes.

## Lire et corriger les alertes

Les erreurs empêchent la publication, mais permettent de sauvegarder un brouillon. Elles concernent notamment un manque de personnel, un chevauchement de groupes pour une même éducatrice, une indisponibilité ou un conflit de local. Les avertissements signalent les écarts d'heures ou préférences.

Après une modification, consultez le compteur **Vérifier** et cliquez dessus pour ouvrir la liste des alertes. Les messages indiquent la journée, l'intervalle et le groupe concernés, avec une piste de correction lorsqu'elle est disponible.

## Générer une proposition

Cliquez sur « Générer ». Le moteur respecte les contraintes obligatoires qu'il modélise et les quarts verrouillés, puis cherche à améliorer les heures et les préférences. Examinez la proposition avant de l'accepter. Si la recherche échoue, lisez l'explication ; vous pouvez modifier les disponibilités, effectifs ou quarts et recommencer. Un échec dans les candidats examinés ne signifie pas nécessairement qu'aucune solution manuelle n'existe.

## Sauvegarder, revenir en arrière et exporter

Sauvegardez régulièrement et utilisez l'export de sauvegarde locale avant un changement important. Les anciennes versions de chaque journée restent consultables dans **Menu → Journées et historique**. Une restauration crée une nouvelle version ; une duplication permet de réutiliser une journée. Une publication conserve sa photographie historique.

**Exporter PDF** enregistre directement un seul horaire général de la journée, sans choix de formats individuels. Le document reprend le modèle fourni : lettre paysage, titre à gauche, date à droite, colonne des noms puis grille 7 h–18 h avec repères de 30 minutes, huit éducateurs maximum par page. Les blocs indiquent leur groupe et leurs heures exactes ; un même groupe garde la même couleur sur toutes les pages. Les pauses, rémunérées ou non, et les interruptions restent simplement vides. Aucun compteur ni colonne d’activité n’est ajouté. **Menu → Aperçu avant impression** ouvre ce même document. Pour une sauvegarde informatique complète, utilisez la sauvegarde locale SQLite ; un PDF sert à consulter ou imprimer et ne remplace pas la base.

## Ouvrir la version portable, sans installation

Téléchargez le ZIP correspondant à votre ordinateur dans les [Releases du projet](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/latest). Ces fichiers sont publics et ne demandent pas de compte GitHub. Les fichiers « Source code » sont destinés au développement ; choisissez le ZIP **Windows-x64-Portable** ou **macOS-arm64-Portable**.

1. Décompressez le ZIP reçu dans un dossier ou sur une clé USB où vous pouvez enregistrer des fichiers.
2. Ouvrez le dossier **Planificateur-SDG** extrait.
3. Sous Windows, ouvrez **Planificateur-SDG.exe**. Sous Mac, ouvrez **Planificateur-SDG.app** depuis ce dossier.

Aucun programme d’installation, Python, compte ou téléchargement complémentaire n’est nécessaire. Ne lancez pas l’application directement dans le ZIP et gardez tous les fichiers ensemble, notamment **portable.mode** et le sous-dossier **donnees**. Sous Mac, ne déplacez pas seulement l’application dans Applications.

Vos horaires, éducatrices, archives et sauvegardes locales restent dans **donnees**, à côté de l’application. Fermez le logiciel avant de déplacer le dossier ou de retirer la clé USB. Le poste doit autoriser l’exécution de l’application et l’écriture dans le dossier choisi.

Pour une mise à jour, sauvegardez vos données, décompressez la nouvelle version dans un autre dossier et conservez votre ancien sous-dossier **donnees** dans le nouveau dossier portable. Ne remplacez jamais vos données par un dossier vide. Pour transférer une planification entre Windows et Mac, utilisez l’export et l’import de sauvegarde locale.

### Si macOS ouvre une copie temporaire

Depuis la version 0.1.2, le logiciel demande à macOS le chemin du dossier d’origine lorsqu’il s’exécute sous **AppTranslocation**. Il utilise alors le sous-dossier **donnees** d’origine, avec vos horaires existants.

Si ce chemin n’est pas disponible, une fenêtre demande de choisir le dossier portable. Sélectionnez le dossier extrait du ZIP qui contient **Planificateur-SDG.app** et **portable.mode**, puis confirmez. Ne choisissez pas le ZIP ni l’application seule. Le bouton Annuler ferme le logiciel sans créer de nouvelle base. Un dossier en lecture seule ou incomplet est refusé avec une explication.

Si vous utilisez encore la version 0.1.1 et voyez une erreur contenant « AppTranslocation » ou « Read-only file system », téléchargez la nouvelle version, extrayez le dossier complet dans Documents et ouvrez cette nouvelle application. Conservez votre ancien sous-dossier **donnees** si vous aviez déjà des horaires.

La préparation du fichier à remettre est décrite dans les procédures [Windows](DISTRIBUTION_WINDOWS.md) et [macOS](DISTRIBUTION_MACOS.md). Elle concerne la personne qui construit le logiciel.

## Retrouver les anciens horaires

Les anciennes semaines ne sont pas supprimées. Le menu **Consulter une journée** affiche leurs dates planifiées. À l’ouverture d’une date, ses quarts, activités, inscriptions et son nom sont repris dans un horaire quotidien séparé. L’ancienne photographie hebdomadaire reste intacte.

Les anciens objectifs hebdomadaires ne deviennent pas des obligations journalières : les cibles et garanties de la journée sont à définir dans les profils. Une copie de sécurité du fichier est créée avant la mise à niveau du format de données. La version 0.1.x ne peut pas ouvrir la base après cette mise à niveau ; conservez la sauvegarde si vous devez revenir en arrière.

## Grille horaire du PDF

Les points de départ et d’arrivée des blocs sont calculés à la minute, sans arrondi à la demi-heure. Les repères de 30 minutes servent uniquement à lire la grille. Un horaire coupé crée plusieurs blocs distincts sur une seule ligne. De 1 à 8 éducateurs, le document a une page ; de 9 à 16, deux pages ; le même en-tête, la date, la légende et l’échelle sont repris sur chacune.

La grille demandée commence à 7 h. La présence de préparation dès 6 h 50 reste indiquée par son heure exacte dans le bloc et une mention au bas de la page ; elle n’est pas arrondie à 7 h ni perdue. Les plages entièrement hors de la grille sont indiquées au bas de la page. Le PDF d’exemple reprend les données fictives des pièces jointes.
