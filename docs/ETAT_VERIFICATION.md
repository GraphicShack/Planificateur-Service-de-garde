# État des vérifications

Les constructions et les contrôles natifs s’exécutent sur GitHub Actions. Les fichiers à remettre sont les ZIP portables d’une exécution réussie correspondant au code voulu. Une sortie compilée dont le contrôle échoue n’est pas livrée.

## Livraison 0.3.2 — rangs, tous les groupes et plafond de huit heures

Le code exact testé est `8bb801276a79a9cacee14887776c7cbd31a7453f`. Les deux constructions natives réussissent **260 tests chacune**, plus les **six sous-cas de pagination**, sans test ignoré :

- [Windows — tests, compilation et ZIP extrait vérifiés](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40768429513).
- [Mac Apple Silicon — tests, compilation et ZIP extrait vérifiés](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40768429567).

Le diagnostic de chaque exécutable confirme la couverture des deux groupes, la participation de l’équipe, l’ordre des rangs de profils équivalents et le plafond de huit heures, en plus de SQLite, de l’accueil, des PDF, du solveur et des opérations hors ligne. Ces contrôles sont exécutés sur le logiciel compilé, dans son dossier portable puis après extraction de son ZIP. La préparation de la release refuse un rapport sans le nouveau contrôle `daily_groups_seniority_eight_hours`.

La dernière précision métier impose deux éducateurs minimum dans chaque groupe ouvert, y compris la préparation et la fermeture. Le ratio propre au groupe peut exiger davantage de personnel. Les pauses ne comptent jamais dans sa couverture et les relèves conservent quinze minutes communes. Les versions de travail adoptent les règles actuelles ; les snapshots historiques restent intacts.

Le solveur maximise d’abord la participation, limite les heures inutiles, puis privilégie les rangs dans l’ordre : quarts continus, davantage d’heures et fin plus tôt. Une proposition initiale vérifiée amorce les cas de deux équipes continues par groupe. La limite de recherche peut empêcher de prouver l’optimalité de toutes les préférences ; le message de proposition le précise. Une erreur bloquante empêche toujours son application.

La suite locale Qt6/OR-Tools réussit aussi 260 tests et six sous-cas. Les dix contrôles de préparation de release et de notes passent. Les tests supplémentaires couvrent les 480/481 minutes, les pauses, les groupes et leurs buffers, les inscriptions, les profils indisponibles, les rangs non consécutifs, la suppression avec restauration/sauvegarde, la migration et la date stylée Qt 6.12.

Les aperçus et le PDF d’exemple sont générés par le code réel avec des données fictives : deux groupes et huit éducatrices, les quatre premiers rangs à 8 h et les quatre suivants à 3 h, avec deux personnes par groupe en continu et une relève de quinze minutes. Les captures Qt6 ont été inspectées avant publication ; les annotations de grille vide sont retirées et le bouton Supprimer est visible sur l’accueil.

SQLite passe au format 3 avec copie de sécurité avant migration. Une suppression masque la date sans effacer ses versions et survit aux sauvegardes. [Fichiers modifiés, hypothèses et limites](LIVRAISON_0_3_2.md). Les notes sont versionnées dans le [CHANGELOG](../CHANGELOG.md) et reprises dans la release GitHub.

Aucune mise à jour automatique ni notarisation DeveloperID Mac n’est ajoutée. Les essais sur le poste de l’école, avec un lecteur d’écran et une imprimante physique restent à faire. Les heures maximales correspondent aux minutes rémunérées, buffers compris et pauses non payées déduites. Conservez une copie du dossier `donnees` lors de la mise à jour.

## Livraison 0.3.1 — accueil, groupes et navigation latérale

Le code exact testé est `a7456ec72d6705f8d9643f2216a5894460278c8b`. Les deux constructions natives ont réussi **238 tests chacune**, plus les **six sous-cas de pagination**, sans test ignoré :

- [Windows — tests, compilation et ZIP extrait vérifiés](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40759375757).
- [Mac Apple Silicon — tests, compilation et ZIP extrait vérifiés](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40759375694).

Les contrôles du programme gelé ouvrent aussi l’accueil réel avant la grille. Ils confirment SQLite, les sauvegardes, les PDF, le solveur CP-SAT et les opérations hors ligne après extraction. Les sept contrôles de préparation de release et les trois contrôles de génération des notes passent également.

