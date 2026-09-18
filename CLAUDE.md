# Contexte projet — Huggor (HF Explorer)

Application Python/Gradio pour rechercher, examiner, comparer et tester les modèles du Hugging Face Hub. Voir [README.md](README.md) pour l'installation, le lancement et le déploiement (Hugging Face Spaces, Render).

## Documentation

> Documentation : suivre [DOCUMENTATION_SPEC.md](DOCUMENTATION_SPEC.md). Une tâche n'est « done » que si la doc correspondante (dans [`/docs`](docs/index.md)) est à jour — voir §39 de la spec pour la check-list complète.

La documentation utilisateur/développeur vit dans [`/docs`](docs/index.md), en Markdown simple (pas de générateur de site : le projet n'en a pas besoin, voir §4 de la spec). Elle est versionnée avec le code.

Avant de considérer une tâche fonctionnelle comme terminée :
1. Le code est-il terminé et testé (`python -m unittest discover -s tests -v`) ?
2. La documentation dans `/docs` reflète-t-elle le nouveau comportement (fonctionnalité, paramètre, permission, donnée, erreur, mode hors connexion) ?
3. Le changelog (`docs/versions.md`) doit-il être mis à jour ?
4. La FAQ ou le dépannage (`docs/faq.md`, `docs/troubleshooting.md`) doivent-ils l'être aussi ?

Ne jamais inventer un comportement non vérifiable dans le code, la config ou les tests — écrire `À vérifier` et le signaler.

## Tests

```bash
python -m unittest discover -s tests -v
```

Isolés du réseau, bibliothèque standard uniquement (`unittest`).

## Mentions légales / avertissement de premier lancement

Système ajouté via la commande `/mentions-legales`. Contenu centralisé dans [`src/legal_notice.py`](src/legal_notice.py), affiché à deux endroits dans [`app.py`](app.py) : un bandeau au premier lancement et un lien permanent « ⚖️ Mentions légales » en pied de page. Détails complets : [`docs/legal.md`](docs/legal.md).

- **Stockage** : `localStorage` du navigateur, clé `legal_notice_acknowledged` (+ `legal_notice_acknowledged_version`). 100 % côté client, rien envoyé au serveur ni journalisé.
- **Modifier le texte** : éditer [`src/legal_notice.py`](src/legal_notice.py) uniquement — jamais dupliquer un paragraphe ailleurs, il est rendu aux deux endroits depuis ce seul fichier.
- **Changer la version** : incrémenter `LEGAL_NOTICE_VERSION` dans `src/legal_notice.py` et la chaîne JS correspondante dans `_LEGAL_ACCEPT_THEN_MAYBE_ONBOARDING_JS` (`app.py`). Ne pas déclencher automatiquement une réapparition de l'avertissement pour un changement mineur — c'est un choix délibéré, pas fait par défaut ; si un changement le justifie un jour, comparer `legal_notice_acknowledged_version` au stockage côté JS avant de considérer l'avertissement comme acquis.
- **Tester le premier lancement** : ouvrir l'app dans une fenêtre de navigation privée, ou effacer `localStorage` pour `localhost:7860` (console navigateur : `localStorage.removeItem('legal_notice_acknowledged')` puis recharger).
- **Tests Python** : [`tests/test_legal_notice.py`](tests/test_legal_notice.py) vérifie la structure du contenu (8 sections, non vides, pas de section GPS puisque Huggor n'en a pas besoin). Le parcours interactif (bandeau → détails → acceptation → persistance) a été vérifié manuellement au navigateur, pas par un test automatisé : le projet n'a pas d'outillage e2e JS et il n'était pas justifié d'en ajouter un pour cette seule fonctionnalité.

## Visite guidée (onboarding)

Contenu centralisé dans [`src/onboarding.py`](src/onboarding.py) (5 étapes), affichée dans `app.py` juste après l'acceptation de l'avertissement légal au premier lancement, et rejouable depuis l'écran « ⚙️ Paramètres » (bouton « 🧭 Revoir la visite guidée », géré par `settings_onboarding_button`/`_SETTINGS_TO_ONBOARDING_JS`). Réutilise le même mécanisme d'overlay (`.hf-legal-overlay`/`.hf-legal-card`, généré via `_overlay_switch_js`) que les mentions légales et l'écran « À propos » — voir le commentaire au-dessus de `.hf-legal-overlay` dans `app.py`. Détails complets : [`docs/guide.md`](docs/guide.md#visite-guidée-onboarding).

- **Stockage** : `localStorage` du navigateur, clé `onboarding_completed` (+ `onboarding_completed_version`), indépendante de `legal_notice_acknowledged`. 100 % côté client.
- **Ordre d'affichage** : mentions légales toujours en premier si non acceptées ; la visite guidée ne s'affiche qu'ensuite (voir `_STARTUP_CHECK_JS` et `_LEGAL_ACCEPT_THEN_MAYBE_ONBOARDING_JS` dans `app.py`), jamais les deux overlays en même temps.
- **Ajouter/modifier une étape** : éditer `ONBOARDING_STEPS` dans [`src/onboarding.py`](src/onboarding.py) uniquement — la navigation (`onboarding_go_next`/`onboarding_go_prev` dans `app.py`) s'adapte automatiquement au nombre d'étapes.
- **Tester le premier lancement** : effacer `localStorage` (`legal_notice_acknowledged` ET `onboarding_completed`) ou navigation privée.
- **Tests Python** : [`tests/test_onboarding.py`](tests/test_onboarding.py) (contenu) et `OnboardingNavigationTests` dans [`tests/test_app.py`](tests/test_app.py) (bornes de navigation). Parcours interactif vérifié manuellement au navigateur, même raison que pour les mentions légales.

## Écran « À propos » / métadonnées de build

Contenu assemblé dans `_build_about_markdown()` (`app.py`) à partir de [`src/app_info.py`](src/app_info.py). Point piégeux confirmé empiriquement le 2026-09-18 : **Render déploie depuis un clone Git superficiel**, sans tags ni remote `origin` — `git describe`/`git remote` y échouent silencieusement (repli sur un hash nu, ou `None`). `src/app_info.py` compense en préférant les variables `RENDER_GIT_COMMIT`/`RENDER_GIT_BRANCH`/`RENDER_GIT_REPO_SLUG` (injectées par Render lui-même, donc fiables même sur ce clone superficiel) avant de retomber sur Git local puis sur `—`. Toujours garder cet ordre de repli si ce fichier est modifié : Render en priorité, jamais l'inverse, sinon la régression revient silencieusement en production sans échouer en local.

- **`PYTHONUNBUFFERED=1`** est déclaré dans `render.yaml` : sans lui, la sortie standard de Python (donc tout `print()` de débogage) n'apparaît dans les logs Render qu'après un délai imprévisible, voire jamais tant que le process tourne — c'est ce qui a caché ce problème un moment.
- **Tests Python** : [`tests/test_app_info.py`](tests/test_app_info.py), notamment `RenderEnvironmentPriorityTests` qui verrouille cet ordre de priorité avec des variables d'environnement simulées.
- **Ne jamais logger la valeur d'un secret pour déboguer** un problème d'environnement sur Render : `GET /v1/services/{id}/env-vars` de l'API Render renvoie les valeurs **en clair**, contrairement à l'API Hugging Face qui masque ses secrets — vérifié en le découvrant après coup avec `HF_TOKEN`. Se limiter aux noms de clés, ou aux variables déjà documentées comme publiques par Render (préfixe `RENDER_`, hors tout ce qui ressemble à un token/secret).

## Git

Dépôt GitHub : `nouhailler/huggor`. Ne jamais commit de secret (`.env`, tokens). `data/cache/` et `data/analytics/` sont ignorés par git ; `data/favorites.json` est versionné mais doit rester vide (`[]`) dans les commits — c'est un fichier de données utilisateur, pas un exemple.
