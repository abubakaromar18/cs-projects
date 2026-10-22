"""Allow ``python -m todo_cli``."""

import sys

from .cli import main

sys.exit(main())