L’accueil utilise les calculs du planificateur pour ses alertes, heures et besoins. Les tests couvrent le tri des journées, l’état vide, la création et sa sauvegarde, le refus d’écrasement, la navigation clavier, les profils et l’empilement des cartes en petite fenêtre. Les règles de présence aux extrémités, les pauses, les archives et la conservation des groupes et des quarts verrouillés dans la génération sont vérifiées.

Un premier passage avait révélé un ratio invalide mal intercepté ; le garde-fou a été ajouté. Le test de démarrage portable utilisait ensuite un faux contrôle obsolète, ce qui ouvrait un dialogue sans réponse. Il utilise maintenant l’interface actuelle et échoue explicitement au lieu de bloquer sur un dialogue inattendu. Les suites natives complètes ci-dessus passent après ces corrections.

Les captures du dépôt montrent le code réel avec un adaptateur Qt5 local non livré. Un aperçu supplémentaire a été rendu et inspecté sous Qt6 réel, en grand format et à 720 × 600, sans défilement horizontal. La suite complète locale sous Qt6 et OR-Tools passe aussi (238 tests et six sous-cas). Les aperçus utilisent uniquement des données fictives.

La publication prend ses notes dans la section 0.3.1 du [CHANGELOG](../CHANGELOG.md) et refuse une version sans notes. Le manifeste autorise uniquement le SHA testé ci-dessus, après présentation de l’aperçu et demande explicite de publication. [Fichiers modifiés, hypothèses et limites](LIVRAISON_0_3_1.md).

Les essais sur le poste de l’école, avec un lecteur d’écran et une imprimante physique restent à réaliser. Aucune mise à jour automatique ni notarisation DeveloperID Mac n’est ajoutée. Conservez une sauvegarde du dossier `donnees` lors de la mise à jour.

## Livraison 0.3.0 — grille lisible et ratio escamotable

Le code exact vérifié et approuvé est `8c1863d5396106b97be42877ffe1fe121b81579c`. Les deux constructions natives ont réussi **208 tests chacune**, plus les **six sous-cas de pagination** et les contrôles du programme compilé et du ZIP extrait :

- [Windows — tests, compilation et ZIP portable vérifiés](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40718405454).
- [Mac Apple Silicon — tests, compilation et ZIP portable vérifiés](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40718405410).

Ces exécutions utilisent PySide6/Qt6 et OR-Tools réels. Les contrôles du binaire confirment le stockage SQLite, sa réouverture, la sauvegarde, les PDF, le solveur, le fonctionnement hors ligne et l’écriture dans le dossier portable après extraction. Aucun test n’est ignoré dans ces suites natives. Un avertissement de dépréciation d’un constructeur Qt utilisé par un ancien test subsiste ; il ne bloque aucun contrôle.

Les seize corrections initiales, les huit étapes de grille et la fermeture du ratio constituent vingt-cinq commits fonctionnels distincts. Un commit administratif supplémentaire enregistre uniquement cette preuve et le manifeste de publication du code testé. [Relevé des changements, hypothèses, fichiers et limites](CORRECTIONS_INTERFACE.md).

La couverture est calculée à la minute puis fusionnée lorsque les comptes présents/requis sont identiques. Les pauses payées ou non payées en sont exclues. Pour les dernières corrections de grille, seuls deux tests ciblés de ce calcul ont été ajoutés ; la suite existante n’a pas été refondue.

Le bouton **− Ratio / + Ratio** masque ou réaffiche la bande et rend ses 184 pixels aux quarts. La bande est visible au lancement ; le choix est conservé pendant la session, y compris après changement de date. La validation reste active lorsqu’elle est masquée. La commande Espace au clavier, le rafraîchissement et la sélection d’une plage masquée ont été vérifiés manuellement sur le code réel. Les PDF produits avec la bande visible ou masquée ont un texte identique : aucune bande de ratio, aucun compte de couverture et aucun panneau d’alertes n’y sont imprimés.

Les aperçus sont des rendus du code réel avec données fictives et un adaptateur Qt5 temporaire non livré. Ils complètent les contrôles natifs Qt6 ci-dessus. Les mesures locales donnent 72 % de hauteur utile pour la grille à 1480 × 940, 69 % avec alertes latérales et 66 % à 720 × 600 avec alertes fermées. Dans une petite fenêtre, les alertes s’empilent sous la grille et réduisent temporairement cette hauteur.

