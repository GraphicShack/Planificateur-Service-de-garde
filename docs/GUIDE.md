# Guide d'utilisation

## Un écran simple

L’équipe reste à gauche et le calendrier occupe le reste de l’écran. Les commandes courantes sont **Générer**, **Exporter PDF**, **Inscriptions**, **Annuler/Rétablir** et **Vérifier**. La sauvegarde est automatique ; l’indicateur en haut à droite confirme son état.

- **Inscriptions** définit le nombre d’enfants et affiche le minimum d’éducatrices nécessaire. Pour créer un quart, glissez un nom sur la grille ou double-cliquez sur une plage vide. Au clavier, sélectionnez un nom et appuyez sur Entrée.
- **Vérifier** ouvre le détail des alertes ; **Fermer** redonne toute la place au calendrier. La validation continue même lorsque ce panneau est fermé.
- **Menu → Organisation** contient les profils et les règles d’encadrement.
- **Menu → Affichage** permet de régler le zoom, le magnétisme et la visibilité du panneau de l’équipe.
- L’icône **Dossier**, dans la barre latérale verte, regroupe l’enregistrement, l’ouverture des journées, la duplication, l’historique et les sauvegardes. **Menu** conserve les règles, le statut, l’affichage et l’annulation.

## Préparer une journée pédagogique

1. Choisissez la **date exacte** avec les flèches ou le champ de date. Chaque date possède son propre horaire, même si deux journées tombent dans la même semaine.
2. Cliquez sur le **+ de L’équipe**. Une couleur encore inutilisée est proposée automatiquement ; vous pouvez la changer dans le profil. Choisissez le **rang de 1 à 11** : le rang 1 est le plus ancien, et des rangs peuvent rester libres (1, 4, 9, par exemple). Aucun profil n’est renuméroté automatiquement.
3. Saisissez les heures cibles, garanties et maximales **pour cette journée**. Un objectif vide signifie « Aucun objectif défini ». Précisez les disponibilités et absences si nécessaire.
4. Cliquez sur **Inscriptions** et indiquez le nombre d’enfants. Le besoin additionne les minimums et ratios de chaque groupe. Le nom se modifie directement dans l’en-tête de la grille. Le minimum de deux éducatrices et le ratio configuré restent contrôlés.
5. Ajoutez les quarts ou demandez une proposition automatique. L’interface gère uniquement les horaires.

Une nouvelle date reprend les profils et paramètres utiles. Ses inscriptions et quarts restent vides ; les absences de l’ancienne date ne sont pas recopiées. Pour reprendre aussi un horaire complet, utilisez **Dossier → Dupliquer cette journée** et choisissez une date vide.

## Planifier dans le calendrier

Glissez une éducatrice depuis l’équipe vers un groupe et l’heure souhaitée. Déplacez son bloc pour changer l’heure ou le groupe ; tirez son bord supérieur ou inférieur pour régler sa durée. Le double-clic ouvre les heures exactes, les buffers et les pauses. Saisir 7 h 13 à 8 h 55 produit 1 h 42, sans arrondi automatique.

Les couleurs pastel des blocs identifient les groupes ; les initiales colorées identifient les éducatrices. Le rang est visible dans chaque fiche de l’équipe et reste modifiable dans le profil.

**Menu → Affichage** propose le zoom, la journée entière et le magnétisme de 1, 5 ou 15 minutes, ou libre. Le calendrier affiche uniquement la journée choisie. Les objectifs et les totaux d’heures concernent cette journée.

Un quart verrouillé est conservé pendant la génération ; déverrouillez-le dans son formulaire pour le modifier.

## Ouverture, fermeture et relève

Pour une journée ouverte aux enfants de 7 h à 17 h 30, le service exige deux personnes au total de 6 h 50 à 7 h et de 17 h à 17 h 35. De 7 h à 17 h, chaque groupe ouvert exige deux éducateurs minimum. Les dix minutes de préparation avant l’ouverture et les cinq minutes de fermeture sont des temps de présence rémunérés, distincts de la couverture des enfants. De 7 h à 17 h, le besoin d’un groupe est le maximum de deux et du nombre d’enfants divisé par son ratio, arrondi au supérieur. Pendant l’accueil commun, les enfants et la couverture sont comptés pour tout le service. Les pauses doivent être remplacées et les relèves comporter quinze minutes communes.

