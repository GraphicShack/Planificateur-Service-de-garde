# Livraison 0.5.0 — mise à jour, bilan et accueil personnalisé

## Fonctionnalités

- **Dossier → Mettre à jour depuis un ZIP** : contrôle du manifeste, de la version, de la plateforme, de l’architecture, des chemins et des empreintes SHA-256 ; préparation dans un dossier séparé avec données SQLite, versions, préférences et sauvegardes connues. Les opérations longues utilisent un fil de travail et un indicateur réel, sans bloquer l’interface. Aucun ancien fichier n’est écrasé.
- **Fermer et démarrer** : dernière sauvegarde, actualisation de la copie et lancement indépendant du nouveau programme. Un premier démarrage différé reprend également la dernière base enregistrée, après fermeture de l’ancienne session. Un verrou de données empêche une copie pendant l’utilisation de la source ou de la cible.
- **Revenir à la version précédente** : ancien programme contrôlé et état des données d’avant mise à jour, dans un autre dossier. Le travail plus récent reste conservé dans sa version et dans une copie supplémentaire.
- **Bilan avant application** : couverture, erreurs, avertissements, heures, horaires coupés, interruptions, préférences respectées, personnes sans heures et quarts verrouillés. Les noms et souhaits non satisfaits sont précisés. Les détails avant/après sont conservés et un verrou altéré empêche l’application.
- **Génération sans petits trous inutiles** : réduction des personnes avec un horaire coupé, puis de la durée des interruptions, avant la minimisation du coût rémunéré. Les pauses restent dans les quarts ; une limite ou une indisponibilité peut conserver une coupure nécessaire.
- **Bonjour [nom de session] !** à l’accueil. Lecture locale du nom de connexion, ou du nom complet du compte Mac ; nettoyage des caractères non affichables, texte brut et repli générique. Aucun compte ni envoi de données.

Les règles de couverture, les huit heures maximum, les relèves, les pauses, les rangs et le PDF restent identiques. Les notes sont reprises automatiquement depuis le CHANGELOG dans chaque Release GitHub.

## Aperçus

[Accueil](accueil-0.5.0.png) · [Bilan](bilan-0.5.0.png) · [Assistant](mise-a-jour-0.5.0.png).

Captures de l’application Qt6 réelle avec des profils fictifs et le nom de session fictif Camille. Le bilan d’une correction locale montre explicitement une alerte préexistante restante : son application conserve le statut brouillon.

## Vérification

Cinq cas supplémentaires vérifient la continuité par défaut, les interruptions imposées par le maximum ou les disponibilités, les pauses et les changements de groupe adjacents. Les tests ciblés couvrent les noms de session et le repli, le comptage des interruptions et des souhaits, les absences, les verrous, les données copiées et conservées après retour, les ZIP altérés, les traversées de chemins, les collisions, les liens Mac, les plateformes incompatibles, une ouverture différée, les verrous SQLite, l’interface réelle de l’assistant et un échec de lancement. La suite complète locale réussit **339 tests et six sous-cas** en 126,89 s, sans test ignoré. Les dix contrôles de publication et le diagnostic Qt6 hors ligne réussissent aussi. Les constructions natives restent le dernier contrôle avant livraison.

Les contrôles natifs du ZIP compilé préparent une copie du logiciel, modifient la base source après préparation, démarrent réellement le nouvel exécutable et vérifient les données reprises. Ils restaurent ensuite une copie de l’ancien programme et la démarrent aussi. Ces deux lancements utilisent le binaire de la version compilée, avec un mode de contrôle interne : le retour entre deux versions différentes est couvert par les tests de données ; le lancement interversions sera vérifiable au prochain ZIP plus récent. La publication exige les résultats `session_greeting`, `proposal_report` et `portable_update_archive` sur les deux plateformes. Les preuves et le code exact sont consignés dans [État des vérifications](ETAT_VERIFICATION.md).

## Hypothèses et limites

- **Premier passage depuis 0.4.0 ou avant : manuel.** Ces versions ne possèdent pas encore l’assistant. Fermer, sauvegarder puis transférer `donnees` dans le dossier 0.5.0 extrait. L’assistant traite ensuite les ZIP officiels plus récents, de la même plateforme et architecture.
- Le nom affiché est celui du compte local fourni par le système ; sur Windows, il peut s’agir du nom de connexion plutôt que du nom complet. Aucune reconnaissance biométrique, aucun profil utilisateur séparé ni champ de personnalisation supplémentaire.
- Le ZIP est apporté par la personne utilisatrice. Pas de recherche ou téléchargement automatique, de connexion réseau, de signature d’éditeur ni de notarisation Mac. L’inventaire détecte une copie incomplète ou altérée ; il n’authentifie pas l’éditeur.
- Les dossiers ancien et nouveau doivent être gardés jusqu’au premier lancement. Le retour nécessite l’ancien programme et sa sauvegarde vérifiée ; il restaure les données d’avant mise à jour, sans fusion des modifications plus récentes. Les bases deviennent indépendantes après activation. Aucune mise à jour de la version en cours d’exécution ni suppression automatique des anciennes versions.
- Les exports PDF placés ailleurs et les fichiers externes inconnus ne sont pas déplacés automatiquement. Les dossiers de sauvegarde contenant des liens sont refusés pour éviter une copie ambiguë.
- Le moteur conserve sa recherche bornée et les contraintes métier ; l’objectif de continuité passe désormais avant le coût rémunéré. La correction ciblée reste locale. Les essais physiques sur le poste de l’école et une future mise à jour interversions restent à réaliser.

## Fichiers modifiés

- Données et calculs : `gardeplan/session_user.py`, `gardeplan/proposal_summary.py`, `gardeplan/portable_package.py`, `gardeplan/updater.py`, `gardeplan/preferences.py`, `gardeplan/optimizer.py`, `gardeplan/optimizer_priorities.py`.
- Interface et démarrage : `gardeplan/ui/home.py`, `gardeplan/ui/proposal.py`, `gardeplan/ui/proposal_report.py`, `gardeplan/ui/update.py`, `gardeplan/ui/main_window.py`, `gardeplan/app.py`.
- Contrôles et distribution : `gardeplan/installation_check.py`, `gardeplan/update_check.py`, `scripts/build-windows.ps1`, `scripts/build-macos.sh`, `scripts/prepare_release.py`, `scripts/test_prepare_release.py`, `scripts/release_notes.py`.
- Tests : `tests/test_session_user.py`, `tests/test_proposal_summary.py`, `tests/test_updater.py`, `tests/test_update_ui.py`, `tests/test_generation_continuity.py`.
- Version et documentation : `gardeplan/__init__.py`, `pyproject.toml`, `CHANGELOG.md`, `README.md`, `docs/GUIDE.md`, ce rapport, `docs/ETAT_VERIFICATION.md`, les trois captures 0.5.0 et `.github/release-request.json`.