La certification avec un lecteur d’écran, l’impression sur une imprimante physique et un essai sur le poste de l’école restent à faire. Aucune mise à jour automatique ni notarisation DeveloperID Mac n’est ajoutée. Le dossier `donnees` doit être sauvegardé et conservé lors du remplacement du ZIP portable.

## Livraison 0.2.2 — interface épurée et formulaire clair

La [version 0.2.2](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/tag/v0.2.2) utilise le code `2319f51fb39dd6358a20a8b802650f71bae89e07`. Les deux constructions ont réussi **180 tests chacune**, plus les six sous-cas de pagination et les contrôles du programme compilé et du ZIP extrait :

- [Windows — tests et ZIP portable vérifiés](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40629432220).
- [Mac — tests et ZIP portable vérifiés](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40629432248).

Le dossier est accessible dans la barre latérale, avec ses commandes réelles d’ouverture, d’enregistrement, de duplication, d’historique et de sauvegarde. Les boutons Aujourd’hui sont retirés du planificateur et du sélecteur ; le repère de la date actuelle reste visible dans la grille.

Le formulaire des profils tient dans une seule fenêtre, sans onglets. Les tests vérifient les champs à 16 px, le contraste avec un parent en thème sombre, la présence de toutes les sections dans le grand format et le passage à une colonne avec défilement vertical dans une fenêtre de 540 × 600. Un profil complet est créé depuis le bouton de l’équipe, enregistré puis relu dans SQLite, avec son rang, ses heures exactes, sa couleur, ses disponibilités, ses absences et ses préférences.

Les vérifications ont permis de corriger des différences de dimensions natives et un problème de basculement des colonnes sur Windows. La mise en page utilise la largeur de la fenêtre visible, afin que les dimensions minimales du contenu ne bloquent pas son adaptation. Les captures publiées proviennent du code réel rendu sur le poste Linux avec l’adaptateur Qt5 temporaire, non livré ; les contrôles Qt6 sont ceux des deux constructions natives ci-dessus.

## Livraison 0.2.1 — sélecteur lisible et horaires uniquement

La [version 0.2.1](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/tag/v0.2.1) est publiée à la demande explicite du responsable du projet. Les constructions du code `61aeb0f4664ac55e880857ac90362e811bb4c5b4` ont réussi **176 tests chacune**, plus les six sous-cas de pagination et les contrôles des ZIP extraits :

- [Windows — 176 tests et paquet portable vérifié](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40622502409).
- [Mac — 176 tests et paquet portable vérifié](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40622502394).

Les nouveaux contrôles utilisent les véritables événements QTest pour le clavier, le survol et le focus ; ils vérifient les passages de mois/d’année, l’année bissextile, les limites de dates, la sélection simple, l’annulation et le chargement du planning après sélection. Un sous-processus Qt6 avec `QT_SCALE_FACTOR=2` vérifie une fenêtre de 360 × 330 pixels logiques à 200 %, sans réduire les cases ni les caractères. Le diagnostic du binaire gelé ouvre et dessine aussi le sélecteur, avec une cible minimale de 44 × 44.

Les paires de texte du sélecteur ont un contraste de 5,63:1 à 11,83:1. Les dates et contrôles principaux sont à 16 px minimum, le mois et l’année à 20 px gras. Les voisins affichent leur mois, les dates indisponibles sont barrées et aujourd’hui conserve contour et point sur la sélection. Les boutons principaux et les actions du calendrier se réorganisent dans une fenêtre étroite ; le sélecteur défile au besoin.

Le menu Dossier a été testé avec ses vrais rappels d’enregistrement, ouverture, duplication, historique, export/import de sauvegarde. Les activités et locaux historiques ne sont plus exposés dans l’interface quotidienne et ne bloquent pas les horaires ; leur présence dans les données a fait l’objet d’un test de conservation.

Le calendrier et le PDF utilisent les bornes exactes 6 h 50 et 17 h 35. Un quart quotidien extérieur à la plage configurée est signalé. Le nouvel exemple PDF a été rendu et inspecté avec huit éducateurs fictifs et des heures conformes aux règles de couverture.

Les aperçus publiés ont été produits par le code réel avec l’adaptateur Qt5 temporaire du poste Linux, non livré. Les vérifications Qt6 proviennent des exécutions natives ci-dessus. Un second aperçu local à 200 % confirme un DPR de 2, des cases de 44 pixels minimum et une police de 16 pixels ; il complète le test natif sans le remplacer.

