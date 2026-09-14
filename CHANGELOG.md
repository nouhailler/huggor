# Historique des versions

## 0.1.0 — 2026-09-14

- Recherche et exploration des modèles Hugging Face.
- Fiches techniques avec infobulles en français pour les champs d’identité, d’architecture et de compatibilité.
- Comparaison de modèles et graphiques Analytics avec observations locales.
- Paquet Debian avec lanceur `hf-explorer` et entrée dans le menu des applications.
- Données et environnement Python isolés par utilisateur pour les installations système.

### Installation du paquet

```bash
sudo apt install ./hf-explorer_0.1.0_all.deb
hf-explorer
```

Nécessite Python 3.10+ (Ubuntu 22.04+ ou Debian 12+, par exemple). Le premier lancement télécharge les dépendances Python et nécessite Internet. Ouvrez ensuite http://127.0.0.1:7860 dans votre navigateur.

Le paquet contient le code de l’application ; les dépendances Python sont installées séparément dans le compte utilisateur. Le fichier SHA256SUMS permet de vérifier le téléchargement avec `sha256sum -c SHA256SUMS`.

L’onglet de test d’inférence et la gestion complète des favoris sont encore des espaces réservés. L’ajout aux favoris depuis une fiche est disponible.
