# Notes de version

Chaque release reprend la section correspondant à sa version. Une section doit
être ajoutée ici avant de publier ; le contrôle de publication refuse une
version sans notes. Les téléchargements sont dans les [Releases GitHub](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases).

## [0.5.1] — 2026-10-29

- **Mise à jour compatible avec vos exports existants** : les PDF et autres documents enregistrés à côté du programme ne bloquent plus la préparation ni le retour à une version conservée. Ils restent dans leur dossier d’origine et ne sont jamais intégrés au nouveau logiciel.
- Les fichiers, dossiers et liens déclarés du programme restent tous contrôlés. Une modification de l’exécutable ou d’un élément de son inventaire bloque toujours la copie ; les ZIP distribués restent soumis à une vérification stricte, sans fichiers inattendus.
- Test supplémentaire couvrant un PDF personnel dans le dossier portable, sa conservation lors d’une mise à jour et d’un retour, son exclusion des nouveaux dossiers et le refus d’un exécutable altéré.
- La grille Proposition reste affichée en premier ; l’assistant, le bilan détaillé, l’accueil par nom de session et la réduction des trous inutiles de la 0.5.0 sont conservés. Une demande de publication seule ne relance plus les compilations des deux plateformes.

## [0.5.0] — 2026-10-29

- **Assistant de mise à jour hors ligne**, dans Dossier → Mettre à jour depuis un ZIP. Il contrôle la version, le système, l’architecture, les chemins et les empreintes des fichiers, puis prépare un dossier portable séparé, sans installation ni droits administrateur. Les données SQLite, historiques, préférences et sauvegardes connues sont copiés ; le dossier actuel reste conservé.
- **Démarrage et retour accompagnés** : la dernière sauvegarde est reprise au premier démarrage après fermeture de l’ancienne version, même si la préparation avait été faite plus tôt. Le retour prépare l’ancien programme avec les données d’avant mise à jour, tout en conservant les modifications plus récentes séparément. Une erreur de préparation ou de lancement laisse la version actuelle utilisable.
- **Proposition visible dès la fin de la génération** : la fenêtre de comparaison s’ouvre directement sur la grille proposée, ajustée au début de la journée. Le bilan reste accessible dans son onglet ; aucune proposition n’est appliquée sans confirmation.
- **Bilan clair avant application** : couverture, erreurs bloquantes, avertissements, heures rémunérées, horaires coupés, interruptions, préférences respectées, personnes sans heures et quarts verrouillés conservés. Les noms et les souhaits non satisfaits sont précisés ; les détails avant/après restent accessibles. Un quart verrouillé modifié empêche l’application.
- **Trous inutiles évités lors de la génération** : après la participation de l’équipe, la recherche réduit les personnes avec un horaire coupé puis la durée des interruptions, avant de réduire les heures rémunérées superflues. Elle ne crée plus volontairement un petit trou seulement pour économiser quelques minutes payées. Les coupures nécessaires, les pauses, les indisponibilités, les verrous et le maximum quotidien restent respectés.
- **Accueil personnalisé** : « Bonjour [nom de session] ! », lu localement sur Windows ou Mac, sans compte, transmission ni connexion. Si le nom est indisponible, l’accueil reste générique.
- Les ZIP portent désormais un inventaire `version-portable.json`. Les contrôles natifs extraient le vrai ZIP, préparent sa copie, démarrent l’exécutable copié, restaurent une version et démarrent celle-ci avec vérification des données. La publication exige ces résultats sur Windows et Mac.
- **Premier passage depuis 0.4.0 ou avant** : transfert manuel du dossier `donnees` vers 0.5.0 après sauvegarde. L’assistant servira ensuite aux ZIP plus récents. Aucun téléchargement automatique ni signature/notarisation n’est ajouté ; utilisez les ZIP des publications officielles du projet.

## [0.4.0] — 2026-10-28

- **Absence pour la journée en un clic** depuis L’équipe. Le profil reste actif ; les quarts non verrouillés sont retirés, la couverture et les alertes se recalculent, et Annuler permet de récupérer l’horaire précédent. Les quarts verrouillés sont conservés et signalés pour traitement manuel. Les absences rapides ne sont pas reprises dans les nouvelles journées.
- **Correction ciblée** depuis Vérifier : sélectionner une alerte de couverture, puis Proposer une correction. La recherche peut ajouter une remplaçante ou prolonger un quart voisin non verrouillé, avec les buffers et les limites applicables, sans déplacer les autres quarts. Elle ne renvoie aucun résultat partiel et ne crée aucune nouvelle erreur bloquante ; les erreurs déjà présentes restent indiquées et empêchent la publication.
- **Comparaison avant/après** avant toute application : quarts ajoutés, retirés ou modifiés, heures rémunérées par éducatrice, écarts et nombre d’alertes. Les grilles actuelle et proposée restent consultables. Des identifiants générés différents ne suffisent pas à marquer un quart identique comme modifié.
- **Préférences individuelles structurées** : ouvrir, fermer, éviter les horaires coupés, heure de départ souhaitée à la minute. Elles départagent les propositions rang par rang, après les contraintes obligatoires, la participation, les heures utiles et la continuité. Un souhait non satisfait produit un avertissement ; il ne devient pas une indisponibilité obligatoire.
- La génération conserve ses contraintes de groupes, les deux présences collectives aux extrémités, les quinze minutes de relève, les pauses et le maximum de huit heures. Les anciennes journées restent consultables et les nouveaux champs sont optionnels à la lecture des anciens fichiers.
- Le contrôle des logiciels portables extraits vérifie aussi les absences, les préférences sauvegardées, une correction réelle et l’affichage de la comparaison, sans connexion réseau.