Pour une relève à 12 h 30, l'éducatrice entrante peut commencer sa présence à 12 h 15 avec quinze minutes de préparation avant sa couverture de 12 h 30. L'éducatrice sortante reste présente pendant ces quinze minutes. Le besoin de couverture du groupe doit rester satisfait, même pendant les pauses et les relèves.

## Lire et corriger les alertes

Les erreurs empêchent la publication, mais permettent de sauvegarder un brouillon. Elles concernent notamment un manque de personnel, un chevauchement de groupes pour une même éducatrice, une indisponibilité ou une limite d’heures. Les avertissements signalent les écarts d'heures ou préférences.

Après une modification, consultez le compteur **Vérifier** et cliquez dessus pour ouvrir la liste des alertes. Les messages indiquent la journée, l'intervalle et le groupe concernés, avec une piste de correction lorsqu'elle est disponible.

## Générer une proposition

Cliquez sur « Générer ». Le moteur respecte les contraintes obligatoires qu'il modélise et les quarts verrouillés, puis cherche à améliorer les heures et les préférences. Examinez la proposition avant de l'accepter. Si la recherche échoue, lisez l'explication ; vous pouvez modifier les disponibilités, effectifs ou quarts et recommencer. Un échec dans les candidats examinés ne signifie pas nécessairement qu'aucune solution manuelle n'existe.

## Sauvegarder, revenir en arrière et exporter

Sauvegardez régulièrement et utilisez l'export de sauvegarde locale avant un changement important. Les anciennes versions de chaque journée restent consultables dans **Dossier → Historique des versions**. Une restauration crée une nouvelle version ; une duplication permet de réutiliser une journée. Une publication conserve sa photographie historique.

**Exporter PDF** enregistre directement un seul horaire général de la journée, sans choix de formats individuels. Le document reprend le modèle fourni : lettre paysage, titre à gauche, date à droite, colonne des noms puis grille 6 h 50–17 h 35 avec repères de 30 minutes, huit éducateurs maximum par page. Les blocs indiquent leur groupe et leurs heures exactes ; un même groupe garde la même couleur sur toutes les pages. Les pauses, rémunérées ou non, et les interruptions restent simplement vides. Aucun compteur ni colonne d’activité n’est ajouté. **Menu → Aperçu avant impression** ouvre ce même document. Pour une sauvegarde informatique complète, utilisez la sauvegarde locale SQLite ; un PDF sert à consulter ou imprimer et ne remplace pas la base.

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

La grille commence exactement à 6 h 50 et se termine à 17 h 35. Les dix minutes d’ouverture et les cinq minutes de fermeture font partie de la présence rémunérée, sans être confondues avec la couverture des enfants.
## Choisir la date au clavier

La barre affiche la date complète dans un champ modifiable, sans calendrier mensuel. Sélectionnez le jour, le mois ou l’année pour modifier cette partie au clavier. Les boutons précédent et suivant changent de journée. Une seule journée est ouverte à la fois ; la sauvegarde automatique reste active. Si l’enregistrement échoue, la navigation est annulée et les modifications restent à l’écran.

## Lire la couverture et les alertes

La bande verticale est placée entre les heures et les quarts. Elle suit le même défilement que la grille et fusionne les plages consécutives dont les nombres de personnes présentes et requises sont identiques. **2 présentes / 2 requises · OK** indique le besoin exact en vert ; **1 présente / 2 requises · Manque 1** signale un déficit en rouge ; **3 présentes / 2 requises · +1** indique un surplus en gris neutre. Les limites restent exactes à la minute : aucune moyenne ne masque une pause. Cliquez une plage ou utilisez haut/bas puis Entrée pour la surligner ; le détail sélectionné reste affiché dans l’en-tête.

