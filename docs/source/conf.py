"""
Sphinx configuration for fieldframe documentation.
"""

import os
import sys

# Make the source package importable so autodoc can introspect it
sys.path.insert(0, os.path.abspath("../src"))

# ---------------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------------

project = "fieldframe"
author = "Fraser Toon"
release = "1.0.0"
copyright = f"2026, {author}"

# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",  # Pull docstrings from source automatically
    "sphinx.ext.napoleon",  # Support Google and NumPy style docstrings
    "sphinx.ext.viewcode",  # Add [source] links next to every class/function
    "sphinx.ext.intersphinx",  # Cross-link to Python standard library docs
    "sphinx.ext.autosummary",  # Generate summary tables for modules
]

# ---------------------------------------------------------------------------
# autodoc settings
# ---------------------------------------------------------------------------

autodoc_default_options = {
    "members": True,  # Document all public members
    "undoc-members": False,  # Skip members with no docstring
    "private-members": False,  # Skip _private methods
    "show-inheritance": True,  # Show base classes
    "no-index": False,
}

# Add this to suppress the duplicates
suppress_warnings = ["autodoc.duplicate"]

autodoc_member_order = "bysource"  # Keep the order as written in source
autoclass_content = "both"  # Include both class and __init__ docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True

# ---------------------------------------------------------------------------
# intersphinx — cross-link to Python stdlib
# ---------------------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------

html_theme = "furo"  # pip install furo

html_theme_options = {
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
}

html_static_path = ["_static"]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