## [0.3.5] — 2026-10-28

- Nouvel écran de chargement pendant la génération réelle de l’horaire : indicateur circulaire animé, message explicite et temps écoulé, sans pourcentage simulé.
- L’indicateur utilise la couleur du thème et respecte l’option « Animations discrètes » : l’information reste visible quand les mouvements sont désactivés.
- Fermeture automatique à l’arrivée d’une proposition, d’une impossibilité ou d’une erreur. Les animations et le compteur sont arrêtés et libérés à la fin du calcul.
- La génération continue dans son fil de calcul ; aucune proposition n’est appliquée sans confirmation. Les commandes sont réactivées après la fin du calcul et les horaires existants restent conservés.
- Cinq tests supplémentaires couvrent le chargement, la réduction des mouvements et les issues de génération : proposition, absence de solution et erreur.

## [0.3.4] — 2026-10-28

- Transitions discrètes entre l’accueil et la planification, et entre les panneaux Équipe, Inscriptions et Vérification. Les effets courts (120–160 ms) sont interruptibles ; les commandes et le clavier restent immédiatement utilisables.
- Survol et focus des boutons accompagnés d’un contour progressif, sans déplacement des contrôles ni des quarts. Les animations peuvent être désactivées dans Réglages → Affichage. L’observation des événements est suspendue quand la fenêtre est masquée, pour éviter les traitements inutiles lors des réouvertures.
- Quatre thèmes clairs : Forêt, Bleu, Prune et Ardoise. Un accent personnalisé peut être choisi dans un sélecteur de couleur ou saisi en hexadécimal ; une couleur trop claire est foncée pour conserver un contraste d’au moins 4,5:1 avec le texte blanc.
- Les thèmes s’appliquent à l’accueil, à la barre latérale, aux boutons, aux formulaires, aux champs de date et aux sélections de la grille. Les couleurs des éducatrices, des groupes, des alertes et du PDF sont conservées.
- Le thème et la préférence d’animation sont enregistrés dans `donnees/interface.json`, séparément des horaires. Un fichier absent ou endommagé ne bloque pas l’application ; une écriture impossible est expliquée dans Affichage.
- Les options d’affichage défilent sur les petits écrans, avec un bouton Fermer toujours accessible. Neuf tests ciblés supplémentaires couvrent les transitions, les clics et le focus, le contraste, les préférences et la conservation des données.

## [0.3.3] — 2026-10-28

- Accueil commun de 6 h 50 à 7 h et de 17 h à 17 h 35 : minimum de deux personnes au total, tous groupes confondus. Le minimum de deux par groupe demeure de 7 h à 17 h.
- Le ratio initial de 1/20 reste applicable à l’ensemble des enfants pendant l’accueil commun ; plus de quarante enfants peuvent donc exiger plus de deux personnes.
- La bande de couverture et les alertes identifient clairement les plages « Tous les groupes ». Les pauses et les buffers non dédiés à la couverture restent exclus du ratio.
- La génération utilise exactement les mêmes bornes que la validation et autorise une transmission entre éducateurs de groupes différents pendant l’accueil commun.
- Les inscriptions et les paramètres expliquent les plages communes. Les horaires d’ouverture restent inchangés : début à 6 h 50 et fin à 17 h 35.
- Les nouveaux brouillons adoptent la règle actualisée ; les versions publiées/archivées conservent leurs règles. Les huit heures rémunérées maximum, les priorités de rang et les quarts verrouillés sont conservés.
- Sept tests ciblés supplémentaires et contrôle des plages communes dans les logiciels portables extraits.

## [0.3.2] — 2026-10-28

### Génération et règles

