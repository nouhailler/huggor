# Politique de sécurité

## Signaler une vulnérabilité

Ne publiez pas de faille dans une issue publique. Écrivez à **contact@swinux.ch** (l'adresse de contact de l'éditeur indiquée dans les [mentions légales](docs/legal.md)) en décrivant le problème et les étapes pour le reproduire. Il n'existe pas de délai de réponse garanti : le projet est maintenu par une seule personne.

Pour un problème sans enjeu de sécurité, utilisez les [issues](https://github.com/nouhailler/huggor/issues).

## Version concernée

Seule la dernière version publiée (voir [Releases](https://github.com/nouhailler/huggor/releases)) est suivie.

## Rappels sur les secrets

- Le token Hugging Face (`HF_TOKEN`) se configure via `.env` (ignoré par Git), `hf auth login` ou le secret de la plateforme de déploiement. Ne le publiez jamais dans une issue, une capture d'écran ou un commit.
- Si un token a été exposé, révoquez-le dans les [réglages de votre compte Hugging Face](https://huggingface.co/settings/tokens) puis créez-en un nouveau.

Données stockées et échanges réseau : voir [Données](docs/data.md) et [Permissions](docs/permissions.md).