Le premier passage a révélé un nom d’énumération Qt5 utilisé dans le test d’annulation. Le test a été adapté à Qt6 et les deux suites complètes ont ensuite réussi. Aucun contournement ou test ignoré n’a été introduit.

## Livraison 0.2.0 approuvée

Le code approuvé et publié est `46ab53061d9ed010f9f7f1a2b5cc32eedd458284`. Le code applicatif est identique au premier contrôle `407924c88a13385e598e46d7508a3bb420b5acee` ; le contexte de publication GitHub a été ajusté. Les deux constructions ont réussi **158 tests chacune**, puis les contrôles natifs des dossiers portables et des ZIP extraits :

- [Windows — 158 tests et ZIP vérifié](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40617443118).
- [Mac Apple Silicon — 158 tests et ZIP vérifié](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40617443092).

La [release v0.2.0](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/tag/v0.2.0) a été [publiée avec succès](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40617772875). Les six fichiers sont publics : deux ZIP portables, deux rapports natifs, le PDF d’exemple et les sommes SHA-256. Le premier essai de création a été refusé par GitHub ; la publication du contexte vérifié a réussi sans modification du logiciel.

Le nouveau PDF général a été testé avec le bouton réel de l’interface, les dimensions lettre paysage, la pagination, les heures exactes, les interruptions vides et les couleurs répétées. Les exemples joints ont été inspectés visuellement après rendu. Les polices et les modules de prévisualisation sont inclus dans les paquets ; aucune installation supplémentaire n’est nécessaire sur le poste final.

## PDF unique selon les modèles joints

Le nouveau rendu a été généré à partir des douze noms, des groupes, des heures et de la date de l’exemple joint : deux pages lettre paysage, huit lignes sur la première et quatre sur la seconde, avec quatre lignes vierges. Les deux pages ont été rendues et inspectées visuellement. Les libellés/blocs/légende de pauses du modèle ne sont pas repris, conformément à la demande explicite.

Six contrôles PDF réels vérifient la pagination 0/1/8/9/16/17 noms, les dimensions 792 × 612 pt, les en-têtes et légendes répétés, les coupures/pauses, la géométrie exacte d’un quart de 102 minutes, la couleur d’un groupe sur deux pages, les heures hors grille et la conservation du fichier précédent en cas d’échec. Ils passent localement avec ReportLab et extraction pypdf. Un test Qt supplémentaire fait produire le PDF par le véritable bouton Exporter.

La publication a ensuite été autorisée explicitement par le responsable du projet ; le PDF d’exemple est joint à la livraison. Le code de référence du rendu est `407924c88a13385e598e46d7508a3bb420b5acee`.

## Historique de préparation quotidienne 0.2.0

Une première demande du responsable du projet avait suspendu la publication 0.2.0. La publication a ensuite été autorisée dans la conversation ; le manifeste désigne explicitement le SHA approuvé. Les futures modifications de code ne sont pas publiées par cet accord.

Les nouvelles fonctions sont présentes dans les sources : écran quotidien inspiré de la référence, dates indépendantes, objectifs journaliers, PDF et génération limités à une date, couleurs distinctes à la création et rangs 1 à 11 sans rang intermédiaire obligatoire. Le calendrier conserve ses mouvements, redimensionnements et calculs à la minute.

Le format SQLite 2 garde les photographies historiques sans modification de leur contenu/checksum. Une copie au format 1 est créée avant migration. Les journées extraites d’anciennes semaines possèdent leurs propres versions ; les objectifs hebdomadaires ne sont pas convertis implicitement en objectifs journaliers.

Les nouveaux tests vérifient notamment deux dates de la même semaine, la duplication sans écrasement, la restauration, la copie de sécurité et l’import, les PDF de la seule date choisie, le solveur quotidien, les couleurs au-delà de onze profils et les rangs avec écarts. Le premier contrôle Windows a relevé une connexion SQLite laissée ouverte par le test de migration ; ce nettoyage a été corrigé. Le diagnostic du binaire a aussi été adapté pour relire une clé quotidienne.