- Tous les groupes sont conservés pendant la recherche et couverts selon leur propre ratio de 1 pour 20, configurable. Minimum strict de deux éducateurs dans chaque groupe ouvert, préparation et fermeture comprises, sans plage allégée dans les nouvelles journées. Un surplus dans un groupe ne masque plus un groupe sans personnel.
- Attribution d’heures au plus grand nombre de profils actifs possible, puis priorité aux rangs 1, 2, etc., même avec des rangs intermédiaires libres : quarts continus, davantage d’heures et fin plus tôt, en limitant les heures inutiles.
- Maximum obligatoire de 8 h rémunérées par personne et par jour, tous quarts cumulés et buffers compris ; les pauses non payées sont déduites. Les limites individuelles plus basses sont conservées.
- Les personnes sans heures sont nommées dans la proposition. Les contraintes incompatibles avec le plafond sont expliquées ; aucun résultat invalide n’est appliqué.
- Les affectations verrouillées, les disponibilités, les pauses et les quinze minutes de relève restent obligatoires. Le logiciel précise quand le délai empêche de prouver l’optimalité des préférences.

### Interface et données

- Bouton Supprimer sur chaque journée de l’accueil, avec confirmation. Les versions sont conservées ; la date reste supprimée après réouverture et import/export de sauvegarde. Une restauration ou une création explicite permet de réutiliser la date.
- Les profils restent accessibles après suppression de la dernière journée. Modifier un profil ne fait pas réapparaître la journée supprimée.
- Retrait des annotations « Votre calendrier commence ici » et du texte superposé à la grille vide.
- Correction du champ de date devenu invisible avec les styles Qt 6.12 ; saisie au clavier conservée.
- Format SQLite 3 avec copie de sécurité avant migration ; les anciennes versions publiées/archivées gardent leurs règles et leur contenu.
- Contrôle du logiciel portable étendu aux groupes, à l’attribution à toute l’équipe, à l’ordre des rangs et au plafond de huit heures.

## [0.3.1] — 2026-10-28

### Ajouts

- Page d’accueil au démarrage : journées sauvegardées triées, résumé d’aujourd’hui, équipe et accès direct aux profils.
- Création d’une journée depuis l’accueil, suivie de la saisie des inscriptions ; sélection d’une journée par liste ou champ de date.
- Icône Accueil en premier et retour depuis la planification ; cartes empilées sur les petites fenêtres.
- Fichier de notes de version dans le dépôt, repris automatiquement dans chaque release GitHub.

### Planification

- Groupes au-dessus des sous-colonnes de leurs éducatrices, en-têtes figés et heures exactes.
- Équipe, Inscriptions et Vérification partagent le panneau gauche. La vérification porte un badge du nombre d’alertes.
- Ratio masquable ; dîners masqués dans les blocs, avec couverture et rémunération conservées dans les calculs.
- Annuler et Rétablir sur la ligne du nom de la journée. Dossier et Réglages sont regroupés en bas de la barre latérale.
- Une éducatrice peut suffire de 6 h 50 à 7 h et de 17 h 20 à 17 h 35. Deux restent nécessaires entre ces plages. Le ratio configuré, initialement 1/20, reste obligatoire pendant tout l’accueil.

### Fiabilité

- Validation, bande de couverture et solveur utilisent les mêmes bornes à la minute. Les groupes, les profils et les affectations verrouillées sont conservés dans les propositions.
- Les anciens horaires publiés/archivés conservent leurs règles ; les versions de travail adoptent les règles actuelles dans une nouvelle version.
- Les compteurs d’alertes de l’accueil et du planificateur partagent la même fonction. Une journée existante n’est jamais écrasée par le bouton de création.
- Contrôle de l’accueil ajouté aux vérifications des exécutables portables extraits.
- PDF lettre paysage conservé : huit éducateurs par page, interruptions vides, aucun ratio ni panneau d’alertes imprimé.

## [0.3.0]

- Planification d’une journée à la fois, effectif global, couverture verticale par plages fusionnées et alertes sélectionnables.
- Pauses et dîner calculés à la minute, couleurs individuelles, redimensionnement et édition au clavier.
- Annuler/Rétablir sur cinquante actions, nom de journée en place et sélection de date sans calendrier mensuel.
- Formulaire de profil clair, rangs de 1 à 11 avec validation des doublons et sauvegarde locale.

## [0.2.2]

- Interface épurée, dossier dans la barre latérale et formulaire de profil dans une seule fenêtre claire.
- Boutons Aujourd’hui retirés ; adaptation des sections aux petits écrans.

## [0.2.1]

- Sélection de date plus lisible et accessible, commandes de dossier et horaires uniquement.
- Grille et PDF de 6 h 50 à 17 h 35.

## [0.2.0]

- Journées indépendantes, nom personnalisé, profils colorés et rangs d’ancienneté.
- PDF unique selon le modèle de journée pédagogique, pagination à huit éducateurs par page et pauses vides.
- Migration des anciennes semaines avec sauvegarde et conservation des historiques.

## [0.1.2]

- Correctif Mac AppTranslocation : recherche du dossier portable d’origine ou choix explicite, sans écrire dans une copie temporaire en lecture seule.

## [0.1.1]

- Interface simplifiée et distributions portables Windows/Mac avec téléchargements publics.
- Stockage des données à côté du logiciel, contrôles après extraction et sommes SHA-256.
