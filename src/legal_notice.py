"""Contenu centralisé de l'avertissement légal et de la limitation de responsabilité.

Un seul texte, réutilisé à deux endroits (bandeau de premier lancement dans ``app.py``,
page complète accessible en permanence) : voir la commande ``/mentions-legales``, piège
« un seul contenu, un seul rendu ». Ne jamais dupliquer un de ces paragraphes ailleurs :
modifier ce fichier suffit à mettre à jour les deux affichages.
"""

from __future__ import annotations

from dataclasses import dataclass

LEGAL_NOTICE_VERSION = "1.0"
LEGAL_NOTICE_LAST_UPDATED = "2026-09-18"

TITLE = "⚠️ Information importante"

SHORT_WARNING = (
    "Cette application est fournie à titre informatif et pratique. Malgré les précautions "
    "prises lors de son développement, elle peut contenir des erreurs, des imprécisions ou "
    "présenter des limitations techniques.\n\n"
    "L'utilisation de cette application se fait sous votre responsabilité. Les informations, "
    "résultats, données ou recommandations fournis par l'application ne doivent pas être "
    "considérés comme infaillibles.\n\n"
    "Pour toute information importante ou décision susceptible d'avoir des conséquences, "
    "vérifiez les données auprès de sources fiables et officielles ou auprès d'un "
    "professionnel compétent.\n\n"
    "En utilisant cette application, vous reconnaissez avoir pris connaissance de cet "
    "avertissement."
)


@dataclass(frozen=True, slots=True)
class LegalSection:
    """Une section nommée de la page de mentions légales, un ou plusieurs paragraphes."""

    title: str
    paragraphs: tuple[str, ...]


# Paragraphes du texte de limitation de responsabilité, verbatim, organisés sous les
# 8 sections minimales demandées. Aucun mot n'est modifié par rapport au texte fourni ;
# seule l'organisation en sections change.
LIABILITY_SECTIONS: tuple[LegalSection, ...] = (
    LegalSection("Avertissement", (SHORT_WARNING,)),
    LegalSection(
        "Limitation de responsabilité",
        (
            "L'utilisateur reconnaît utiliser l'application sous sa propre responsabilité et "
            "demeure seul responsable de l'utilisation qu'il fait des informations et "
            "fonctionnalités proposées.",
            "Dans les limites autorisées par la réglementation applicable, l'éditeur ne "
            "saurait être tenu responsable des dommages, pertes, préjudices ou conséquences "
            "résultant directement ou indirectement de l'utilisation, de l'impossibilité "
            "d'utiliser ou de l'interprétation des informations ou fonctionnalités proposées "
            "par l'application.",
            "Cette limitation concerne notamment, lorsque cela est applicable, les erreurs ou "
            "omissions dans les informations, les dysfonctionnements techniques, les "
            "interruptions de service, les pertes de données, les problèmes de connexion, les "
            "incompatibilités matérielles ou logicielles et les décisions prises par "
            "l'utilisateur sur la base des informations fournies.",
        ),
    ),
    LegalSection(
        "Utilisation de l'application",
        (
            "Cette application est proposée à titre informatif, documentaire, éducatif et/ou "
            "pratique selon sa finalité. Elle est destinée à fournir à l'utilisateur des "
            "informations, données, outils ou fonctionnalités destinés à faciliter son "
            "utilisation.",
        ),
    ),
    LegalSection(
        "Exactitude des informations",
        (
            "L'éditeur s'efforce de fournir des informations aussi fiables, pertinentes et "
            "actualisées que possible. Toutefois, aucune garantie ne peut être donnée quant à "
            "l'exactitude, l'exhaustivité, l'actualité ou la pertinence des informations "
            "présentées.",
            "L'application ne doit pas être considérée comme une source unique ou définitive "
            "d'information lorsqu'une décision importante, professionnelle, financière, "
            "médicale, juridique, scientifique, géographique ou liée à la sécurité est "
            "concernée.",
            "Lorsque cela est nécessaire, l'utilisateur doit vérifier les informations auprès "
            "de sources officielles, de documents de référence ou d'un professionnel qualifié.",
        ),
    ),
    LegalSection(
        "Dysfonctionnements et disponibilité",
        (
            "Malgré les efforts déployés pour assurer le bon fonctionnement de l'application, "
            "l'éditeur ne garantit pas que celle-ci sera disponible en permanence, exempte "
            "d'erreurs ou compatible avec tous les appareils, systèmes d'exploitation, "
            "navigateurs, réseaux ou configurations.",
            "Des interruptions, ralentissements, pertes de connexion, erreurs techniques ou "
            "indisponibilités temporaires peuvent notamment survenir.",
        ),
    ),
    LegalSection(
        "Données et résultats",
        (
            "Les résultats, calculs, estimations, localisations, statistiques, "
            "recommandations ou autres données produits par l'application sont fournis à "
            "titre indicatif, sauf indication contraire explicite.",
            "L'utilisateur doit apprécier leur pertinence en fonction de son propre contexte "
            "et procéder aux vérifications nécessaires avant toute utilisation susceptible "
            "d'entraîner des conséquences importantes.",
        ),
    ),
    LegalSection(
        "Sources externes",
        (
            "Certaines informations peuvent provenir de sources externes ou être générées, "
            "calculées ou interprétées automatiquement. Des erreurs, omissions, imprécisions "
            "ou incohérences peuvent donc subsister.",
            "Lorsque l'application utilise ou référence des données provenant de sources "
            "externes, celles-ci peuvent évoluer, devenir indisponibles ou être modifiées "
            "indépendamment de l'éditeur. L'éditeur ne garantit donc pas la disponibilité "
            "permanente ni l'exactitude des contenus provenant de ces sources.",
        ),
    ),
    LegalSection(
        "Évolution de l'application",
        (
            "Les fonctionnalités, contenus, données et services proposés par l'application "
            "peuvent être modifiés, mis à jour, suspendus ou supprimés à tout moment afin "
            "d'assurer son évolution et sa maintenance.",
        ),
    ),
)

