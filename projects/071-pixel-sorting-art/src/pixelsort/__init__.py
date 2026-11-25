"""pixelsort — glitch art by sorting runs of pixels.

Public API::

    from pixelsort import sort_image, SortConfig
"""

from .sorter import SortConfig, sort_image, sort_array

__all__ = ["SortConfig", "sort_image", "sort_array"]
__version__ = "1.0.0"
