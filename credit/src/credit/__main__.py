"""CLI entry for ``python -m credit``.

This module is only loaded via ``python -m credit`` (not imported as a library),
so the CLI is invoked at module level.
"""

from credit.cli import main

main()