Le bouton **− Ratio** masque la bande et rend cet espace aux quarts ; **+ Ratio** la réaffiche. Le contrôle reste accessible au clavier et la validation continue même lorsque la bande est fermée. Ce choix ne modifie ni les horaires ni les exports : le PDF ne contient aucune bande de ratio, aucun compte de présence et aucun panneau d’alertes.

Toutes les éducatrices actives disposent d’une colonne, sans défilement horizontal. Si un nom ne tient pas, ses initiales sont affichées ; l’infobulle conserve le nom complet. Les noms des quarts sont en gras à 14 px minimum, les heures à 13 px. Le bouton ⓘ à côté de « L’équipe » explique la création des quarts sans prendre de place dans la liste. Annuler et Rétablir sont alignés à droite dans l’en-tête.

**Vérifier (N)** ouvre les alertes. Cliquer sur une alerte ou l’activer au clavier sélectionne sa plage et fait défiler la grille et la bande de ratio. La validation continue même lorsque le panneau est fermé. Avec une journée valide, le panneau indique **Aucune alerte**.

Les deux poignées de chaque quart sont visibles. Les pauses indiquent leurs heures, leur durée et leur rémunération. Les dîners restent masqués dans les blocs ; leur incidence sur la couverture et la paie est conservée. Une pause payée compte dans le total rémunéré mais n’assure jamais la couverture des enfants. Un dépassement d’objectif est orange ; celui d’un maximum obligatoire est rouge. Un libellé précise toujours la situation.

## Annuler et rétablir

Les boutons **Annuler** et **Rétablir** conservent cinquante actions. Les raccourcis sont Cmd+Z et Cmd+Maj+Z sur Mac, Ctrl+Z et Ctrl+Maj+Z sur Windows. Une nouvelle modification après une annulation efface les actions qui restaient à rétablir.

## Ajouter ou modifier un profil

Le bouton **+** à côté de « L’équipe » ouvre un formulaire clair, sans onglets. Le profil, le rang d’ancienneté, les heures, les disponibilités, les absences, les notes se remplissent dans une seule fenêtre. Une couleur distincte et le premier rang libre sont proposés dès la création. Les rangs vont de 1 à 11, peuvent rester non consécutifs et ne peuvent pas être attribués à deux profils. Les objectifs non définis sont vides. Les heures garanties sont conservées car la génération les applique comme minimum obligatoire.

Sur un grand écran, les sections apparaissent en deux colonnes. Sur un petit écran, elles s’empilent avec un défilement vertical ; les boutons **Enregistrer** et **Annuler** restent visibles. Les textes et les champs restent lisibles lorsque le système utilise un thème sombre.


## Navigation dans le panneau de gauche

Les icônes de la barre latérale remplacent le contenu du panneau de gauche :
**Équipe**, **Inscriptions** ou **Vérification**. Le calendrier conserve sa place.
L’icône Vérification affiche le nombre de points à vérifier dans un badge.
Cliquez l’icône Équipe, ou le bouton de retour, pour retrouver la liste.

Dans Inscriptions, le besoin se met à jour pendant la saisie. Cliquez
**Enregistrer** pour appliquer le nombre d’enfants à la journée sélectionnée.
Un changement de date charge les inscriptions de cette nouvelle journée.
Les versions archivées restent en consultation.

Les dîners ne sont plus dessinés ni nommés dans les blocs du calendrier.
Ils restent modifiables dans le formulaire du quart. Ils sont exclus de la
couverture et, lorsqu’ils ne sont pas payés, du total rémunéré.


## Groupes et sous-colonnes

L’en-tête de chaque groupe couvre les sous-colonnes de ses éducatrices. Une
éducatrice affectée à plusieurs groupes apparaît dans chacun d’eux, avec ses
quarts distincts et leurs heures exactes. Les en-têtes restent visibles pendant
le défilement. Les noms passent en initiales si nécessaire ; l’infobulle et le
nom accessible donnent le libellé complet. Les profils sans affectation restent
dans une section « À affecter » et les groupes vides offrent une cible de dépôt.

