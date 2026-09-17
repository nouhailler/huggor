"""Traduire un objectif utilisateur (« je veux faire du chat ») en recherches Hub concrètes.

Chaque usage recouvre une ou plusieurs tâches réellement supportées par le Hub. Certains
rapprochements restent approximatifs faute de tâche dédiée (RAG notamment, qui n'est pas un
pipeline_tag du Hub) : ce sont des heuristiques de découverte, pas une garantie d'adéquation
à l'usage visé.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UseCaseTask:
    """Une recherche Hub concrète (tâche + mot-clé optionnel) associée à un usage."""

    pipeline_tag: str
    keyword: str = ""


@dataclass(frozen=True, slots=True)
class UseCase:
    """Un objectif utilisateur, traduit en une ou plusieurs recherches Hub réelles."""

    key: str
    label: str
    description: str
    tasks: tuple[UseCaseTask, ...]


USE_CASES: tuple[UseCase, ...] = (
    UseCase(
        "chatbot", "💬 Chatbot", "Dialoguer avec un assistant conversationnel.",
        (UseCaseTask("text-generation", "chat"),),
    ),
    UseCase(
        "coding", "💻 Coding", "Générer, compléter ou expliquer du code.",
        (UseCaseTask("text-generation", "code"),),
    ),
    UseCase(
        "rag", "📚 RAG",
        "Recherche documentaire augmentée : rapprochement approximatif, le Hub n'a pas de "
        "tâche « RAG » dédiée ; ce sont des modèles d'embeddings taggés RAG.",
        (UseCaseTask("feature-extraction", "rag"), UseCaseTask("sentence-similarity", "rag")),
    ),
    UseCase(
        "embeddings", "🔤 Embeddings", "Produire des vecteurs de similarité pour du texte.",
        (UseCaseTask("sentence-similarity"), UseCaseTask("feature-extraction")),
    ),
    UseCase(
        "translation", "🌍 Traduction", "Traduire un texte d'une langue à une autre.",
        (UseCaseTask("translation"),),
    ),
    UseCase(
        "vision", "👁️ Vision", "Analyser ou classer des images.",
        (UseCaseTask("image-classification"), UseCaseTask("object-detection")),
    ),
    UseCase(
        "speech", "🗣️ Speech", "Transcrire ou synthétiser de la voix.",
        (UseCaseTask("automatic-speech-recognition"), UseCaseTask("text-to-speech")),
    ),
    UseCase(
        "image_generation", "🖼️ Génération d'images", "Créer des images à partir d'un texte.",
        (UseCaseTask("text-to-image"),),
    ),
)


def find_use_case(key: str) -> UseCase | None:
    """Retrouver un usage par sa clé stable."""
    return next((item for item in USE_CASES if item.key == key), None)
