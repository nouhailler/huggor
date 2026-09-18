"""Point d'entrée et composition de l'interface Gradio de HF Explorer."""

from __future__ import annotations

import os
from functools import partial
from pathlib import Path

import gradio as gr

from src import app_info
from src.api_client import HuggingFaceClient
from src.ui.analytics_tab import build_analytics_tab
from src.ui.compare_tab import build_compare_tab
from src.ui.details_tab import build_details_tab, create_repo_id_input
from src.ui.favorites_tab import build_favorites_tab
from src.ui.hardware_tab import build_hardware_tab
from src.ui.search_tab import build_search_tab
from src.ui.usage_tab import build_usage_tab
from src.ui.test_tab import build_test_tab
from src.legal_notice import EDITOR as LEGAL_EDITOR, SHORT_WARNING, TITLE as LEGAL_TITLE, render_full_notice_markdown
from src.onboarding import ONBOARDING_STEPS, ONBOARDING_VERSION

APP_CSS = """
.gradio-container {
    max-width: 1480px !important;
}
.hf-header {
    align-items: center;
    background: linear-gradient(120deg, #eef2ff 0%, #f0f9ff 100%);
    border: 1px solid #c7d2fe;
    border-radius: 18px;
    display: flex;
    gap: 1.5rem;
    justify-content: space-between;
    margin-bottom: 0.75rem;
    padding: 1.15rem 1.35rem;
}
.hf-title {
    color: #1e1b4b;
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1.2;
}
.hf-subtitle {
    color: #475569;
    margin-top: 0.35rem;
}
.hf-status {
    align-items: center;
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    color: #334155;
    display: inline-flex;
    flex-shrink: 0;
    font-size: 0.9rem;
    font-weight: 600;
    gap: 0.45rem;
    padding: 0.5rem 0.8rem;
}
.hf-status-dot {
    background: #10b981;
    border-radius: 50%;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.16);
    height: 0.55rem;
    width: 0.55rem;
}
.hf-status span {
    color: #334155 !important;
}
.hf-status.public .hf-status-dot {
    background: #64748b;
    box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.16);
}
.hf-placeholder {
    border: 1px dashed #cbd5e1;
    border-radius: 14px;
    color: #64748b;
    margin-top: 0.5rem;
    padding: 1rem 1.1rem;
}
.hf-search-status {
    color: #475569;
    min-height: 1.5rem;
}
.hf-result-card {
    background: var(--block-background-fill);
    border: 1px solid #dbeafe !important;
    border-radius: 14px !important;
    box-shadow: 0 5px 18px rgba(30, 64, 175, 0.05);
    margin: 0.7rem 0;
    padding: 0.3rem 0.35rem;
}
.hf-result-card:hover {
    border-color: #a5b4fc !important;
    box-shadow: 0 8px 24px rgba(30, 64, 175, 0.09);
}
.hf-result-content {
    min-width: 0;
}
.hf-details-status,
.hf-favorite-status {
    min-height: 1.5rem;
}
.hf-cache-status {
    align-self: center;
    color: #64748b;
    font-size: 0.88rem;
}
.hf-tech-card {
    background: var(--block-background-fill);
    border: 1px solid var(--border-color-primary);
    border-radius: 14px;
    margin: 0.75rem 0;
    min-width: 0;
    padding: 0.8rem 1rem;
}
.hf-tech-card table {
    font-size: 0.92rem;
}
.hf-field-label {
    font-weight: 600;
}
.hf-field-help {
    background: transparent;
    border: 0;
    font: inherit;
    position: relative;
    display: inline-block;
    color: var(--link-text-color);
    cursor: help;
    font-weight: 400;
    padding: 0.15rem 0.25rem;
}
.hf-field-help:focus {
    outline: 2px solid var(--link-text-color);
    outline-offset: 2px;
    border-radius: 4px;
}
.hf-field-tooltip {
    display: none;
    position: absolute;
    left: 0;
    top: 100%;
    z-index: 30;
    width: min(280px, 60vw);
    box-sizing: border-box;
    padding: 0.65rem 0.8rem;
    border: 1px solid var(--border-color-primary);
    border-radius: 8px;
    background: var(--block-background-fill);
    color: var(--body-text-color);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
    font-size: 0.85rem;
    font-weight: 400;
    line-height: 1.5;
    white-space: normal;
    text-align: left;
}
.hf-field-help:hover > .hf-field-tooltip,
.hf-field-help:focus > .hf-field-tooltip {
    display: block;
}
.hf-hardware-card {
    border-left: 5px solid #10b981;
}
.hf-huggor-score-card {
    border-left: 5px solid #f59e0b;
}
.hf-huggor-score-card h2 {
    margin-top: 0.25rem;
}
.hf-hardware-disclaimer {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 12px;
    margin: 0.5rem 0 1rem;
    padding: 0.7rem 1rem;
}
.hf-download-advice {
    background: var(--block-background-fill);
    border: 1px solid #a5b4fc;
    border-left: 5px solid #4f46e5;
    border-radius: 14px;
    margin: 0.75rem 0 1rem;
    padding: 0.8rem 1.1rem;
}
.hf-download-advice pre {
    margin-bottom: 0;
}
.hf-model-card {
    max-height: 780px;
    overflow: auto;
    padding: 0.5rem;
}
.hf-file-tree {
    max-height: 680px;
    overflow: auto;
}
.hf-header-right {
    align-items: center;
    display: flex;
    flex-shrink: 0;
    gap: 0.6rem;
}
.hf-hamburger {
    display: none !important;
    font-size: 1.25rem !important;
    min-width: 2.6rem !important;
}
.hf-nav-menu {
    background: var(--block-background-fill);
    border: 1px solid var(--border-color-primary);
    border-radius: 14px;
    margin-bottom: 0.75rem;
    padding: 0.9rem 1rem 0.4rem;
}
.hf-nav-category {
    color: #475569;
    margin-top: 0.6rem;
}
.hf-nav-category:first-child {
    margin-top: 0;
}
.hf-nav-row {
    flex-wrap: wrap;
    gap: 0.5rem;
}
/* Classes de panneau génériques : partagées par les overlays mentions légales, à propos et
   visite guidée, malgré leur préfixe "hf-legal-" d'origine — pas trois jeux de styles dupliqués. */
.hf-legal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 9999;
    align-items: center;
    justify-content: center;
    background: rgba(15, 23, 42, 0.55);
    padding: 1rem;
    box-sizing: border-box;
}
.hf-legal-card {
    background: var(--block-background-fill);
    border-radius: 18px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
    display: flex;
    flex-direction: column;
    max-height: min(85vh, 720px);
    max-width: 560px;
    width: 100%;
    overflow: hidden;
}
.hf-legal-scroll {
    overflow-y: auto;
    padding: 1.25rem 1.4rem 0.5rem;
}
.hf-legal-actions {
    border-top: 1px solid var(--border-color-primary);
    flex-shrink: 0;
    gap: 0.6rem;
    padding: 0.9rem 1.4rem;
}
.hf-footer {
    align-items: center;
    color: var(--body-text-color-subdued);
    flex-wrap: wrap;
    font-size: 0.9rem;
    gap: 0.4rem 1rem;
}
.hf-footer-legal-button {
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    color: var(--link-text-color) !important;
    display: inline;
    font: inherit !important;
    height: auto !important;
    min-width: 0 !important;
    padding: 0 !important;
    text-decoration: underline;
    width: auto !important;
}
.hf-about-logo {
    margin: 0 auto 0.5rem;
    max-width: 96px;
}
.hf-about-logo img {
    border-radius: 12px;
}
.hf-nav-footer {
    border-top: 1px solid var(--border-color-primary);
    margin-top: 0.6rem;
    padding-top: 0.6rem;
}
.hf-onboarding-dots {
    color: var(--body-text-color-subdued);
    letter-spacing: 0.2rem;
    text-align: center;
}
@media (max-width: 640px) {
    .hf-header {
        align-items: flex-start;
        flex-direction: column;
    }
}
@media (max-width: 768px) {
    .hf-hamburger {
        display: inline-flex !important;
    }
    .hf-main-tabs [role="tablist"] {
        display: none;
    }
}
"""


