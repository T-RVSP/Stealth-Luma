# Stealth Luma

Gestionnaire graphique pour **Stealth Luma**, déverrouilleur Steam en **mode furtif**.  
Il prépare l’AppList, gère vos profils (comptes Steam et jeux) et lance Steam avec les fichiers requis.

**Développé par [ShyninG](https://github.com/T-RVSP)** — Version **1.6.7**

---

## Installation

**[Télécharger Stealth Luma 1.6.7](https://github.com/T-RVSP/Stealth-Luma/releases/latest)**

1. Téléchargez `Stealth-Luma-Setup-1.6.7.exe` depuis la page [Releases](https://github.com/T-RVSP/Stealth-Luma/releases)
2. Lancez l’installateur et choisissez la langue (français ou anglais)
3. Ouvrez **Stealth Luma** depuis le menu Démarrer ou le raccourci bureau

### Prérequis

- Windows 10/11
- [Steam](https://store.steampowered.com/) installé

### Mise à jour

Au démarrage, l’application peut vérifier GitHub et proposer de télécharger la dernière version de `Stealth-Luma-Setup-X.exe`. L’installateur désinstalle l’ancienne version puis installe la nouvelle (profils et paramètres conservés).

Pour mettre à jour manuellement, téléchargez le dernier `Stealth-Luma-Setup-X.exe` sur [Releases](https://github.com/T-RVSP/Stealth-Luma/releases) et lancez-le.

### Désinstallation

Via **Paramètres Windows** → Applications, ou `unins000.exe` dans le dossier d’installation.

---

## Fonctionnalités

### Profils

| Type | Description |
|------|-------------|
| **Compte Steam** | Profil lié à un compte enregistré sur la machine (mode Famille). Non supprimable. |
| **Profil jeu** | Créé via **+ Profil** à partir d’un jeu installé ; charge automatiquement les DLC. |

- Limite de **168 entrées** par profil (AppList)
- **Charger** : importe la configuration (jeu + DLC) du profil correspondant au jeu sélectionné
- **Ajouter** / **Retirer** : gère les jeux et DLC du profil actif

### Mode furtif (Lancer)

Au clic sur **Lancer** :

1. Fermeture de Steam si nécessaire
2. Exécution de `DeleteSteamAppCache.exe`
3. Génération de l’AppList dans le dossier Steam
4. Déploiement de `user32SF.dll` → `user32.dll` dans Steam
5. Relance de Steam en mode furtif
6. Réduction de l’application dans la zone de notification

À la **fermeture** de Stealth Luma, `user32.dll` est retiré ou restauré dans Steam, puis Steam est relancé normalement si nécessaire.

### Paramètres

- Chemin Steam
- **Version Steam** affichée + bouton **Restaurer** (`steam.cfg`, mise à jour officielle)
- Downgrade Steam automatique au premier lancement
- Vérification des mises à jour au démarrage
- Interface **bilingue FR / EN**

### Éditeur manuel

Tableau central pour ajouter des jeux / DLC non détectés (ID Steam, nom, type Game/DLC), puis **Ajouter** au profil actif.

---

## Données locales

| Élément | Emplacement |
|---------|-------------|
| Configuration | `%LOCALAPPDATA%/GLR_Manager/config.json` |
| Profils | `%LOCALAPPDATA%/GLR_Manager/Profiles/` |
| GLinject | `%LOCALAPPDATA%/GLR_Manager/GLinject/` |
| Logs | `%LOCALAPPDATA%/GLR_Manager/errors.log` |

---

## Risques

L’utilisation d’un déverrouilleur Steam comporte un **risque** pour votre compte ou vos jeux (bannissement possible).  
Certains titres détectent les fichiers injectés ou vérifient la possession des jeux côté serveur.  
Stealth Luma ne fonctionne pas avec tous les jeux.

---

## Crédits

| Auteur | Rôle |
|--------|------|
| **[ShyninG](https://github.com/T-RVSP)** | Stealth Luma — développement principal |
| **[BlueAmulet](https://github.com/BlueAmulet)** | Fork GreenLuma 2024 Manager |
| **[ImaniiTy](https://github.com/ImaniiTy)** | GreenLuma Reborn Manager (original) |
| **Steam006** | GreenLuma (moteur sous-jacent) |

## Licence

Voir le fichier [LICENSE](LICENSE).
