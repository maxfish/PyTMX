import logging

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

from .pytmx import *
from . import util_xml

try:
    from .util_pygame import load_pygame
except ImportError:
    logger.debug('cannot import pygame tools')
    raise


__version__ = (3, 21, 0)
__author__ = 'bitcraft'
__author_email__ = 'leif.theden@gmail.com'
__description__ = 'Map loader for TMX Files - Python 2 and 3'