def create_theme() -> gr.themes.Soft:
    """Créer la palette visuelle cohérente de l'application."""
    return gr.themes.Soft(
        primary_hue=gr.themes.colors.indigo,
        secondary_hue=gr.themes.colors.sky,
        neutral_hue=gr.themes.colors.slate,
        radius_size=gr.themes.sizes.radius_lg,
    )


NAV_CATEGORIES: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "🔍 Explorer",
        (
            ("search", "🔍 Recherche"),
            ("usage", "🎯 Mon usage"),
        ),
    ),
    (
        "🔬 Analyser un modèle",
        (
            ("details", "📄 Détails"),
            ("hardware", "💻 Hardware"),
            ("compare", "🆚 Comparateur"),
            ("test", "🧪 Test"),
        ),
    ),
    (
        "📊 Suivre et organiser",
        (
            ("analytics", "📈 Analytics"),
            ("favorites", "⭐ Favoris"),
        ),
    ),
)


def toggle_nav_menu(is_open: bool) -> tuple[bool, gr.Column]:
    """Ouvrir ou fermer le menu hamburger selon son état actuel."""
    new_state = not is_open
    return new_state, gr.Column(visible=new_state)


def select_tab_from_menu(tab_id: str) -> tuple[gr.Tabs, bool, gr.Column]:
    """Naviguer vers l'onglet choisi dans le menu hamburger, puis le refermer."""
    return gr.Tabs(selected=tab_id), False, gr.Column(visible=False)


