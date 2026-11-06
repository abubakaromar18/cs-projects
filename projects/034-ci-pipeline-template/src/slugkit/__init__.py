"""slugkit: a tiny sample library that gives the CI template something real to test.

Turns arbitrary text into URL-safe slugs.
"""

from slugkit.core import slugify, unique_slug

__all__ = ["slugify", "unique_slug", "__version__"]
__version__ = "0.1.0"
