← [Documentation](index.md)

# Paquet Debian / Ubuntu

## Installer

Télécharger le `.deb` depuis les [releases GitHub](https://github.com/nouhailler/huggor/releases), puis :

```bash
sudo apt install ./hf-explorer_0.1.0_all.deb
hf-explorer
```

> Le seul `.deb` publié à ce jour est celui de la release v0.1.0 (avec `SHA256SUMS`). La release v0.3.0 n'a aucun fichier attaché et v0.2.0 n'existe que comme tag Git. Pour les dernières fonctionnalités, reconstruire le paquet (voir plus bas) ou lancer depuis les sources.

- Python 3.10 ou supérieur requis (par exemple Ubuntu 22.04+, Debian 12+).
- Au premier lancement, une connexion Internet est nécessaire pour installer les dépendances Python dans un environnement isolé : garder le terminal ouvert, puis ouvrir <http://127.0.0.1:7860>. Arrêt avec `Ctrl+C`.
- L'entrée **HF Explorer** du menu des applications ouvre aussi le lanceur dans un terminal.
- Le paquet contient le code de l'application ; aucune donnée personnelle n'y est incluse.

## Emplacement des données

Le lanceur ([`packaging/hf-explorer`](../packaging/hf-explorer)) conserve l'environnement Python et les données dans `${XDG_DATA_HOME:-~/.local/share}/hf-explorer/` (données dans le sous-dossier `data/`, modifiable via `HF_EXPLORER_DATA_DIR`). Les mises à jour et la désinstallation conservent favoris et historique.

Pour utiliser un token : `export HF_TOKEN=…` avant `hf-explorer`, ou `hf auth login`.

## Reconstruire le paquet depuis les sources

Nécessite Python et `dpkg-deb` :

```bash
python3 scripts/build_deb.py --version 0.1.0
```

Le résultat est écrit dans `dist/` (ignoré par Git) ; la construction a été vérifiée avec `--version 0.3.0`. Le numéro de version doit respecter le format `X.Y.Z`.

## Désinstaller

```bash
sudo apt remove hf-explorer
```

Les données locales sont conservées ; pour les effacer, supprimer `${XDG_DATA_HOME:-~/.local/share}/hf-explorer/`.