Le double-clic dans une plage vide présélectionne le groupe et l’éducatrice de
la sous-colonne. Le dépôt depuis l’équipe et le déplacement horizontal d’un
quart ciblent le groupe situé sous le pointeur. Les heures ne changent pas lors
d’un déplacement purement horizontal. Déplacer un quart au clavier conserve son
groupe ; le formulaire permet de le changer explicitement.

Les inscriptions réutilisent la préparation par groupes de vingt enfants,
en conservant les identifiants et les affectations existantes. Les périodes des
groupes devenus inutiles sont fermées ; aucun quart n’est supprimé. La taille de
préparation des groupes ne constitue pas un ratio réglementaire. Les règles de
couverture sont désormais appliquées à chaque groupe ; les heures d’ouverture et de fermeture sont conservées.


## Règles actuelles — version 0.3.3

| Plage initiale | Minimum de présence |
| --- | --- |
| 6 h 50 à 7 h | Deux personnes pour tout le service |
| 7 h à 17 h | Deux personnes dans chaque groupe ouvert |
| 17 h à 17 h 35 | Deux personnes pour tout le service |

Pendant les plages communes, les enfants de tous les groupes sont comptés ensemble et le ratio reste obligatoire : avec 60 enfants présents et un ratio de 1/20, trois éducateurs sont nécessaires. Les noms et les colonnes de groupes sont conservés ; il n’est pas nécessaire de déplacer tous les quarts dans un seul groupe pour bénéficier de la règle commune.

Une pause, même payée, ne couvre jamais les enfants. Les buffers servent à la présence avant l’ouverture et après la fermeture, mais ne comptent pas dans la couverture pendant l’accueil. Chaque relève conserve quinze minutes communes ; pendant l’accueil commun, la transmission peut se faire avec un éducateur d’un autre groupe.

Les plages suivent les heures configurées : la préparation précède l’ouverture aux enfants, et l’accueil commun du soir commence trente minutes avant leur fermeture et se termine après le buffer de fermeture. Les heures initiales demeurent 6 h 50–17 h 35. Le minimum de deux par groupe est maintenu entre les plages communes.

Les anciennes versions publiées/archivées conservent leurs règles ; les versions de travail, nouvelles journées et duplications adoptent les règles actuelles.

La barre latérale présente Planning, Équipe, Inscriptions, Ratio et Vérification.
Dossier et Réglages sont placés en bas. Annuler/Rétablir sont sur la ligne du
nom de la journée ; leurs raccourcis clavier restent disponibles.


## Accueil

Le logiciel s’ouvre sur **Bonjour, bienvenue**. L’icône maison, première dans
la barre latérale, permet d’y revenir depuis le planning. Les journées créées
sont triées par date décroissante, y compris les dates futures. Cliquez une
ligne pour ouvrir son horaire. La journée du jour est mise en évidence et
reprend les heures exactes de présence.

Les badges utilisent exactement les mêmes alertes que Vérifier dans la grille,
y compris les avertissements. « Couverture complète » signifie qu’aucun point
n’est à vérifier. Les compteurs d’aujourd’hui indiquent le plus grand effectif
d’enfants et le besoin maximal sur la journée, les éducatrices actives ayant
au moins un quart et le total rémunéré.

**Nouvelle journée pédagogique** crée aujourd’hui et ouvre Inscriptions. Si
aujourd’hui existe déjà, choisissez une autre date dans le champ proposé.
Choisir une date existante ouvre son contenu sans l’écraser. **Ouvrir une
journée précédente** permet de choisir dans la liste ou de saisir une date,
sans calendrier mensuel.

La carte **L’équipe** reprend les profils actifs du dernier horaire enregistré,
comme le modèle de profils existant. Ajouter ou modifier ouvre le formulaire
habituel et crée une nouvelle version de travail de cet horaire ; les archives
restent conservées. Dans une base entièrement vide, l’ajout d’un profil utilise
le brouillon d’aujourd’hui. Les modifications de la grille sont enregistrées
avant le retour à l’accueil.