Localement, 64 contrôles cœur ont passé ; 12 contrôles quotidiens passent avec un contrôle OR-Tools réservé aux runners natifs. Les 11 contrôles de chemins portables et les 7 contrôles de préparation des fichiers passent. Les 24 diagnostics d’interface exécutés avec l’adaptateur Qt5 temporaire passent ; cet adaptateur n’est pas livré. Les résultats des contrôles Qt6 et des ZIP natifs sont consignés ci-dessous après achèvement.

## Correctif AppTranslocation — version 0.1.2

La capture de l’utilisateur montrait une erreur `EROFS` dans `AppTranslocation/.../d/donnees`. Les contrôles précédents lançaient directement le binaire extrait et ne reproduisaient pas cette copie temporaire créée par Gatekeeper.

Le correctif interroge la correspondance native macOS pour retrouver le dossier portable d’origine. En cas d’indisponibilité, le démarrage demande explicitement le dossier extrait. Il ne crée aucune base en cas d’annulation et ne bascule pas vers un profil différent. Les réglages de sécurité et la quarantaine ne sont pas modifiés.

Les constructions natives ont réussi **132 tests chacune**, puis les contrôles des exécutables et ZIP portables extraits :

- [Mac — 132 tests et ZIP portable vérifié](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40612486730).
- [Windows — 132 tests et ZIP portable vérifié](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40612486807).

Ces résultats correspondent au code `dcba9f901a5fbd62ba1502707c599118962a8db2`. Les dix nouveaux tests couvrent le chemin d’origine, la réouverture des horaires existants, le choix d’un dossier, les dossiers incomplets ou en lecture seule et l’annulation. L’appel ctypes est exécuté sur le vrai framework macOS avec un chemin non transloqué. Les cas de copie temporaire sont reproduits par injection des chemins et du sélecteur ; le téléchargement suivi d’une ouverture Gatekeeper sur le poste de l’utilisateur reste à confirmer.

La [release publique v0.1.2](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/tag/v0.1.2) a été [publiée avec succès après contrôle des deux ZIP](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40612825567). Les cinq fichiers (deux ZIP, deux rapports et SHA256SUMS) sont téléversés et la release est publique.

Les onze contrôles unitaires de chemins portables passent également sous Linux. Les six contrôles de démarrage ont passé un diagnostic local avec un adaptateur Qt5 temporaire avant la validation PySide6 native. Aucun adaptateur n’est livré. Aucun changement de schéma ni migration des horaires n’est nécessaire.

## Interface simplifiée — version 0.1.1

Les deux constructions de l’interface simplifiée ont réussi **122 tests chacune**, avec PySide6/Qt6 et OR-Tools réels :

- [Windows — 122 tests et ZIP portable vérifié](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40150886874).
- [macOS 15 Apple Silicon — 122 tests et ZIP portable vérifié](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40150886862).

Ces résultats correspondent au code `3d727674dc1de9558d5388a96a1e3124b8022b00`. Quatre nouveaux tests vérifient le panneau d’alertes fermé par défaut, les commandes fonctionnelles du Menu, la réouverture des réglages d’affichage et les restrictions d’édition. Le calendrier dispose de plus de hauteur et les fiches de l’équipe sont compactes. Aucun changement du format des données n’est nécessaire.

Les téléchargements destinés aux utilisateurs sont les ZIP des [Releases publiques](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/latest), téléchargeables sans compte. Les liens d’artefacts Actions ci-dessous sont conservés pour la traçabilité des contrôles historiques ; ils peuvent exiger une connexion et expirer.

Le contrôle de publication possède sept tests indépendants : il refuse les rapports incomplets, les versions/plateformes incorrectes, les ZIP corrompus, les marqueurs manquants et l’absence d’une plateforme. Il valide les deux plateformes avant de préparer les fichiers et leurs sommes SHA-256.

## Publication publique vérifiée

La [release v0.1.1](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/tag/v0.1.1) contient directement les ZIP Windows x64 et macOS arm64, les deux rapports après extraction et leurs sommes SHA-256. Les cinq fichiers sont publiés, sans brouillon ni préversion.

Les binaires publiés correspondent au code `38f535568ca2ce62d2103dbf97ddd520ee0276a1` :

- [Windows — 122 tests et contrôles portables réussis](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40609894459).
- [Mac — 122 tests et contrôles portables réussis](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40609894511).
- [Publication — sept tests du contrôle, validation des deux ZIP et téléversement réussis](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40610162523).

La publication remplace les liens d’artefacts Actions pour la distribution aux utilisateurs. Les artefacts Actions restent utiles pour les diagnostics de fabrication.

