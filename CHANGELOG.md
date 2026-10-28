# Notes de version

Chaque release reprend la section correspondant à sa version. Une section doit
être ajoutée ici avant de publier ; le contrôle de publication refuse une
version sans notes. Les téléchargements sont dans les [Releases GitHub](https://github.com/GraphicShack/Planificateur-Service-de-garde/releases).

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
