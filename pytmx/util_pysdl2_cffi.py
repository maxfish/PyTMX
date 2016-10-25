import logging
from functools import partial

logger = logging.getLogger(__name__)

try:
    import sdl
except ImportError:
    logger.error('cannot import pysdl_cffi (is it installed?)')
    raise

__all__ = ['load_pysdl2_cffi',
           'pysdl2_cffi_image_loader']

flag_names = ('flipped_horizontally',
              'flipped_vertically',
              'flipped_diagonally',)


def pysdl2_cffi_image_loader(ctx, filename, colorkey, **kwargs):
    def load_image(rect=None, flags=None):
        if rect:
            try:
                flip = 0
                if flags.flipped_horizontally:
                    flip |= sdl.SDL_FLIP_HORIZONTAL
                if flags.flipped_vertically:
                    flip |= sdl.SDL_FLIP_VERTICAL
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