CLOSING_STATEMENT = (
    "L'utilisation de l'application implique que l'utilisateur a pris connaissance du présent "
    "avertissement et accepte les conditions d'utilisation applicables à l'application."
)

# Absence volontaire, pas un oubli : Huggor n'utilise ni GPS, ni géolocalisation, ni calcul
# d'itinéraire, ni donnée cartographique (vérifié dans le code par recherche de
# "geolocation"/"navigator.geolocation"/"gps"/"latitude"/"longitude" — aucune occurrence hors
# faux positifs comme "GGUF"). La section "Précision de la localisation" ne s'applique donc pas.
GPS_WARNING: str | None = None

EDITOR = {
    "name": "Swinux",
    "address": "Canton de Vaud, Suisse",
    "email": "contact@swinux.ch",
    "host": "Render (render.com)",
}


def render_full_notice_markdown() -> str:
    """Construire le Markdown complet des mentions légales pour la page permanente."""
    lines: list[str] = [f"# {TITLE}", ""]
    for section in LIABILITY_SECTIONS:
        lines.append(f"## {section.title}")
        lines.append("")
        for paragraph in section.paragraphs:
            lines.append(paragraph)
            lines.append("")
    if GPS_WARNING:
        lines.append("## Précision de la localisation")
        lines.append("")
        lines.append(GPS_WARNING)
        lines.append("")
    lines.append("## Éditeur")
    lines.append("")
    lines.append(f"- **Éditeur** : {EDITOR['name']}")
    lines.append(f"- **Adresse** : {EDITOR['address']}")
    lines.append(f"- **Contact** : {EDITOR['email']}")
    lines.append(f"- **Hébergement** : {EDITOR['host']}")
    lines.append("")
    lines.append(f"_Version {LEGAL_NOTICE_VERSION} — dernière mise à jour : {LEGAL_NOTICE_LAST_UPDATED}._")
    lines.append("")
    lines.append(CLOSING_STATEMENT)
    return "\n".join(lines)
