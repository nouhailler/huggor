"""Composants Gradio modulaires de HF Explorer."""

from .analytics_tab import build_analytics_tab
from .compare_tab import build_compare_tab
from .details_tab import DetailsTabComponents, build_details_tab
from .favorites_tab import build_favorites_tab
from .search_tab import SearchTabComponents, build_search_tab
from .test_tab import build_test_tab

__all__ = [
    "DetailsTabComponents",
    "SearchTabComponents",
    "build_analytics_tab",
    "build_compare_tab",
    "build_details_tab",
    "build_favorites_tab",
    "build_search_tab",
    "build_test_tab",
]
