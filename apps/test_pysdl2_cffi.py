"""
This is tested on pysdl2 1.2 and python 2.7.
Leif Theden "bitcraft", 2012-2014

Rendering demo for the TMXLoader.

This should be considered --alpha-- quality.  I'm including it as a
proof-of-concept for now and will improve on it in the future.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from pytmx import TiledTileLayer
from pytmx.util_pysdl2_cffi import load_pysdl2_cffi


class SDLContext(object):
    def __init__(self):
        self.window = None
        self.renderer = None
        self.display_info = None


def is_quit_event(event):
    return event.type == sdl.QUIT or \
           (event.type == sdl.KEYDOWN and event.key.keysym.sym == sdl.K_ESCAPE)


class TiledRenderer(object):
    """
    Super simple way to render a tiled map with pysdl2
    """

    def __init__(self, ctx, filename):
        tm = load_pysdl2_cffi(ctx, filename)
        self.ctx = ctx
        self.size = tm.width * tm.tilewidth, tm.height * tm.tileheight
        self.tmx_data = tm

    def render_tile_layer(self, layer):
        """ Render the tile layer

        DOES NOT CHECK FOR DRAWING TILES OFF THE SCREEN
        """
        # deref these heavily used references for speed
        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight
        renderer = self.ctx.renderer

        dest = sdl.Rect()
        dest.x = 0
        dest.y = 0
        dest.w = tw
        dest.h = th
        rce = sdl.renderCopyEx

        # iterate over the tiles in the layer
        for x, y, tile in layer.tiles():
            texture, src, flip = tile
            dest.x = x * tw
            dest.y = y * th
            angle = 90 if (flip & 4) else 0
            rce(renderer, texture, src, dest, angle, None, flip)

    def render_map(self):
        """ Render the entire map

        Only tile layer drawing is implemented
        """
        for layer in self.tmx_data.visible_layers:

            # draw map tile layers
            if isinstance(layer, TiledTileLayer):
                self.render_tile_layer(layer)


class SimpleTest(object):
    def __init__(self, ctx, filename):
        self.running = False
        self.dirty = False
        self.exit_status = 0
        self.ctx = ctx
        self.map_renderer = TiledRenderer(ctx, filename)
        self.event = sdl.Event()

        logger.info("Objects in map:")
        for obj in self.map_renderer.tmx_data.objects:
            logger.info(obj)
            for k, v in obj.properties.items():
                logger.info("%s\t%s", k, v)

        logger.info("GID (tile) properties:")
        for k, v in self.map_renderer.tmx_data.tile_properties.items():
            logger.info("%s\t%s", k, v)

    def draw(self):
        renderer = self.ctx.renderer
        sdl.renderClear(renderer)
        self.map_renderer.render_map()
        sdl.renderPresent(renderer)

    def run(self):
        """Starts an event loop without actually processing any event."""
        self.running = True
        self.exit_status = 1
        while self.running:
            while sdl.pollEvent(self.event) != 0:
                if is_quit_event(self.event):
                    quit_sdl(self.ctx)
                    self.running = False
                    self.exit_status = 0
                    break
                elif self.event.type == sdl.KEYDOWN:
                    self.running = False
                    self.exit_status = 1
                    break

            if self.running:
                self.draw()

        return self.exit_status


def all_filenames():
    import os.path
    import glob
    return glob.glob(os.path.join('data', '0.9.1', '*.tmx'))


def quit_sdl(sdl_context):
    if sdl_context.renderer is not None:
        sdl.destroyRenderer(sdl_context.renderer)
    if sdl_context.window is not None:
        sdl.destroyWindow(sdl_context.window)
    sdl.quit()


def handle_sdl_errors(callback, sdl_context):
    try:
        callback()
    except sdl.SDLError as e:
        print(e.message)
    finally:
        quit_sdl(sdl_context)


if __name__ == '__main__':
    import sdl

    sdl.init(sdl.INIT_VIDEO)

    ctx = SDLContext()
    ctx.display_info = sdl.DisplayMode()
    sdl.getDesktopDisplayMode(0, ctx.display_info)

    ctx.window = sdl.createWindow(
        "pytmx + psdl2 = awesome???",
        0, 0,
        ctx.display_info.w, ctx.display_info.h,
        sdl.WINDOW_SHOWN)

    sdl.setWindowFullscreen(ctx.window, sdl.WINDOW_FULLSCREEN)

    ctx.renderer = sdl.createRenderer(
        ctx.window,
        -1,  # What's this do? ¯\_(ツ)_/¯
        sdl.RENDERER_ACCELERATED |
        sdl.RENDERER_PRESENTVSYNC)

    try:
        for filename in all_filenames():
            logger.info("Testing %s", filename)
            if not SimpleTest(ctx, filename).run():
                break
    except:
        raise
