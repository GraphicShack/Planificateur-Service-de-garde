# Demande d'autorisation — Service informatique (TI)

> Fiche à remettre au service informatique de la commission scolaire (centre de
> services scolaire) pour faire **autoriser** ou **déployer** le logiciel
> *Planificateur — Service de garde* sur un poste géré.
>
> Le logiciel n'est pas malveillant : c'est une application de bureau interne,
> **portable et non signée**, ce qui déclenche normalement le blocage d'exécution
> d'un poste administré (message « Vous ne disposez peut-être pas des
> autorisations appropriées »). Ce document fournit les éléments nécessaires à
> une décision éclairée.

## 1. Identification du logiciel

| Élément | Valeur |
| :--- | :--- |
| Nom | Planificateur — Service de garde |
| Version | 0.5.2 |
| Éditeur | GraphicShack (projet maison) |
| Usage | Planification locale des horaires d'éducatrices et d'éducateurs du service de garde (journées pédagogiques) |
| Plateforme | Windows 10 (version 1809 / 10.0.17763) ou 11, 64 bits |
| Technologie | Python 3.12, interface Qt (PySide6 6.12), solveur OR-Tools, PDF ReportLab |
| Code source | Public : https://github.com/GraphicShack/Planificateur-Service-de-garde |
| Version officielle | https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/tag/v0.5.2 |

## 2. Posture de sécurité et de confidentialité

Ces propriétés sont vérifiées automatiquement à chaque version par la chaîne de
construction (rapport `verification-Windows-x64.json` joint à la release) :

- **Entièrement hors ligne.** Aucune opération réseau (`offline_operations: true`).
  Le logiciel ne se connecte à aucun serveur, n'envoie aucune donnée et ne
  requiert pas Internet pour fonctionner.
- **Sans installation système.** Version portable : aucune écriture dans
  `Program Files` ni dans le registre système, **aucun droit administrateur requis**.
- **Sans compte ni abonnement.** Aucune authentification, aucun service tiers.
- **Données locales.** Les horaires, profils et sauvegardes restent dans le
  sous-dossier `donnees`, à côté de l'exécutable, sur le poste. Rien n'est
  transmis à l'extérieur.

**Note Loi 25.** Le logiciel traite des renseignements personnels d'employés
(noms, disponibilités, horaires). Comme le traitement est **entièrement local et
hors ligne**, aucune donnée ne quitte le poste ni l'environnement de la
commission scolaire. Aucun transfert vers un service infonuagique n'a lieu.

## 3. Intégrité des fichiers (SHA-256)

Empreintes officielles de la version 0.5.2 (fichier `SHA256SUMS.txt` joint à la
release) :

```
817e2b3692685c063aee5014d3718c053146d35a3770f01d04c74257e8902366  Planificateur-SDG-0.5.2-Windows-x64-Portable.zip
```

Pour vérifier le téléchargement, dans PowerShell :

```powershell
Get-FileHash .\Planificateur-SDG-0.5.2-Windows-x64-Portable.zip -Algorithm SHA256
```

La valeur obtenue doit correspondre à celle ci-dessus.

## 4. Options d'autorisation / de déploiement

Trois voies possibles, de la plus durable à la plus simple. **L'option A est
recommandée.**

### Option A — Règle AppLocker / WDAC par éditeur (après signature) ✅ recommandé

Si l'éditeur fait signer l'exécutable avec un certificat de signature de code
(Authenticode), la TI peut créer **une seule règle par éditeur** qui autorise
l'application **et toutes ses futures mises à jour** sans nouvelle demande.
C'est la solution la plus pérenne. *(La signature est en préparation côté
éditeur.)*

### Option B — Règle par empreinte ou par chemin (sans signature, immédiat)

En attendant la signature, la TI peut autoriser :

- **par empreinte (hash)** : l'outil AppLocker génère l'empreinte à partir de
  `Planificateur-SDG.exe` extrait. À refaire à chaque nouvelle version.
- **par chemin approuvé** : autoriser l'exécution depuis un dossier maîtrisé par
  la TI (p. ex. un dossier déployé par la commission scolaire), et non depuis
  `Téléchargements`.

### Option C — Déploiement en Centre logiciel (SCCM / Intune)

Le projet fournit un installateur Inno Setup **par utilisateur, sans droit
administrateur** (`PrivilegesRequired=lowest`, installation dans
`%LocalAppData%\Programs\GardePlan`). Il se prête à un déploiement silencieux.

> L'installateur n'est pas inclus dans la release portable actuelle ; l'éditeur
> peut le fournir sur demande (construit via `scripts/build-windows.ps1
> -BuildInstaller`), idéalement signé.

Commandes de déploiement silencieux :

```text
Installation   : Planificateur-SDG-Installation.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG
Désinstallation : "%LocalAppData%\Programs\GardePlan\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Les données personnelles de l'utilisateur (dossier `donnees` / profil local) ne
sont volontairement pas supprimées à la désinstallation.

## 5. Contact

- Dépôt et code source : https://github.com/GraphicShack/Planificateur-Service-de-garde
- Éditeur : GraphicShack
- Toute question technique peut être adressée à l'éditeur via le dépôt.

---

## Annexe — Modèle de courriel à la TI

> À envoyer de préférence par la direction de l'école ou la personne
> responsable du service de garde (une demande interne pèse davantage).

**Objet :** Demande d'autorisation d'un logiciel — Planificateur Service de garde

Bonjour,

Le service de garde de [nom de l'école] souhaite utiliser un logiciel de
planification des horaires des éducatrices et éducateurs lors des journées
pédagogiques. Son exécution est actuellement bloquée sur un poste géré (message
« Vous ne disposez peut-être pas des autorisations appropriées »).

Il s'agit d'une application de bureau interne, portable et hors ligne :

- **Nom :** Planificateur — Service de garde, version 0.5.2 (éditeur : GraphicShack)
- **Fichier :** `Planificateur-SDG.exe` (archive portable Windows x64)
- **Source officielle :** https://github.com/GraphicShack/Planificateur-Service-de-garde/releases/tag/v0.5.2
- **Empreinte SHA-256 de l'archive :**
  `817e2b3692685c063aee5014d3718c053146d35a3770f01d04c74257e8902366`

Caractéristiques pertinentes :

- entièrement hors ligne (aucune connexion réseau, vérifié à chaque version) ;
- aucune installation système ni droit administrateur requis ;
- données conservées localement sur le poste, aucun transfert externe.

Pourriez-vous **autoriser ce logiciel** (règle par empreinte ou par chemin
approuvé), ou nous indiquer la **procédure de demande** à suivre ? Une fiche
technique détaillée est jointe (ou disponible sur demande).

Merci de votre aide,

[Nom, fonction, école]