# JS pur, exécuté côté client sans aller-retour serveur : l'acceptation des mentions légales
# est strictement locale (localStorage), jamais transmise ni journalisée côté application.

_LEGAL_OPEN_JS = """
() => {
    const overlay = document.getElementById('hf-legal-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}
"""


def show_legal_details() -> tuple[gr.Column, gr.Column, gr.Button, gr.Button]:
    """Basculer vers la page complète des mentions légales, dans le même panneau.

    Rester dans le même panneau (plutôt qu'ouvrir un second overlay) évite tout conflit de
    z-index avec le bandeau court : voir la commande /mentions-legales, piège des overlays.
    """
    return gr.Column(visible=False), gr.Column(visible=True), gr.Button(visible=False), gr.Button(visible=True)


def hide_legal_details() -> tuple[gr.Column, gr.Column, gr.Button, gr.Button]:
    """Revenir à l'avertissement court, sans quitter le panneau."""
    return gr.Column(visible=True), gr.Column(visible=False), gr.Button(visible=True), gr.Button(visible=False)


def _overlay_switch_js(hide_id: str | None = None, show_id: str | None = None) -> str:
    """Générer le JS masquant un overlay et/ou en affichant un autre, par identifiant DOM.

    Évite de réécrire à la main la même paire « hide/show » pour chaque nouveau panneau
    (mentions légales, à propos, visite guidée, paramètres…) — voir /mentions-legales,
    /apropos et la commande ayant ajouté la visite guidée pour l'origine de ce motif.
    """
    lines = ["() => {"]
    if hide_id:
        lines.append(f"    const hidden_ = document.getElementById('{hide_id}');")
        lines.append("    if (hidden_) { hidden_.style.display = 'none'; }")
    if show_id:
        lines.append(f"    const shown_ = document.getElementById('{show_id}');")
        lines.append("    if (shown_) { shown_.style.display = 'flex'; }")
    lines.append("}")
    return "\n".join(lines)


_ABOUT_CLOSE_JS = _overlay_switch_js(hide_id="hf-about-overlay")
_ABOUT_OPEN_JS = _overlay_switch_js(show_id="hf-about-overlay")
_ABOUT_TO_LEGAL_JS = _overlay_switch_js(hide_id="hf-about-overlay", show_id="hf-legal-overlay")

_ONBOARDING_LAST_INDEX = len(ONBOARDING_STEPS) - 1

# La visite guidée ne se déclenche plus jamais automatiquement (voir historique Git) : un
# déclenchement lors d'un chargement lent — Render en sortie de veille, notamment — laissait le
# bouton « Suivant » visuellement figé sans le moindre retour, perçu comme cassé. Elle reste
# entièrement fonctionnelle, mais uniquement à la demande depuis « ⚙️ Paramètres ».
_LEGAL_ACCEPT_JS = """
() => {
    try {
        localStorage.setItem('legal_notice_acknowledged', 'true');
        localStorage.setItem('legal_notice_acknowledged_version', '1.0');
    } catch (error) {
        // Stockage indisponible : on masque quand même le bandeau pour la session en cours.
    }
    const legal = document.getElementById('hf-legal-overlay');
    if (legal) {
        legal.style.display = 'none';
    }
}
"""

