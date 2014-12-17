So You Want to Make a Game with pytmx?
======================================

This tutorial will introduce you to how pytmx works and how to get the most out
of it.  We will go over the structure of TMX files and learn how to get your
maps on to the screen.  This tutorial assumes that you are using pygame, but
it can be adapted for use with pysdl2 or pyglet.


Introduction to pytmx
=====================

pytmx loads TMX files and give you a few handy classes to access the data from
TMX files along with loading the images from tilesets.  That is pretty much it.
What you do with the data after that is up to you.  This tutorial will show you
one way to get your maps onto the screen.


pytmx Classes
=============

Here is a quick introduction to the classes that pytmx give you to work with.

TiledMap
--------
You will keep a reference to this to access all of the map data


TiledTileLayer
--------------
Holds layer data.  Its possible to use this class directly, but it is easier to
use TiledMap.

TiledObject
-----------
Holds data about 'Objects' created in tiled.

TiledObjectGroup
----------------
Is a list of Tiled Objects, just like a Tiled Image group.

TiledImageLayer
---------------
This is for Tiled's "Image layer", which is just a layer with one image.


Loading the Map
===============

    from pytmx import load_pygame
    tmxdata = load_pygame("map.tmx")



For Python Newbies
==================

So, I -know- that you are just dying to get your map on the screen, but just a
couple more concepts first so that things make sense later.

If you are using pytmx and python to learn how to program and make a game, then
I have to give you a couple pointers first.  If you are unfamiliar with any of
the concepts below, then you might take some time and go over them online or
in whatever materials you are using to learn python.  Because of the innumerable
amount of resources in print and on the web for python, I'm not going to make
any recommendations.  Just find something that makes sense to you.

- iterators


Understanding the TiledMap object
=================================

The TiledMap object is designed to be the main point-of-entry when accessing map
data.  You can get the layers, their data, the images, objects, and even raw
layer data from the TiledMap object.


Many ways to work with TiledMap objects
=======================================

pass


Drawing the Map
===============

Here are a few ways to get your map onto the screen.  Keep in mind that the best
way in most cases is going to be the iterator method.  While the implementation
may differ, each method essentially will be doing the same thing, which I will
illustrate in pseudo code:

for each layer in the map:
   if layer is a tile layer and is visible:
       for each tile in the layer:
          x, y = the tile location in the layer
          screen_x = x * the tile width
          screen_y = y * the tile height
          tile = some_function_to_get_the_tile_image
          draw_the_tile(the screen, screen_x, screen_y)

   if layer is an object layer and is visible:
       for each object in the object layer:
           draw object somewhere

Iterator Method
---------------

The iterator method simplifies drawing by doing stuff for you.  Lots of stuff.
Trust me.  Here's what the above psuedo code looks like translated to python in
the iterator method.

for layer in tmxmap.visible_layers:
    if isinstance(layer, TiledTileLayer):
        for x, y, tile_image in layer.tiles():
            screen.blit(itile_mage, (x * tile_width, y * tile_height))
            # draw object layers

    elif isinstance(layer, TiledObjectGroup):
        for obj in layer:
            # <do whatever you want to draw the object>

Index Method
------------

Sometimes you might want to draw a layer by name or require some other order
to draw stuff.  Here's one way to get layers and draw them without using the
iterator protocol.  Bear in mind that this way is going to be slightly less
pessimum than using the iterator method described above.

for layer_number in range(tmxdata.len(layers)):
    for x in range(tmxdata.width):
        for y in range(tmxdata.height):
            tile_image = tmxdata.get_tile_image(x, y, layer_number)
            screen.blit(tile_image, (x * tile_width, y * tile_height))
