# Guide d'utilisation

## Préparer une semaine

1. Sélectionnez la semaine à planifier. Chaque journée conserve sa date et peut recevoir un nom, par exemple « Journée pédagogique — Halloween ».
2. Ajoutez les éducatrices. Indiquez leurs heures cibles, leur ancienneté, leurs disponibilités et leurs absences. Les détails facultatifs sont regroupés dans les réglages du profil.
3. Utilisez la préparation d’une journée pour saisir le nombre d’inscriptions et la taille de groupe souhaitée. Les groupes et effectifs sont répartis automatiquement ; vous pouvez ensuite modifier leurs périodes et effectifs. Le logiciel calcule le besoin de personnel selon le ratio configuré et le minimum de deux éducatrices par groupe actif.
4. Ajoutez les locaux et leurs capacités si vous souhaitez planifier les activités.

Les durées sont toujours calculées à la minute. Saisir 7 h 13 à 8 h 55 produit 1 h 42, sans arrondi automatique.

## Planifier dans le calendrier Jour

Glissez une éducatrice du panneau de gauche vers la colonne du groupe et l'heure souhaitée. Déplacez le bloc pour changer son horaire ou son groupe. Ajustez son bord supérieur ou inférieur pour changer le début ou la fin. Un double-clic ouvre la saisie exacte des heures, buffers et pauses.

Le magnétisme propose 1, 5 ou 15 minutes et peut être désactivé. Le zoom agrandit l'axe du temps. La vue Semaine sert à consulter les cinq journées et à ouvrir une journée pour l'édition détaillée.

Un quart verrouillé est conservé lors de la génération automatique. Déverrouillez-le dans son formulaire pour le modifier.

## Ouverture, fermeture et relève

Pour une journée ouverte de 7 h à 17 h 30, prévoyez deux éducatrices dès 6 h 50 et deux jusqu'à 17 h 35. Les dix minutes de préparation avant l'ouverture et les cinq minutes après la fermeture sont des temps de présence rémunérés. Ils ne constituent pas de la couverture d'enfants.

Pour une relève à 12 h 30, l'éducatrice entrante peut commencer sa présence à 12 h 15 avec quinze minutes de préparation avant sa couverture de 12 h 30. L'éducatrice sortante reste présente pendant ces quinze minutes. Le besoin de couverture du groupe doit rester satisfait, même pendant les pauses et les relèves.

## Activités et locaux

Une activité se planifie séparément des quarts. Changer « Jeux extérieurs » de la cour au parc ne modifie pas les heures des éducatrices. Les conflits de lieu, capacités et disponibilités apparaissent dans les alertes. La responsabilité et la couverture découlent des affectations réellement présentes.

## Lire et corriger les alertes

Les erreurs empêchent la publication, mais permettent de sauvegarder un brouillon. Elles concernent notamment un manque de personnel, un chevauchement de groupes pour une même éducatrice, une indisponibilité ou un conflit de local. Les avertissements signalent les écarts d'heures ou préférences.

Après une modification, consultez le compteur et la liste des alertes. Les messages indiquent la journée, l'intervalle et le groupe concernés, avec une piste de correction lorsqu'elle est disponible.

## Générer une proposition

Cliquez sur « Générer automatiquement ». Le moteur respecte les contraintes obligatoires qu'il modélise et les quarts verrouillés, puis cherche à améliorer les heures et les préférences. Examinez la proposition avant de l'accepter. Si la recherche échoue, lisez l'explication ; vous pouvez modifier les disponibilités, effectifs ou quarts et recommencer. Un échec dans les candidats examinés ne signifie pas nécessairement qu'aucune solution manuelle n'existe.

## Sauvegarder, revenir en arrière et exporter

Sauvegardez régulièrement et utilisez l'export de sauvegarde locale avant un changement important. Les anciennes versions restent consultables. Une restauration crée une nouvelle version ; une duplication permet de réutiliser une semaine. Une publication conserve sa photographie historique.

L'export PDF offre un horaire général, un horaire individuel et un regroupement. Les horaires indiquent les heures exactes, activités, lieux et totaux. Pour une sauvegarde informatique complète, utilisez la sauvegarde locale SQLite ; un PDF sert à consulter ou imprimer et ne remplace pas la base.

## Ouvrir la version portable, sans installation

1. Décompressez le ZIP reçu dans un dossier ou sur une clé USB où vous pouvez enregistrer des fichiers.
2. Ouvrez le dossier **Planificateur-SDG** extrait.
3. Sous Windows, ouvrez **Planificateur-SDG.exe**. Sous Mac, ouvrez **Planificateur-SDG.app** depuis ce dossier.

Aucun programme d’installation, Python, compte ou téléchargement complémentaire n’est nécessaire. Ne lancez pas l’application directement dans le ZIP et gardez tous les fichiers ensemble, notamment **portable.mode** et le sous-dossier **donnees**. Sous Mac, ne déplacez pas seulement l’application dans Applications.

Vos horaires, éducatrices, archives et sauvegardes locales restent dans **donnees**, à côté de l’application. Fermez le logiciel avant de déplacer le dossier ou de retirer la clé USB. Le poste doit autoriser l’exécution de l’application et l’écriture dans le dossier choisi.

Pour une mise à jour, sauvegardez vos données, décompressez la nouvelle version dans un autre dossier et conservez votre ancien sous-dossier **donnees** dans le nouveau dossier portable. Ne remplacez jamais vos données par un dossier vide. Pour transférer une planification entre Windows et Mac, utilisez l’export et l’import de sauvegarde locale.

La préparation du fichier à remettre est décrite dans les procédures [Windows](DISTRIBUTION_WINDOWS.md) et [macOS](DISTRIBUTION_MACOS.md). Elle concerne la personne qui construit le logiciel.
