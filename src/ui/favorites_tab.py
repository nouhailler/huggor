"""Onglet Gradio des favoris : collections, notes, tags, statut, score et suivi de test."""

from __future__ import annotations

import html
from datetime import date
from functools import partial
from typing import Any
from urllib.parse import quote

import gradio as gr

from src.api_client import HuggingFaceClient
from src.paths import data_directory
from src.ui.details_tab import DetailsTabComponents, load_details_for_ui
from src.ui.search_tab import select_model_for_details
from src.utils.favorites import FavoritesError, FavoritesStore
from src.utils.formatters import escape_markdown

_STATUS_CHOICES = ["", "à tester", "testé", "recommandé", "à écarter"]
_ALL_COLLECTIONS = ""


def build_favorites_tab(
    client: HuggingFaceClient,
    details: DetailsTabComponents,
    app_tabs: gr.Tabs,
    favorites: FavoritesStore | None = None,
) -> None:
    """Construire la liste filtrable des favoris, avec édition complète par carte."""
    favorites_store = favorites or FavoritesStore(data_directory() / "favorites.json")

    gr.Markdown(
        "## ⭐ Favoris\n"
        "Retrouvez vos modèles enregistrés, classez-les en collections et notez vos essais."
    )

    with gr.Row():
        collection_filter = gr.Dropdown(
            choices=_collection_filter_choices(favorites_store),
            value=_ALL_COLLECTIONS,
            label="📁 Collection",
            scale=2,
        )
        refresh_button = gr.Button("🔄 Actualiser", scale=1)

    status = gr.Markdown("", elem_classes="hf-favorite-status")
    favorites_state = gr.State(_filter_favorites(favorites_store, _ALL_COLLECTIONS))

    collection_filter.change(
        fn=partial(_filter_favorites, favorites_store),
        inputs=collection_filter,
        outputs=favorites_state,
        api_visibility="private",
        show_progress="hidden",
    )
    refresh_button.click(
        fn=partial(_refresh_after_mutation, favorites_store),
        inputs=collection_filter,
        outputs=[favorites_state, collection_filter],
        api_visibility="private",
        show_progress="hidden",
    )

    @gr.render(inputs=favorites_state, show_progress="hidden")
    def render_favorites(items: list[dict[str, Any]] | None) -> None:
        """Afficher chaque favori en carte, avec son panneau d'édition complet."""
        if not items:
            gr.Markdown("_Aucun favori pour l'instant. Ajoutez-en depuis une fiche modèle._")
            return

        for index, item in enumerate(items):
            repo_id = str(item.get("repo_id") or "")
            key_suffix = f"{index}-{repo_id}"
            with gr.Group(key=f"favorite-card-{key_suffix}", elem_classes="hf-result-card"):
                with gr.Row(equal_height=False):
                    gr.Markdown(
                        format_favorite_card(item),
                        container=False,
                        elem_classes="hf-result-content",
                    )
                    details_button = gr.Button(
                        "Voir détails →",
                        variant="secondary",
                        size="sm",
                        min_width=135,
                        scale=0,
                        key=f"favorite-details-{key_suffix}",
                    )
                details_button.click(
                    fn=partial(select_model_for_details, repo_id),
                    outputs=[details.repo_id, app_tabs],
                    queue=False,
                    show_progress="hidden",
                    api_visibility="private",
                ).then(
                    fn=partial(load_details_for_ui, client),
                    inputs=details.repo_id,
                    outputs=list(details.load_outputs),
                    show_progress="minimal",
                    api_visibility="private",
                    concurrency_limit=2,
                    concurrency_id="hub-details",
                )

                with gr.Accordion("✏️ Modifier", open=False, key=f"favorite-edit-{key_suffix}"):
                    with gr.Row():
                        collection_input = gr.Dropdown(
                            choices=favorites_store.list_collections(),
                            value=str(item.get("collection") or ""),
                            label="Collection",
                            allow_custom_value=True,
                            key=f"favorite-collection-{key_suffix}",
                        )
                        status_input = gr.Dropdown(
                            choices=_STATUS_CHOICES,
                            value=str(item.get("status") or ""),
                            label="Statut",
                            allow_custom_value=True,
                            key=f"favorite-status-{key_suffix}",
                        )
                        score_input = gr.Slider(
                            minimum=0,
                            maximum=5,
                            step=1,
                            value=item.get("score") or 0,
                            label="Note personnelle (0 = aucune)",
                            key=f"favorite-score-{key_suffix}",
                        )
                    tags_input = gr.Textbox(
                        value=", ".join(item.get("tags") or []),
                        label="Tags (séparés par des virgules)",
                        placeholder="coding, français, local",
                        key=f"favorite-tags-{key_suffix}",
                    )
                    with gr.Row():
                        last_tested_input = gr.Textbox(
                            value=str(item.get("last_tested_at") or ""),
                            label="Dernier test (JJ/MM/AAAA)",
                            placeholder="Ex. 11/09/2026",
                            scale=3,
                            key=f"favorite-tested-{key_suffix}",
                        )
                        today_button = gr.Button(
                            "Aujourd'hui", scale=1, size="sm", key=f"favorite-today-{key_suffix}"
                        )
                    note_input = gr.Textbox(
                        value=str(item.get("note") or ""),
                        label="Commentaire / note personnelle",
                        placeholder="Ex. Très bon compromis 16 Go RAM",
                        lines=3,
                        key=f"favorite-note-{key_suffix}",
                    )
                    with gr.Row():
                        save_button = gr.Button(
                            "💾 Enregistrer", variant="primary", key=f"favorite-save-{key_suffix}"
                        )
                        remove_button = gr.Button(
                            "🗑️ Retirer des favoris", variant="stop", key=f"favorite-remove-{key_suffix}"
                        )
                    edit_status = gr.Markdown("", key=f"favorite-edit-status-{key_suffix}")

                today_button.click(
                    fn=lambda: date.today().strftime("%d/%m/%Y"),
                    outputs=last_tested_input,
                    queue=False,
                    show_progress="hidden",
                    api_visibility="private",
                )
                save_button.click(
                    fn=partial(_save_favorite_edits, favorites_store, repo_id),
                    inputs=[
                        collection_input, status_input, score_input,
                        tags_input, last_tested_input, note_input, collection_filter,
                    ],
                    outputs=[edit_status, favorites_state, collection_filter],
                    show_progress="hidden",
                    api_visibility="private",
                )
                remove_button.click(
                    fn=partial(_remove_favorite_for_ui, favorites_store, repo_id),
                    inputs=collection_filter,
                    outputs=[status, favorites_state, collection_filter],
                    show_progress="hidden",
                    api_visibility="private",
                )