_LEGAL_CHECK_JS = """
() => {
    let acknowledged = false;
    try {
        acknowledged = localStorage.getItem('legal_notice_acknowledged') === 'true';
    } catch (error) {
        acknowledged = false;
    }
    const overlay = document.getElementById('hf-legal-overlay');
    if (overlay) {
        overlay.style.display = acknowledged ? 'none' : 'flex';
    }
}
"""

_ONBOARDING_FINISH_JS = f"""
() => {{
    try {{
        localStorage.setItem('onboarding_completed', 'true');
        localStorage.setItem('onboarding_completed_version', '{ONBOARDING_VERSION}');
    }} catch (error) {{
        // Stockage indisponible : on masque quand même le panneau pour la session en cours.
    }}
    const overlay = document.getElementById('hf-onboarding-overlay');
    if (overlay) {{
        overlay.style.display = 'none';
    }}
}}
"""

_SETTINGS_CLOSE_JS = _overlay_switch_js(hide_id="hf-settings-overlay")
_SETTINGS_OPEN_JS = _overlay_switch_js(show_id="hf-settings-overlay")
_SETTINGS_TO_ONBOARDING_JS = _overlay_switch_js(hide_id="hf-settings-overlay", show_id="hf-onboarding-overlay")


def _format_onboarding_step(index: int) -> str:
    """Rendre le titre et le corps d'une étape de la visite guidée."""
    step = ONBOARDING_STEPS[index]
    return f"## {step.title}\n\n{step.body}"


def _format_onboarding_dots(index: int) -> str:
    """Indicateur de progression simple, sans dépendre d'une bibliothèque de carrousel."""
    return " ".join("●" if i == index else "○" for i in range(len(ONBOARDING_STEPS)))


def _onboarding_state(index: int) -> tuple[int, str, str, gr.Button, gr.Button, gr.Button]:
    """Construire la mise à jour complète des composants pour une étape donnée."""
    return (
        index,
        _format_onboarding_step(index),
        _format_onboarding_dots(index),
        gr.Button(visible=index > 0),
        gr.Button(visible=index < _ONBOARDING_LAST_INDEX),
        gr.Button(visible=index == _ONBOARDING_LAST_INDEX),
    )


def onboarding_go_next(index: int) -> tuple[int, str, str, gr.Button, gr.Button, gr.Button]:
    """Avancer d'une étape, sans dépasser la dernière."""
    return _onboarding_state(min(index + 1, _ONBOARDING_LAST_INDEX))


def onboarding_go_prev(index: int) -> tuple[int, str, str, gr.Button, gr.Button, gr.Button]:
    """Reculer d'une étape, sans descendre sous la première."""
    return _onboarding_state(max(index - 1, 0))


def onboarding_reset() -> tuple[int, str, str, gr.Button, gr.Button, gr.Button]:
    """Revenir à la première étape — utilisé quand la visite est rejouée depuis « À propos »."""
    return _onboarding_state(0)


def _build_about_markdown() -> str:
    """Assembler le texte de l'écran « À propos » à partir de métadonnées réelles.

    Rien n'est codé en dur : version/SHA viennent de Git (``src/app_info``), l'URL
    d'issues est dérivée du remote réel du dépôt — voir la commande /apropos.
    """
    version = app_info.get_app_version()
    sha = app_info.get_commit_sha()
    build = app_info.get_build_number()
    repo_url = app_info.get_repo_url()
    issue_url = app_info.get_issue_url()
    year = app_info.current_copyright_year()

    repo_line = f"[Dépôt GitHub et README]({repo_url})" if repo_url else "Dépôt GitHub : à renseigner"
    issue_line = f"[Signaler un bug]({issue_url})" if issue_url else "Signaler un bug : URL du dépôt à renseigner"
    versions_link = f"{repo_url}/blob/main/docs/versions.md" if repo_url else None
    legal_doc_link = f"{repo_url}/blob/main/docs/legal.md" if repo_url else None

    lines = [
        "## 🤗 HF Explorer (Huggor)",
        "",
        f"- **Version** : {version}",
        f"- **Commit** : `{sha}`",
        f"- **Build** : {build} — aucun système de build/CI n'attribue de numéro à ce projet",
    ]
    if versions_link:
        lines.append(f"- [Notes de version]({versions_link})")
    lines += [
        "",
        "### Auteur",
        "",
        "- Développeur : **Patrick Nouhailler**",
        "- Site web : [swinux.ch](https://swinux.ch)",
        "- Portfolio : [swinux.ch/applications](https://swinux.ch/applications/)",
        f"- {repo_line}",
        f"- {issue_line}",
        "",
        "### Support",
        "",
        f"- Contact : {LEGAL_EDITOR['email']}",
        "",
        "### Informations légales",
        "",
        "- **Mentions légales** : voir le bouton ci-dessous.",
        "- **CGU** : la clause de clôture des Mentions légales en tient lieu ; aucun document CGU séparé n'existe à ce jour.",
    ]
    if legal_doc_link:
        lines.append(f"- **Politique de confidentialité** : non créée à ce jour (aucune collecte ne le justifiait) — état des lieux et raison détaillés dans les [Mentions légales, section « Ce qui reste hors de ce texte »]({legal_doc_link}#ce-qui-reste-hors-de-ce-texte). À valider si une politique formelle devient nécessaire.")
    else:
        lines.append("- **Politique de confidentialité** : non créée à ce jour — à valider si nécessaire.")
    lines += [
        "",
        "### Crédits open source",
        "",
    ]
    lines += [f"- `{name}` — {license_name}" for name, license_name in app_info.DEPENDENCY_CREDITS]
    lines += [
        "",
        f"© {year} Patrick Nouhailler / {LEGAL_EDITOR['name']}",
        "",
        "[📚 Documentation](https://github.com/nouhailler/huggor/blob/main/docs/index.md)",
    ]
    return "\n".join(lines)


