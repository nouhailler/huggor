"""Contenu centralisé de la visite guidée (onboarding) affichée aux nouveaux utilisateurs.

Un seul texte par étape, réutilisé à deux endroits (premier lancement, rejoué depuis l'écran
« À propos ») — même principe que ``src/legal_notice.py`` : ne jamais dupliquer une étape
ailleurs, modifier ce fichier suffit à mettre à jour les deux affichages.
"""

from __future__ import annotations

from dataclasses import dataclass

ONBOARDING_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class OnboardingStep:
    """Une étape de la visite guidée : un titre et un corps court."""

    title: str
    body: str


# Chaque étape ne décrit qu'une fonctionnalité réellement implémentée (voir docs/features.md) —
# jamais une fonctionnalité prévue ou supposée.
ONBOARDING_STEPS: tuple[OnboardingStep, ...] = (
    OnboardingStep(
        "👋 Bienvenue sur HF Explorer",
        "Huggor vous aide à rechercher, examiner, comparer et tester les modèles du "
        "Hugging Face Hub — avec des verdicts de compatibilité matérielle honnêtes, jamais "
        "présentés comme une boîte noire.",
    ),
    OnboardingStep(
        "🔍 Recherche & 🎯 Mon usage",
        "L'onglet **Recherche** navigue par domaine puis tâche précise, sans jargon Hub. "
        "L'onglet **Mon usage** part plutôt d'un objectif (Chatbot, Coding, RAG…) croisé "
        "avec votre RAM/VRAM pour ne remonter que des modèles jouables sur votre machine.",
    ),
    OnboardingStep(
        "📄 Fiche technique & Huggor Score",
        "Chaque fiche détaillée inclut un **Model Advisor** (RAM/VRAM nécessaire) et un "
        "**Huggor Score** sur 100, toujours accompagné du détail de ses neuf composantes — "
        "jamais un chiffre seul.",
    ),
    OnboardingStep(
        "🆚 Comparateur & 💻 Hardware",
        "Comparez 2 à 4 modèles avec une recommandation motivée dans l'onglet "
        "**Comparateur**, ou utilisez le calculateur **Hardware** pour savoir, "
        "indépendamment d'un modèle précis, quelles précisions tiennent sur votre machine.",
    ),
    OnboardingStep(
        "⭐ Favoris, 📈 Analytics & mode hors connexion",
        "Gardez une trace personnelle de vos modèles testés dans **Favoris**, suivez les "
        "tendances du Hub dans **Analytics**, et continuez à consulter vos recherches et "
        "fiches déjà vues même si le Hub devient injoignable. Sur petit écran, le menu ☰ "
        "regroupe tous les onglets par catégorie.",
    ),
)