def _collection_filter_choices(store: FavoritesStore) -> list[tuple[str, str]]:
    """Lister les collections disponibles pour le filtre, avec un choix « toutes »."""
    try:
        collections = store.list_collections()
    except FavoritesError:
        collections = []
    return [("Toutes les collections", _ALL_COLLECTIONS)] + [(name, name) for name in collections]


def _filter_favorites(store: FavoritesStore, collection_value: str) -> list[dict[str, Any]]:
    """Lister les favoris (les plus récents d'abord), filtrés par collection si demandé."""
    try:
        favorites = store.list_favorites()
    except FavoritesError:
        return []
    filtered = [
        favorite for favorite in favorites if not collection_value or favorite.collection == collection_value
    ]
    filtered.sort(key=lambda favorite: favorite.added_at, reverse=True)
    return [favorite.to_dict() for favorite in filtered]


def _refresh_after_mutation(store: FavoritesStore, collection_value: str) -> tuple[list[dict[str, Any]], gr.Dropdown]:
    """Recharger la liste et les choix de collection après un ajout, une édition ou un retrait."""
    choices = _collection_filter_choices(store)
    valid_values = {value for _label, value in choices}
    kept_value = collection_value if collection_value in valid_values else _ALL_COLLECTIONS
    return _filter_favorites(store, kept_value), gr.Dropdown(choices=choices, value=kept_value)


def _save_favorite_edits(
    store: FavoritesStore,
    repo_id: str,
    collection_value: str,
    status_value: str,
    score_value: float,
    tags_value: str,
    last_tested_value: str,
    note_value: str,
    collection_filter_value: str,
) -> tuple[str, list[dict[str, Any]], gr.Dropdown]:
    """Enregistrer les modifications d'un favori et rafraîchir la liste affichée."""
    try:
        store.update(
            repo_id,
            collection=collection_value or "",
            status=status_value or "",
            score=int(score_value) if score_value else None,
            clear_score=not score_value,
            tags=[tag.strip() for tag in (tags_value or "").split(",")],
            last_tested_at=last_tested_value or "",
            note=note_value or "",
        )
        message = "✅ Favori mis à jour."
    except (ValueError, FavoritesError) as error:
        message = f"⚠️ {html.escape(str(error))}"
    except Exception:
        message = "⚠️ Une erreur inattendue est survenue."

    favorites, dropdown = _refresh_after_mutation(store, collection_filter_value)
    return message, favorites, dropdown


def _remove_favorite_for_ui(
    store: FavoritesStore,
    repo_id: str,
    collection_filter_value: str,
) -> tuple[str, list[dict[str, Any]], gr.Dropdown]:
    """Retirer un favori et rafraîchir la liste affichée."""
    try:
        removed = store.remove(repo_id)
        message = f"🗑️ **{escape_markdown(repo_id)}** a été retiré des favoris." if removed else ""
    except (ValueError, FavoritesError) as error:
        message = f"⚠️ {html.escape(str(error))}"
    except Exception:
        message = "⚠️ Une erreur inattendue est survenue."

    favorites, dropdown = _refresh_after_mutation(store, collection_filter_value)
    return message, favorites, dropdown


def format_favorite_card(item: dict[str, Any]) -> str:
    """Présenter un favori et son classement personnel en carte Markdown lisible."""
    repo_id = str(item.get("repo_id") or "Modèle sans nom")
    safe_repo = escape_markdown(repo_id)
    url = f"https://huggingface.co/{quote(repo_id, safe='/')}"

    score = item.get("score")
    stars = f"{'⭐' * int(score)} {score}/5" if score else "⭐ Non noté"

    collection = str(item.get("collection") or "").strip()
    collection_line = f"📁 {escape_markdown(collection)}" if collection else "📁 Non classé"

    tags = [str(tag) for tag in (item.get("tags") or [])]
    tags_line = "🏷 " + ", ".join(escape_markdown(tag) for tag in tags) if tags else "🏷 _Aucun tag_"

    status_value = str(item.get("status") or "").strip()
    status_line = f"Statut : **{escape_markdown(status_value)}**" if status_value else "Statut : _non renseigné_"

    last_tested = str(item.get("last_tested_at") or "").strip()
    tested_line = f"Dernier test : {escape_markdown(last_tested)}" if last_tested else "Dernier test : _jamais_"

    note = str(item.get("note") or "").strip()
    note_line = f"“{escape_markdown(note)}”" if note else "_Aucune note personnelle._"

    added_at = str(item.get("added_at") or "")[:10]

    return (
        f"### [{safe_repo}]({url})\n"
        f"{collection_line} · {stars}  \n"
        f"{tags_line}  \n"
        f"{note_line}  \n"
        f"{status_line} · {tested_line}  \n"
        f"_Ajouté le {escape_markdown(added_at) or '—'}_"
    )
