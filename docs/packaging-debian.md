← [Documentation](index.md)

# Paquet Debian / Ubuntu

## Installer en une commande (sans sudo)

```bash
curl -fsSL https://raw.githubusercontent.com/nouhailler/huggor-downloads/main/install.sh | bash
```

L'installateur ([`install.sh`](https://github.com/nouhailler/huggor-downloads/blob/main/install.sh), dépôt [huggor-downloads](https://github.com/nouhailler/huggor-downloads)) :

1. détermine la dernière release publiée (ou celle demandée avec `--release X.Y.Z`) ;
2. télécharge `hf-explorer_X.Y.Z_all.deb` en HTTPS et **vérifie son SHA-256** (il refuse l'installation en cas d'écart) ;
3. ouvre l'archive sans droits root (`dpkg-deb` ou `ar`) et place le code dans `~/.local/lib/huggor` ;
4. crée la commande `~/.local/bin/huggor` et une entrée « HF Explorer » dans le menu des applications (sauf avec `--no-desktop`).

Ensuite, lancer `huggor` et ouvrir <http://127.0.0.1:7860>. Si la commande est introuvable, ajouter `~/.local/bin` au `PATH`.

Options : `--release X.Y.Z`, `--prefix CHEMIN` (racine, défaut `~/.local`), `--no-desktop`, `--uninstall`, `--help`. Pour lire le script avant de l'exécuter, le télécharger avec `curl -fsSL <url> -o install.sh` puis l'ouvrir.

**Prérequis** : Linux, `python3` ≥ 3.10 avec le module `venv` (Debian/Ubuntu : `sudo apt install python3-venv`), `curl`, `tar`, `sha256sum`, `flock`, et `dpkg-deb` ou `ar`. Le paquet est indépendant de l'architecture. Fonctionne aussi hors Debian/Ubuntu (`À vérifier` : testé uniquement sur Debian).

**Mettre à jour** : relancer la même commande ; favoris et cache sont conservés.

**Désinstaller** :

```bash
curl -fsSL https://raw.githubusercontent.com/nouhailler/huggor-downloads/main/install.sh | bash -s -- --uninstall
```

Les favoris, le cache et l'environnement Python restent dans `${XDG_DATA_HOME:-~/.local/share}/hf-explorer/` ; supprimer ce dossier pour les effacer.

## Installer le paquet `.deb` (avec sudo)

Télécharger `hf-explorer_X.Y.Z_all.deb` et son `.sha256` depuis les [releases de huggor-downloads](https://github.com/nouhailler/huggor-downloads/releases), puis :

```bash
sha256sum -c hf-explorer_0.3.0_all.deb.sha256
sudo apt install ./hf-explorer_0.3.0_all.deb
hf-explorer
```

La release 0.3.0 y est publiée ; l'ancienne release 0.1.0 du dépôt [huggor](https://github.com/nouhailler/huggor/releases) reste disponible mais est obsolète. Le paquet 0.3.0 est construit depuis le code de `main` au moment de la publication, pas depuis le tag `v0.3.0` du dépôt source.

- Python 3.10 ou supérieur requis (par exemple Ubuntu 22.04+, Debian 12+).
- Au premier lancement, une connexion Internet est nécessaire pour installer les dépendances Python dans un environnement isolé : garder le terminal ouvert, puis ouvrir <http://127.0.0.1:7860>. Arrêt avec `Ctrl+C`.
- L'entrée **HF Explorer** du menu des applications ouvre aussi le lanceur dans un terminal.
- Le paquet contient le code de l'application ; aucune donnée personnelle n'y est incluse.

## Emplacement des données

Le lanceur ([`packaging/hf-explorer`](../packaging/hf-explorer)) conserve l'environnement Python et les données dans `${XDG_DATA_HOME:-~/.local/share}/hf-explorer/` (données dans le sous-dossier `data/`, modifiable via `HF_EXPLORER_DATA_DIR`). Les mises à jour et la désinstallation conservent favoris et historique.

Pour utiliser un token : `export HF_TOKEN=…` avant `hf-explorer` (ou `huggor`), ou `hf auth login`.

## Reconstruire le paquet depuis les sources

Nécessite Python et `dpkg-deb` :

```bash
python3 scripts/build_deb.py --version 0.1.0
```

Le résultat est écrit dans `dist/` (ignoré par Git). Le numéro de version doit respecter le format `X.Y.Z`.

## Publier une release (mainteneur)

```bash
scripts/publish_downloads.sh X.Y.Z
```

Le script construit le `.deb`, génère le `.sha256` et crée la release dans `huggor-downloads` après confirmation (nécessite `gh` authentifié). L'installateur attend exactement les noms `hf-explorer_X.Y.Z_all.deb` et `hf-explorer_X.Y.Z_all.deb.sha256`.

## Désinstaller

```bash
sudo apt remove hf-explorer
```

Les données locales sont conservées ; pour les effacer, supprimer `${XDG_DATA_HOME:-~/.local/share}/hf-explorer/`.
