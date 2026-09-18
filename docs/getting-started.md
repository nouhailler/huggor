← [Documentation](index.md)

# Bien démarrer

## Présentation et compatibilité

Huggor (« 🤗 HF Explorer ») est une application **web**, pas une application mobile native ni une PWA installable de façon systématique :

- Elle tourne dans un navigateur, en local ou déployée (Hugging Face Spaces, Render — voir le [README](../README.md#déploiement-sur-hugging-face-spaces)).
- Le mode PWA (installation sur l'écran d'accueil, icône dédiée) est fourni par Gradio et s'active **automatiquement uniquement** quand l'application tourne sur un Hugging Face Space. Sur Render ou en local, elle reste une page web classique sauf à ajouter explicitement `pwa=True` dans `app.py` (non fait à ce jour).
- Compatibilité : tout navigateur récent (desktop ou mobile) supportant JavaScript. Sur petit écran (< 768px), la barre d'onglets laisse place à un [menu hamburger](guide.md#-menu-hamburger-mobile) — voir [Compatibilité](reference.md#compatibilité) pour le détail.

Il n'existe pas de version « Android » ou « iOS » packagée séparément. Il existe en revanche un **paquet Debian/Ubuntu** pour un usage desktop Linux — voir plus bas.

## Installation

### En local (développement ou usage personnel)

Prérequis : Python 3.10 ou supérieur.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Un token Hugging Face est facultatif pour les modèles publics, nécessaire pour les ressources privées ou protégées — voir [Permissions](permissions.md). Renseignez-le dans `.env` (`HF_TOKEN=...`) ou authentifiez la machine avec `hf auth login`. Ne jamais versionner `.env`.

### Paquet Debian/Ubuntu

```bash
sudo apt install ./hf-explorer_0.1.0_all.deb
hf-explorer
```

Téléchargez le `.deb` depuis les [releases GitHub](https://github.com/nouhailler/huggor/releases). Python 3.10+ requis (Ubuntu 22.04+, Debian 12+). Au premier lancement, une connexion Internet est nécessaire pour installer les dépendances Python dans un environnement isolé — gardez le terminal ouvert. L'entrée **HF Explorer** du menu des applications ouvre aussi le lanceur.

### Accès via une instance déjà déployée

Si quelqu'un partage un lien Hugging Face Space (`https://huggingface.co/spaces/...`) ou Render (`https://....onrender.com`), aucune installation n'est nécessaire : ouvrez le lien dans un navigateur. Sur le tier gratuit, une instance inactive se met en veille et le premier chargement peut prendre 30 à 50 secondes (voir [Dépannage](troubleshooting.md)).

## Premier lancement

```
Lancement (`python app.py` ou lien déployé)
    ↓
Avertissement légal (première visite de ce navigateur uniquement)
    ↓
« J'ai compris » (ou « Voir les détails » d'abord)
    ↓
Écran principal (onglet « 🔍 Recherche » actif par défaut)
    ↓
Champ « Mot-clé » déjà pré-rempli avec « Gemma » (exemple fonctionnel immédiat)
    ↓
Appuyer sur Entrée ou cliquer « 🔍 Rechercher »
    ↓
Résultats affichés, chacun avec un bouton « Voir détails → »
```

À la toute première visite d'un navigateur, un avertissement légal (« ⚠️ Information importante ») s'affiche avant l'écran principal — voir [Informations légales](legal.md). Il ne réapparaît plus ensuite sur ce même navigateur (mémorisé dans son `localStorage`), et reste consultable à tout moment depuis le pied de page ou l'écran [« ℹ️ À propos »](guide.md#a-propos). Une **visite guidée** en 5 étapes est aussi disponible, mais uniquement à la demande depuis l'écran [« ⚙️ Paramètres »](guide.md#-paramètres) (« 🧭 Revoir la visite guidée ») — elle ne s'affiche jamais automatiquement. Aucune permission native de type caméra/GPS n'est utilisée — voir [Permissions](permissions.md). Le bandeau en haut de l'écran indique immédiatement si un token Hugging Face est configuré (« 🟢 Token HF configuré ») ou non (« Accès public »).

Aucune configuration initiale n'est requise : l'application fonctionne sans compte, sans inscription, sans token. Le seul réglage possible est l'authentification Hugging Face (voir [Permissions](permissions.md)), qui peut être ajoutée à tout moment sans redémarrer l'application (relancer `python app.py` après avoir modifié `.env`, ou re-fournir `HF_TOKEN` côté serveur pour un déploiement).

## Mise à jour et désinstallation

- **En local / dépôt Git** : `git pull` puis `pip install -r requirements.txt` si les dépendances ont changé.
- **Paquet Debian** : `sudo apt install ./hf-explorer_<nouvelle-version>_all.deb` ; les mises à jour conservent les favoris et l'historique (stockés dans `${XDG_DATA_HOME:-~/.local/share}/hf-explorer/`).
- **Désinstallation (paquet Debian)** : `sudo apt remove hf-explorer` — les données locales (`data/`) sont conservées par défaut, pas supprimées automatiquement. Pour les effacer manuellement : supprimer `${XDG_DATA_HOME:-~/.local/share}/hf-explorer/`.
- **Déploiement (Spaces/Render)** : la désinstallation consiste à supprimer le Space ou le service Render depuis leur interface respective ; voir le [README](../README.md) pour les liens.
