# DEPRECATED: This package is superseded by Zeus. All logic and tests should be migrated to ZeusBlueprint. File retained for legacy reference only.

# Enhanced search/analysis UX: show ANSI/emoji boxes, summarize results, show result counts, display params, update line numbers, distinguish code/semantic
# This is a stub for gawd blueprint search/analysis UX. (If this blueprint is implemented, the run method should follow the unified UX pattern.)

default_app_config = 'blueprints.gawd.apps.GAWDConfig'

# No run method in __init__.py, but if/when a blueprint is implemented here, ensure:
# - Support for both code and semantic search (with clear output distinction)
# - ANSI/emoji boxes for search/analysis, with result counts, search params, and progress
# - Creative output box for non-search/agent output
# - Spinner states: 'Generating.', 'Generating..', 'Generating...', 'Running...'
