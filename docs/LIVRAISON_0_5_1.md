# Livraison 0.5.1 — mise à jour compatible avec les exports existants

## Résultat

La 0.5.1 conserve toutes les nouveautés de la [0.5.0](LIVRAISON_0_5_0.md) : assistant de mise à jour portable, bilan, nom de session à l’accueil, continuité privilégiée lors de la génération et grille Proposition affichée avant application.

Le correctif distingue le programme distribué des documents ajoutés ensuite. Un PDF exporté à côté du logiciel ne bloque plus la mise à jour ni le retour. Les fichiers, dossiers et liens déclarés dans l’inventaire restent contrôlés ; un exécutable altéré est toujours refusé. Les documents supplémentaires restent intacts dans leur dossier d’origine et ne sont pas copiés dans le nouveau programme. Les ZIP livrés gardent une vérification stricte de leur contenu.

Une demande de publication seule ne déclenche plus deux nouvelles compilations : elle référence les résultats du code exact déjà construit. Les notes sont ajoutées au CHANGELOG et reprises dans la Release GitHub.

## Vérification

Les 21 tests directement liés à l’assistant et à la copie passent localement, dont le nouveau cas avec PDF personnel, préparation, retour, conservation des documents et refus d’un exécutable corrompu. Les dix tests des scripts de publication passent. La suite complète locale réussit **340 tests et six sous-cas** en 122,39 s, sans test ignoré. Les suites Windows et Mac réussissent aussi 340 tests et six sous-cas. Les trois contrôles natifs de chaque plateforme passent, dont le ZIP extrait et les lancements des copies préparée et restaurée. La version 0.5.1 est publiée avec ses six fichiers publics ; les preuves figurent dans [État des vérifications](ETAT_VERIFICATION.md).

## Aperçus

L’interface reste celle montrée pour la 0.5.0 : [accueil](accueil-0.5.0.png), [proposition affichée en premier](proposition-0.5.0.png), [bilan](bilan-0.5.0.png) et [assistant](mise-a-jour-0.5.0.png). Les captures utilisent des données fictives.

## Hypothèses et limites

- Depuis 0.4.0 ou avant, fermer puis sauvegarder et transférer `donnees` dans le dossier 0.5.1 extrait. Depuis 0.5.0, choisir le ZIP 0.5.1 dans Dossier → Mettre à jour depuis un ZIP. Si la 0.5.0 refuse à cause d’un PDF ajouté dans le dossier, déplacer ce document à côté du dossier ou utiliser le transfert manuel après sauvegarde.
- Les PDF et autres fichiers supplémentaires restent dans l’ancien dossier ; ils ne sont pas fusionnés ni déplacés automatiquement. Le retour conserve l’état des données d’avant mise à jour, sans supprimer le travail plus récent.
- Les contraintes de couverture et le plafond de huit heures priment sur la continuité. Des coupures nécessaires restent possibles ; les pauses sont conservées. La recherche reste limitée en temps et affiche ses limites.
- Aucun téléchargement automatique, changement du PDF, compte, installateur, signature ou notarisation ajouté. Les essais physiques sur le poste de l’école et le lancement entre deux versions distribuées différentes restent à réaliser. Les contrôles natifs de copie et retour lancent effectivement les binaires de la version compilée ; les tests de données couvrent des numéros de version différents.

## Fichiers du correctif

- `gardeplan/portable_package.py`, `gardeplan/updater.py` : vérification des chemins connus d’un dossier déjà utilisé, inventaire strict des ZIP.
- `tests/test_updater.py` : régression sur les exports personnels et l’intégrité du programme.
- `.github/workflows/build-windows.yml`, `.github/workflows/build-macos.yml` : ignorer une demande de publication seule pour éviter les compilations redondantes.
- `gardeplan/__init__.py`, `pyproject.toml`, `.github/release-request.json` : version et source vérifiée à publier.
- `CHANGELOG.md`, `README.md`, `docs/GUIDE.md`, `docs/ARCHITECTURE.md`, `docs/LIVRAISON_0_5_0.md`, ce rapport et `docs/ETAT_VERIFICATION.md` : notes, procédure, limites et preuves.

La liste des fichiers et hypothèses des nouveautés initiales reste dans le [rapport 0.5.0](LIVRAISON_0_5_0.md).