Les cartes s’empilent sur les petites fenêtres ; la page défile verticalement.
Les notes de chaque version sont conservées dans [CHANGELOG.md](../CHANGELOG.md)
et reprises dans les Releases GitHub.


## Attribution des quarts et suppression — version 0.3.2

Le générateur traite tous les groupes sans les fusionner. Chaque groupe doit respecter son ratio (initialement 1/20). Deux éducateurs minimum sont requis par groupe entre les plages communes ; pendant ces plages, le minimum est de deux pour tout le service, avec le ratio collectif maintenu. Si des groupes demeurent ouverts avec des enfants à la fin de la journée, leur couverture reste nécessaire.

La recherche attribue d’abord des heures au plus grand nombre de personnes possible, sans modifier les contraintes obligatoires. Elle limite ensuite les heures inutiles, puis privilégie le rang 1, suivi des rangs suivants : quarts continus, plus d’heures, fin plus tôt. Les rangs n’ont pas besoin d’être consécutifs. Les horaires verrouillés et les disponibilités peuvent empêcher l’ordre idéal ; les personnes sans heures sont nommées dans la proposition. Une recherche interrompue signale que les préférences ne sont pas toutes prouvées optimales.

Le maximum quotidien est de 8 h rémunérées, tous les quarts cumulés. Les buffers payés et les pauses payées comptent ; les pauses non payées sont déduites. Un maximum individuel plus bas reste obligatoire. Un dépassement manuel est une erreur rouge et empêche de valider/publier ; le brouillon demeure sauvegardable pour correction.

Sur l’accueil, **Supprimer** demande confirmation puis retire la journée de la liste. Ses anciennes versions et les profils restent conservés. La suppression survit aux sauvegardes et à leur import. Pour reprendre cette date, créez une nouvelle journée à cette date, ou restaurez une version dans l’historique du dossier. La migration au format SQLite 3 crée une copie de sécurité avant toute modification du format ; ne remplacez pas le dossier `donnees` lors d’une mise à jour.

## Apparence et animations — version 0.3.4

Dans l’icône **Réglages** en bas de la barre latérale, choisissez **Affichage…**.

- Choisissez **Forêt**, **Bleu**, **Prune** ou **Ardoise**. Le changement est immédiat.
- Pour un accent à votre goût, choisissez **Personnalisé**, puis **Choisir une couleur…** ou saisissez une valeur telle que `#245C85`. Les couleurs trop claires sont ajustées pour que les textes blancs restent lisibles ; l’accent réellement appliqué et son contraste sont affichés.
- Désactivez **Animations discrètes** pour une navigation immédiate sans effet. Les transitions ne déplacent jamais les quarts et ne modifient pas les heures.

Ces préférences sont conservées dans `interface.json`, à côté de la base SQLite (dans `donnees` en mode portable). Elles ne créent pas de nouvelle version d’horaire. Les sauvegardes d’horaires SQLite restent indépendantes de ces préférences d’affichage. Les couleurs des éducatrices et des groupes, les alertes et le PDF ne changent pas avec le thème. Les thèmes disponibles gardent des surfaces claires ; aucun thème sombre n’est proposé.

## Chargement de la génération — version 0.3.5

Après **Générer l’horaire**, une fenêtre affiche **Création de votre horaire**, un indicateur circulaire et le temps écoulé. Il ne s’agit pas d’un pourcentage d’avancement : le calcul peut durer quelques instants. Le cercle suit votre thème et reste statique si vous avez désactivé **Animations discrètes** dans Affichage ; le texte confirme toujours que le calcul est en cours.

La fenêtre se ferme quand le calcul rend sa proposition ou un message expliquant l’impossibilité ou l’erreur. Votre horaire actuel est conservé et vous devez confirmer la proposition avant qu’elle soit appliquée. La recherche n’est pas annulable pendant son exécution ; Échap et le bouton de fermeture ne masquent pas son état.