## Application et interface modernisée

La version modernisée a réussi **110 tests sur Windows et 110 tests sur macOS 15 Apple Silicon**, avec Qt6/PySide6 et OR-Tools réellement installés. Le calendrier Jour/Semaine, le déplacement et redimensionnement à la minute, les formulaires, la recherche, l’annulation, les relèves, l’ouverture/fermeture, SQLite, les archives, les PDF et le solveur font partie des tests.

Premières exécutions natives réussies de cette interface :

- [Windows — 110 tests, compilation, installation et désinstallation](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40140615626).
- [Mac — 110 tests, application et ancien DMG](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40140615627).

Ces anciens installateur et DMG ne constituent plus le mode de livraison principal : le poste cible ne permettant pas d’installation, la distribution a été convertie en dossiers portables.

## Livraison portable sans installation

Le marqueur `portable.mode` détermine automatiquement le stockage dans `donnees`, à côté du programme. Le bundle Mac déclare également cette intention dans son fichier Info.plist ; les données ne sont jamais écrites à l’intérieur de l’application signée. Les versions historiques sans mode portable conservent leur emplacement de profil antérieur.

Sept tests locaux supplémentaires ont vérifié les chemins Windows/Mac, le profil historique, le choix explicite d’une base, le mode source et le déplacement du dossier complet avec réouverture de la même base SQLite. Les chemins temporaires sont normalisés pour les liens macOS et les noms courts Windows. La traduction des boutons standard Qt en français fait aussi l’objet d’un test.

Les deux distributions portables ont réussi **118 tests chacune**, puis les contrôles natifs du paquet préparé et de son ZIP extrait :

- [Windows — exécution portable réussie](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657387), [ZIP et rapports](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657387/artifacts/12578819035).
- [macOS 15 Apple Silicon — exécution portable réussie](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657434), [ZIP arm64 et rapports](https://github.com/GraphicShack/Planificateur-Service-de-garde/actions/runs/40141657434/artifacts/12579051978).

Ces résultats correspondent au code `373592c5eed4ba02e8dbc800a59a041d26e491e9`. La construction Windows par défaut n’a utilisé aucun installateur ni Inno Setup ; la construction Mac n’a pas copié l’application dans Applications. Les trois rapports de chaque plateforme confirment le mode portable et l’écriture réelle dans le dossier du logiciel.

Chaque contrôle du paquet portable doit confirmer :

- la bonne version, le binaire gelé et le moteur Qt natif Windows ou cocoa ;
- le logo SVG et la traduction française inclus ;
- la couverture à la minute et le calendrier dessiné ;
- une véritable sauvegarde/réouverture SQLite et une copie de sécurité ;
- les PDF ReportLab ouverts et rendus par Qt, et la disponibilité des modules d’impression ;
- une véritable génération CP-SAT, contrôlée par le validateur ;
- les opérations avec les sockets Python interdites ;
- l’écriture des données dans le dossier portable ;
- les mêmes contrôles après extraction du ZIP dans un nouvel emplacement.

Les données de vérification sont temporaires puis supprimées. Un dossier de fabrication contenant des données personnelles est refusé avant repackaging.

## Vérifications de développement

Le harnais `python scripts/check_core_without_pytest.py` a réussi 64 contrôles cœur avec Python3.12 sous Linux avant la disponibilité des runners natifs. Les deux tests `python -m unittest discover -s tests -p test_optimizer_candidates.py -v` ont aussi réussi. Ces résultats historiques sont désormais complétés par les suites pytest natives.

Le rendu de `docs/apercu-interface.png` a été produit à partir du véritable code de l’interface avec un adaptateur Qt5/PySide2 temporaire, disponible dans l’environnement Linux. Cet adaptateur n’est pas livré. La validation Qt6 provient des exécutions natives indiquées ci-dessus.

## Prise en main sur le poste cible

La souris, la lisibilité à la résolution du poste, l’imprimante physique et les autorisations d’exécution/écriture doivent encore être essayées dans l’école. Les tests d’impression chargent les modules et rendent les PDF ; ils n’utilisent pas d’imprimante physique.

Le ZIP portable n’installe aucun programme sur le système. Le poste doit néanmoins autoriser son exécution. Le paquet Mac est signé localement ; une distribution externe reconnue par Gatekeeper nécessite une signature DeveloperID et une notarisation appropriées.