def _build_support_mailto_js() -> str:
    """Construire le JS du bouton support : un brouillon mailto, jamais un envoi silencieux.

    L'utilisateur relit et envoie lui-même depuis son client mail — voir /apropos.
    """
    version = app_info.get_app_version()
    sha = app_info.get_commit_sha()
    build = app_info.get_build_number()
    email = LEGAL_EDITOR["email"]
    return f"""
() => {{
    const diagnostics = [
        'Version : {version}',
        'Commit : {sha}',
        'Build : {build}',
        'Navigateur : ' + navigator.userAgent,
    ].join('\\n');
    const subject = encodeURIComponent('Support Huggor (HF Explorer)');
    const body = encodeURIComponent('Décrivez votre problème ici.\\n\\n---\\n' + diagnostics);
    window.location.href = 'mailto:{email}?subject=' + subject + '&body=' + body;
}}
"""


def connection_badge(has_token: bool) -> str:
    """Produire l'indicateur d'authentification sans afficher le token."""
    if has_token:
        label = "Token HF configuré"
        css_class = "authenticated"
    else:
        label = "Accès public"
        css_class = "public"
    return (
        f'<div class="hf-status {css_class}" role="status">'
        f'<span class="hf-status-dot"></span><span>{label}</span></div>'
    )


