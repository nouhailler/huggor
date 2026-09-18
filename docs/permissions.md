← [Documentation](index.md)

# Permissions

Huggor n'utilise **aucune permission native** de navigateur ou d'appareil : pas de localisation, caméra, microphone, notifications, Bluetooth, contacts ou capteurs. La seule chose qui s'en approche est le **token d'authentification Hugging Face**, qui n'est pas une permission au sens navigateur/OS mais une clé d'accès applicative.

## Token Hugging Face (`HF_TOKEN`)

- **Pourquoi** : accéder aux ressources privées ou protégées (« gated ») du Hub. Les modèles publics sont accessibles sans token.
- **Quand il est utilisé** : à chaque appel au Hub (recherche, chargement de fiche, Model Card), résolu automatiquement par la bibliothèque `huggingface_hub` (variable d'environnement `HF_TOKEN`, fichier `.env`, ou session `hf auth login`).
- **Obligatoire ?** Non pour l'usage public. Nécessaire uniquement pour les dépôts privés ou nécessitant une acceptation de conditions (« gated »).
- **Si absent** : le bandeau d'en-tête affiche « Accès public » au lieu de « 🟢 Token HF configuré » ; les dépôts protégés renvoient une erreur d'authentification explicite (voir [Référence → Erreurs](reference.md#codes-et-messages-derreur)) plutôt qu'un échec silencieux.
- **Comment le configurer** :
  - En local : `.env` (`HF_TOKEN=...`) ou `hf auth login`.
  - Sur un déploiement (Hugging Face Spaces, Render) : variable d'environnement/secret côté plateforme, jamais dans le code ni dans le dépôt — voir le [README](../README.md#déploiement-sur-hugging-face-spaces).
- **Comment le retirer** : supprimer la ligne `HF_TOKEN` de `.env`, exécuter `hf auth logout`, ou retirer le secret côté plateforme de déploiement.

Le token n'est **jamais affiché** dans l'interface, jamais journalisé, et jamais inclus dans une capture d'écran de cette documentation (voir [Données sensibles](../DOCUMENTATION_SPEC.md) §50 de la spec).
