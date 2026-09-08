"""Point d'entrée de HF Explorer.

L'interface Gradio sera ajoutée à l'étape 2 du plan de développement.
"""

from src.api_client import HuggingFaceClient


def main() -> None:
    """Initialiser le client et confirmer que le socle est opérationnel."""
    client = HuggingFaceClient()
    auth_label = "configuré" if client.has_token else "anonyme"
    print(f"HF Explorer — socle API prêt (accès {auth_label}).")
    print("Validez l'étape 1 pour démarrer l'interface Gradio.")


if __name__ == "__main__":
    main()

