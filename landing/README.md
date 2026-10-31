# Landing page de Huggor (HF Explorer)

Site de présentation statique de [Huggor](https://github.com/nouhailler/huggor), prévu pour [Cloudflare Pages](https://pages.cloudflare.com/). Il est **indépendant de l'application Python/Gradio** : aucun code de l'application n'est utilisé ni modifié, et aucun backend n'est nécessaire.

- HTML / CSS / JavaScript natifs, **aucune dépendance** (Node.js 18+ uniquement pour le script de build).
- Pas de cookie, pas de traceur, pas de police ni de script externe (CSP stricte dans `src/_headers`).
- Les boutons « Installer » de la page d'accueil mènent à `/installer/`, qui donne la commande curl de `huggor-downloads` ; l'accueil n'affiche plus de bouton « Télécharger ».
- Contenu aligné sur les fonctions réellement présentes dans le code : voir le tableau [Correspondance contenu ↔ code](#correspondance-contenu--code).

## Structure

```text
landing/
├── site.config.json   # URLs centralisées (application, GitHub, téléchargements, Hub…) et release de secours
├── build.mjs          # src/ → dist/ : injection des URLs, release lue sur GitHub, robots.txt, sitemap
├── serve.mjs          # serveur statique local (applique aussi src/_headers)
├── src/
│   ├── index.html     # la page (marqueurs {{APP_URL}}, {{DEB_URL}}…)
│   ├── installer/index.html   # page d'installation : commande curl, prérequis, mise à jour, désinstallation
│   ├── styles.css, main.js, estimator.js
│   ├── sw.js, manifest.webmanifest, icons/   # PWA de la vitrine uniquement
│   ├── images/        # captures réelles de HF Explorer (WebP)
│   ├── favicon.svg, og-image.png, _headers
├── tests/             # parité estimator.js ↔ src/resource_calculator.py
└── dist/              # résultat de production (ignoré par Git)
```

## Commandes

```bash
cd landing
npm run build      # produit dist/
npm test           # parité du simulateur avec le calcul Python (72 cas)
npm run serve      # sert dist/ sur http://127.0.0.1:8788/
```

`tests/browser-check.mjs` est un contrôle **manuel** dans un vrai Chromium (menu mobile, simulateur, clavier, images, service worker, console) : ses prérequis sont en tête du fichier.

## Configuration

Toutes les adresses sont dans [`site.config.json`](site.config.json) ; aucune URL n'est écrite en dur dans la page.

| Clé / variable | Rôle |
|---|---|
| `appUrl` | Application HF Explorer en ligne (`https://huggor.onrender.com/`) |
| `githubUrl`, `downloadsUrl`, `hubUrl`, `docsUrl`, `legalUrl`, `issuesUrl`, `contributingUrl` | Liens du site |
| `downloadsRepository` | Dépôt des releases (`nouhailler/huggor-downloads`) |
| `fallbackRelease` | Version utilisée si l'API GitHub est injoignable pendant le build |
| `siteUrl` ou variable d'environnement **`SITE_URL`** | Origine publique du site (ex. `https://huggor.example.com`, sans chemin). **Vide par défaut** : tant qu'elle n'est pas définie, `canonical`, `og:url`, `og:image` absolu et `sitemap.xml` sont omis plutôt que d'inventer un domaine |
| `SKIP_RELEASE_LOOKUP=1` | Ne pas interroger GitHub (utilise `fallbackRelease`) |

À chaque build, `build.mjs` lit la **dernière release** de `huggor-downloads` via l'API GitHub (version, date, taille, nom du `.deb`) ; les liens de téléchargement pointent donc toujours vers des fichiers réellement publiés. Si l'API échoue, il utilise `fallbackRelease` et le signale dans les logs.

Pour mettre à jour la page après une nouvelle release : relancer un déploiement (aucune modification de code).

## Déploiement sur Cloudflare Pages

| Paramètre | Valeur |
|---|---|
| Dépôt à connecter | `nouhailler/huggor` (le site est dans le sous-dossier `landing/`) |
| Branche de production | `main` |
| Répertoire racine (*Root directory*) | `landing` |
| Preset | Aucun (*None*) |
| Commande de build | `npm run build` |
| Répertoire de sortie | `dist` |
| Version de Node | 20 (fichier `landing/.node-version`) |
| Variables d'environnement | `SITE_URL` (recommandée, une fois le domaine connu) ; aucune autre, aucun secret |

Étapes manuelles (dépendent de votre compte Cloudflare, rien n'a été déployé) :

1. Cloudflare → *Workers & Pages* → *Create* → *Pages* → *Connect to Git* → dépôt `huggor`.
2. Renseigner les paramètres ci-dessus. Facultatif : *Build watch paths* = `landing/*` pour ne rebuilder que lorsque la vitrine change.
3. Après le premier déploiement, noter l'adresse `*.pages.dev`, la définir (ou le domaine personnalisé) dans `SITE_URL`, puis redéployer.
4. Domaine personnalisé : *Custom domains* → *Set up a custom domain* ; Cloudflare indique les enregistrements DNS à créer.

Les en-têtes de sécurité (CSP, `nosniff`, `Referrer-Policy`…) et le cache sont dans [`src/_headers`](src/_headers), appliqués par Cloudflare Pages. Aucune règle de redirection n'est nécessaire (page unique).

## PWA de la vitrine

`sw.js` et `manifest.webmanifest` appartiennent **uniquement à ce site** (scope `/`). Ils ne concernent pas l'application HF Explorer, qui est un service distinct : installer la vitrine n'installe pas l'application, et **rien ne permet d'utiliser HF Explorer hors connexion** via ce site. Le service worker ne met en cache que les fichiers statiques du site (réseau d'abord pour la page, cache en secours) ; son nom de cache change à chaque build.

## Correspondance contenu ↔ code

| Affirmation de la page | Vérifiée dans |
|---|---|
| Précisions FP32, FP16, INT8, Q8, Q6, Q4_K_M ; marge d'exécution 10 % ; seuil de confort 85 % ; repères 300 / 40 Go/s | `src/resource_calculator.py` |
| Simulateur identique au calcul Python | `tests/estimator.test.mjs` (72 cas générés par `calculate_resources`) |
| GPU/CPU saisis non utilisés ; pas de détection automatique ; stockage non pris en compte | `src/ui/hardware_tab.py`, `src/resource_calculator.py` |
| Contexte estimé via le cache KV (architecture standard) | `_estimate_context` dans `src/resource_calculator.py` |
| Filtres : mot-clé, domaine/tâche, langue, licence, plage de paramètres, tri, 5–100 résultats | `SearchFilters` dans `src/api_client.py`, `src/ui/search_tab.py` |
| Comparateur 2 à 4 modèles, critères, recommandation, radar | `src/comparison.py`, `src/ui/compare_tab.py` |
| Huggor Score, 9 composantes | `src/huggor_score.py` |
| Page `/installer/` : commande `curl … install.sh \| bash`, options `--release` et `--uninstall`, prérequis, `.deb` manuel ; Linux uniquement | dépôt `huggor-downloads` (release lue via l'API) |
| Aucune licence indiquée | absence de fichier `LICENSE` dans le dépôt |

Non affirmé volontairement : filtre par architecture ou par auteur (non implémentés), intégration avec Ollama ou d'autres moteurs, exécution de modèles ou entraînement, binaires Windows/macOS, garantie de fonctionnement.

## Maintenance

- Remplacer une capture : régénérer les images WebP dans `src/images/` (captures réelles de l'application).
- Changer un texte : éditer `src/index.html`. Garder les promesses alignées avec les fonctions réelles.
- Si les constantes de `src/resource_calculator.py` changent : mettre à jour `src/estimator.js` et régénérer `tests/python-reference.json` (`.venv/bin/python landing/tests/generate_reference.py` depuis la racine du dépôt), puis `npm test`.
