"""Point d'entrée et composition de l'interface Gradio de HF Explorer."""

from __future__ import annotations

import os
from functools import partial

import gradio as gr

from src.api_client import HuggingFaceClient
from src.ui.analytics_tab import build_analytics_tab
from src.ui.compare_tab import build_compare_tab
from src.ui.details_tab import build_details_tab, create_repo_id_input
from src.ui.favorites_tab import build_favorites_tab
from src.ui.hardware_tab import build_hardware_tab
from src.ui.search_tab import build_search_tab
from src.ui.usage_tab import build_usage_tab
from src.ui.test_tab import build_test_tab

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

        gr.Markdown(
            "Données fournies par le [Hugging Face Hub](https://huggingface.co/models).",
            elem_classes="hf-footer",
        )

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