def create_app(client: HuggingFaceClient | None = None) -> gr.Blocks:
    """Assembler l'application sans la lancer, afin de faciliter les tests."""
    hub_client = client or HuggingFaceClient()

    # Depuis Gradio 6, le thème et le CSS sont transmis à launch().
    with gr.Blocks(title="HF Explorer", fill_width=True) as demo:
        with gr.Row(elem_classes="hf-header"):
            gr.HTML(
                """
                <div>
                    <div class="hf-title">🤗 HF Explorer</div>
                    <div class="hf-subtitle">
                        Recherchez, analysez et testez les modèles du Hugging Face Hub.
                    </div>
                </div>
                """
            )
            with gr.Row(elem_classes="hf-header-right"):
                gr.HTML(connection_badge(hub_client.has_token))
                menu_toggle = gr.Button(
                    "☰", elem_classes="hf-hamburger", size="sm", min_width=1
                )

        with gr.Column(visible=True, elem_classes="hf-legal-overlay", elem_id="hf-legal-overlay"):
            with gr.Column(elem_classes="hf-legal-card"):
                with gr.Column(elem_classes="hf-legal-scroll") as legal_short_page:
                    gr.Markdown(f"## {LEGAL_TITLE}\n\n{SHORT_WARNING}")
                with gr.Column(elem_classes="hf-legal-scroll", visible=False) as legal_full_page:
                    gr.Markdown(render_full_notice_markdown())
                with gr.Row(elem_classes="hf-legal-actions"):
                    legal_details_button = gr.Button("Voir les détails", variant="secondary", size="sm")
                    legal_back_button = gr.Button("← Retour", variant="secondary", size="sm", visible=False)
                    legal_accept_button = gr.Button("J'ai compris", variant="primary", size="sm")

        with gr.Column(visible=True, elem_classes="hf-legal-overlay", elem_id="hf-about-overlay"):
            with gr.Column(elem_classes="hf-legal-card"):
                with gr.Column(elem_classes="hf-legal-scroll"):
                    logo_path = Path(__file__).resolve().parent / "assets" / "swinux-logo.png"
                    gr.Image(
                        value=str(logo_path),
                        show_label=False,
                        container=False,
                        interactive=False,
                        buttons=[],
                        height=64,
                        width=64,
                        elem_classes="hf-about-logo",
                    )
                    gr.Markdown(_build_about_markdown())
                    about_support_button = gr.Button("📧 Contacter le support", variant="secondary", size="sm")
                    about_legal_button = gr.Button("⚖️ Mentions légales", variant="secondary", size="sm")
                with gr.Row(elem_classes="hf-legal-actions"):
                    about_close_button = gr.Button("Fermer", variant="primary", size="sm")

        with gr.Column(visible=True, elem_classes="hf-legal-overlay", elem_id="hf-settings-overlay"):
            with gr.Column(elem_classes="hf-legal-card"):
                with gr.Column(elem_classes="hf-legal-scroll"):
                    gr.Markdown(
                        "## ⚙️ Paramètres\n\n"
                        "Réglages généraux de l'application, indépendants d'un onglet précis."
                    )
                    gr.Markdown("**Visite guidée**")
                    settings_onboarding_button = gr.Button(
                        "🧭 Revoir la visite guidée", variant="secondary", size="sm"
                    )
                with gr.Row(elem_classes="hf-legal-actions"):
                    settings_close_button = gr.Button("Fermer", variant="primary", size="sm")

        onboarding_step = gr.State(0)
        with gr.Column(visible=True, elem_classes="hf-legal-overlay", elem_id="hf-onboarding-overlay"):
            with gr.Column(elem_classes="hf-legal-card"):
                with gr.Column(elem_classes="hf-legal-scroll"):
                    onboarding_dots = gr.Markdown(_format_onboarding_dots(0), elem_classes="hf-onboarding-dots")
                    onboarding_content = gr.Markdown(_format_onboarding_step(0))
                with gr.Row(elem_classes="hf-legal-actions"):
                    onboarding_skip_button = gr.Button("Passer l'introduction", variant="secondary", size="sm")
                    onboarding_prev_button = gr.Button("← Précédent", variant="secondary", size="sm", visible=False)
                    onboarding_next_button = gr.Button("Suivant →", variant="primary", size="sm")
                    onboarding_finish_button = gr.Button(
                        "🚀 Commencer", variant="primary", size="sm", visible=_ONBOARDING_LAST_INDEX == 0
                    )

        menu_open = gr.State(False)
        nav_buttons: dict[str, gr.Button] = {}
        with gr.Column(visible=False, elem_classes="hf-nav-menu") as nav_menu:
            for category_label, items in NAV_CATEGORIES:
                gr.Markdown(f"**{category_label}**", elem_classes="hf-nav-category")
                with gr.Row(elem_classes="hf-nav-row"):
                    for tab_id, tab_label in items:
                        nav_buttons[tab_id] = gr.Button(
                            tab_label, elem_classes="hf-nav-item", size="sm"
                        )
            with gr.Row(elem_classes="hf-nav-row hf-nav-footer"):
                settings_menu_button = gr.Button("⚙️ Paramètres", elem_classes="hf-nav-item", size="sm")
                about_menu_button = gr.Button("ℹ️ À propos", elem_classes="hf-nav-item", size="sm")

        details_repo_id = create_repo_id_input(render=False)
        with gr.Tabs(elem_classes="hf-main-tabs") as tabs:
            with gr.Tab("🔍 Recherche", id="search") as search_tab:
                pass
            with gr.Tab("🎯 Mon usage", id="usage") as usage_tab:
                pass
            with gr.Tab("📄 Détails", id="details"):
                details = build_details_tab(hub_client, repo_id=details_repo_id)
            with gr.Tab("💻 Hardware", id="hardware"):
                build_hardware_tab(hub_client)
            with gr.Tab("🆚 Comparateur", id="compare"):
                build_compare_tab(hub_client)
            with gr.Tab("🧪 Test", id="test"):
                build_test_tab()
            with gr.Tab("📈 Analytics", id="analytics"):
                build_analytics_tab(hub_client)
            with gr.Tab("⭐ Favoris", id="favorites"):
                build_favorites_tab(hub_client, details, tabs)

        with search_tab:
            build_search_tab(hub_client, details, tabs)
        with usage_tab:
            build_usage_tab(hub_client, details, tabs)

        menu_toggle.click(toggle_nav_menu, inputs=menu_open, outputs=[menu_open, nav_menu])
        for tab_id, nav_button in nav_buttons.items():
            nav_button.click(
                partial(select_tab_from_menu, tab_id), outputs=[tabs, menu_open, nav_menu]
            )

        legal_page_outputs = [legal_short_page, legal_full_page, legal_details_button, legal_back_button]
        legal_details_button.click(
            show_legal_details, outputs=legal_page_outputs, queue=False, show_progress="hidden"
        )
        legal_back_button.click(
            hide_legal_details, outputs=legal_page_outputs, queue=False, show_progress="hidden"
        )
        legal_accept_button.click(fn=None, js=_LEGAL_ACCEPT_JS, queue=False)

        about_menu_button.click(
            toggle_nav_menu, inputs=menu_open, outputs=[menu_open, nav_menu], queue=False, show_progress="hidden"
        ).then(fn=None, js=_ABOUT_OPEN_JS, queue=False)
        about_close_button.click(fn=None, js=_ABOUT_CLOSE_JS, queue=False)
        about_legal_button.click(
            show_legal_details, outputs=legal_page_outputs, queue=False, show_progress="hidden"
        ).then(fn=None, js=_ABOUT_TO_LEGAL_JS, queue=False)
        about_support_button.click(fn=None, js=_build_support_mailto_js(), queue=False)

        settings_menu_button.click(
            toggle_nav_menu, inputs=menu_open, outputs=[menu_open, nav_menu], queue=False, show_progress="hidden"
        ).then(fn=None, js=_SETTINGS_OPEN_JS, queue=False)
        settings_close_button.click(fn=None, js=_SETTINGS_CLOSE_JS, queue=False)

        onboarding_outputs = [
            onboarding_step,
            onboarding_content,
            onboarding_dots,
            onboarding_prev_button,
            onboarding_next_button,
            onboarding_finish_button,
        ]
        onboarding_next_button.click(
            onboarding_go_next, inputs=onboarding_step, outputs=onboarding_outputs,
            queue=False, show_progress="hidden",
        )
        onboarding_prev_button.click(
            onboarding_go_prev, inputs=onboarding_step, outputs=onboarding_outputs,
            queue=False, show_progress="hidden",
        )
        onboarding_finish_button.click(fn=None, js=_ONBOARDING_FINISH_JS, queue=False)
        onboarding_skip_button.click(fn=None, js=_ONBOARDING_FINISH_JS, queue=False)
        settings_onboarding_button.click(
            onboarding_reset, outputs=onboarding_outputs, queue=False, show_progress="hidden"
        ).then(fn=None, js=_SETTINGS_TO_ONBOARDING_JS, queue=False)

        with gr.Row(elem_classes="hf-footer"):
            gr.Markdown(
                "Données fournies par le [Hugging Face Hub](https://huggingface.co/models). "
                "[📚 Documentation](https://github.com/nouhailler/huggor/blob/main/docs/index.md)",
                container=False,
            )
            legal_footer_button = gr.Button(
                "⚖️ Mentions légales", elem_classes="hf-footer-legal-button", size="sm"
            )
        legal_footer_button.click(
            show_legal_details, outputs=legal_page_outputs, queue=False, show_progress="hidden"
        ).then(fn=None, js=_LEGAL_OPEN_JS, queue=False)

        demo.load(fn=None, js=_LEGAL_CHECK_JS, queue=False)

    return demo


def main() -> None:
    """Lancer le serveur Gradio avec les paramètres de l'environnement."""
    server_name = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    raw_port = os.getenv("GRADIO_SERVER_PORT", "7860")
    try:
        server_port = int(raw_port)
    except ValueError as error:
        raise ValueError("GRADIO_SERVER_PORT doit être un nombre entier.") from error

    create_app().queue().launch(
        server_name=server_name,
        server_port=server_port,
        theme=create_theme(),
        css=APP_CSS,
        show_error=True,
    )


if __name__ == "__main__":
    main()
