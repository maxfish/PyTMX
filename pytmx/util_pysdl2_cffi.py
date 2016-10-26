"""
Copyright (C) 2012-2016

This file is part of pytmx.

pytmx is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pytmx is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pytmx.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
from functools import partial

try:
    import sdl
except ImportError:
    logger.error('cannot import pysdl_cffi (is it installed?)')
    raise

__all__ = ('load_pysdl2_cffi', 'pysdl2_cffi_image_loader')

logger = logging.getLogger(__name__)

flag_names = ('flipped_horizontally',
              'flipped_vertically',
              'flipped_diagonally',)


def pysdl2_cffi_image_loader(ctx, filename, colorkey, **kwargs):
    def load_image(rect=None, flags=None):
        if rect:
            try:
                flip = 0
                if flags.flipped_horizontally:
                    flip |= sdl.FLIP_HORIZONTAL
                if flags.flipped_vertically:
                    flip |= sdl.FLIP_VERTICAL
                if flags.flipped_diagonally:
                    flip |= 4

                this_rect = sdl.Rect()
                this_rect.x = rect[0]
                this_rect.y = rect[1]
                this_rect.w = rect[2]
                this_rect.h = rect[3]
                return texture, this_rect, flip

            except ValueError:
                logger.error('Tile bounds outside bounds of tileset image')
                raise
        else:
            return texture, None, 0

    texture = sdl.image.loadTexture(ctx.renderer, filename)

    return load_image


def load_pysdl2_cffi(ctx, filename, *args, **kwargs):
    import pytmx

    kwargs['image_loader'] = partial(pysdl2_cffi_image_loader, ctx)
    return pytmx.TiledMap(filename, *args, **kwargs)
