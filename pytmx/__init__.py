from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from .pytmx import (
    TiledElement,
    TiledMap,
    TiledTileset,
    TiledTileLayer,
    TiledObject,
    TiledObjectGroup,
    TiledImageLayer,
    TileFlags)

# not sure why this needs to be imported.
# if not, it seems to break some code, idk
try:
    from pytmx.util_pygame import load_pygame
except ImportError:
    import logging

    logger = logging.getLogger(__name__)
    logger.debug('cannot import pygame tools')

__version__ = (3, 20, 18)
__author__ = 'bitcraft'
__author_email__ = 'leif.theden@gmail.com'
__description__ = 'Map loader for TMX Files - Python 2 and 3'
