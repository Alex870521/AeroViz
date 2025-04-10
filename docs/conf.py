# Configuration file for the Sphinx documentation builder.

import os
import sys

sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------

project = 'AeroViz'
copyright = '2024, AeroViz Team'
author = 'AeroViz Team'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'myst_parser',
    'sphinx_rtd_theme',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The master document
master_doc = 'index'

# Source file patterns
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- MyST-Parser configuration ----------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "replacements",
    "smartquotes",
    "tasklist",
]

# -- GitHub Pages configuration ---------------------------------------------

html_baseurl = 'https://alex870521.github.io/AeroViz/'

# -- Navigation configuration ----------------------------------------------

html_theme_options = {
    'navigation_depth': 4,
    'titles_only': False,
    'collapse_navigation': True,
    'sticky_navigation': True,
    'includehidden': True,
    'display_version': True,
    'logo_only': False,
    'prev_next_buttons_location': 'both',
    'style_external_links': True,
    'style_nav_header_background': '#2980B9',
    'vcs_pageview_mode': 'blob',
}

# -- Document structure ---------------------------------------------------

html_sidebars = {
    '**': [
        'globaltoc.html',
        'relations.html',
        'sourcelink.html',
        'searchbox.html',
    ]
}


# -- Custom CSS ----------------------------------------------------------

def setup(app):
    app.add_css_file('custom.css')


# -- AutoDoc configuration ----------------------------------------------

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}
