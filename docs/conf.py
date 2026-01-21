# Configuration file for Sphinx documentation builder
# AindusDB Core - Auto-generated documentation

import os
import sys

# Add the project root to the Python path so Sphinx can import modules
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../app'))

# -- Project information -----------------------------------------------------
project = 'AindusDB Core'
copyright = '2026, AindusDB Team'
author = 'AindusDB Team'
version = '1.0.0'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',        # Auto-generate docs from docstrings
    'sphinx.ext.viewcode',       # Add source code links
    'sphinx.ext.napoleon',       # Support for Google and NumPy style docstrings
    'sphinx.ext.intersphinx',    # Link to other documentation
    'sphinx.ext.todo',           # Support for todo items
    'sphinx.ext.coverage',       # Coverage checker for documentation
    'sphinx_rtd_theme',          # Read the Docs theme
    'myst_parser',               # Markdown support
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The suffix(es) of source filenames.
source_suffix = {
    '.rst': None,
    '.md': None,
}

# The master toctree document.
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_title = f'{project} Documentation'
html_short_title = project
html_logo = None
html_favicon = None

# Theme-specific options
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Add any paths that contain custom static files (such as style sheets)
html_static_path = ['_static']

# Custom CSS
html_css_files = [
    'custom.css',
]

# -- Extension configuration -------------------------------------------------

# autodoc options
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}
autodoc_typehints = 'description'
autodoc_mock_imports = ['asyncpg', 'fastapi', 'pydantic', 'pydantic_settings']

# napoleon options for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'fastapi': ('https://fastapi.tiangolo.com/', None),
    'pydantic': ('https://pydantic-docs.helpmanual.io/', None),
}

# todo options
todo_include_todos = True
todo_emit_warnings = True

# -- Options for LaTeX output -----------------------------------------------
latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '10pt',
    'preamble': '',
    'fncychap': '',
    'maketitle': '\\maketitle',
}

latex_documents = [
    (master_doc, 'AindusDBCore.tex', f'{project} Documentation',
     author, 'manual'),
]

# -- Options for manual page output -----------------------------------------
man_pages = [
    (master_doc, 'aindusdb-core', f'{project} Documentation',
     [author], 1)
]

# -- Options for Texinfo output ---------------------------------------------
texinfo_documents = [
    (master_doc, 'AindusDBCore', f'{project} Documentation',
     author, 'AindusDBCore', 'Open source vector database built on PostgreSQL + pgvector.',
     'Miscellaneous'),
]
