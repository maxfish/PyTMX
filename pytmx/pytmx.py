import logging
import os
from itertools import chain, product
from collections import defaultdict
from operator import attrgetter

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

__all__ = ['TiledMap', 'TiledTileset', 'TiledTileLayer', 'TiledObject',
           'TiledObjectGroup', 'TiledImageLayer', 'TiledElement']


def default_image_loader(filename, flags, **kwargs):
    """Default image loader.  This one doesn't actually load anything.
    """
    def load(rect=None, flags=None):
        return filename, rect, flags
    return load


class TiledElement(object):
    reserved = None

    def __init__(self):
        self.properties = dict()

    def __getattr__(self, item):
        try:
            return self.properties[item]
        except KeyError:
            raise AttributeError

    def __repr__(self):
        return '<{0}: "{1}">'.format(self.__class__.__name__, self.name)


class TiledMap(TiledElement):
    """Contains the layers, objects, and images

    This class is meant to handle most of the work you need to do to use a map.
    """
    reserved = "properties tileset layer objectgroup".split()

    def __init__(self, filename=None, image_loader=default_image_loader,
                 **kwargs):
        """
        :param image_loader: function that will load images (see below)
        :param filename: filename of tiled map to load

        image_loader:
          this must be a reference to a function that will accept a tuple:
          (filename of image, bounding rect of tile in image, flags)

          the function must return a reference to to the tile.
        """
        TiledElement.__init__(self)
        self.filename = filename
        self.image_loader = image_loader

        # optional keyword arguments checked here
        self.optional_gids = kwargs.get('optional_gids', set())
        self.load_all_tiles = kwargs.get('load_all', False)
        self.invert_y = kwargs.get('invert_y', True)

        # defaults from the TMX specification
        self.version = 0.0
        self.orientation = None
        self.width = 0       # width of map in tiles
        self.height = 0      # height of map in tiles
        self.tilewidth = 0   # width of a tile in pixels
        self.tileheight = 0  # height of a tile in pixels
        self.background_color = None
        self.visible = True

        # will be filled in by a loader function
        self.maxgid = 1
        self.images = list()           # GID == index of image
        self.layers = list()           # all layers in proper order
        self.tilesets = list()         # TiledTileset objects
        self.tile_properties = dict()  # tiles that have metadata
        self.layernames = dict()
        self.tiledgidmap = dict()  # mapping of tiledgid to pytmx gid

        self.gidmap = defaultdict(list)
        self.imagemap = dict()     # mapping of gid and trans flags to real gids
        self.imagemap[(0, 0)] = 0

        if filename:
            if filename.lower().endswith('tmx'):
                from . import util_xml
                util_xml.from_xml(filename, self)

    def __repr__(self):
        return '<{0}: "{1}">'.format(self.__class__.__name__, self.filename)

    def __iter__(self):
        """iterate over layers and objects in map
        """
        return chain(self.layers, self.objects)

    def reload_images(self):
        """Load the map images from disk

        :return: None
        """
        self.images = [None] * self.maxgid

        # load tile images used in layers
        for ts in self.tilesets:
            if ts.source is None:
                continue

            path = os.path.join(os.path.dirname(self.filename), ts.source)
            colorkey = getattr(ts, 'trans', None)
            loader = self.image_loader(path, colorkey)

            p = product(range(ts.margin,
                              ts.height + ts.margin - ts.tilewidth + 1,
                              ts.tileheight + ts.spacing),
                        range(ts.margin,
                              ts.width + ts.margin - ts.tileheight + 1,
                              ts.tilewidth + ts.spacing))

            for real_gid, (y, x) in enumerate(p, ts.firstgid):
                rect = (x, y, ts.tilewidth, ts.tileheight)
                gids = self._map_gid(real_gid)
                if gids is None:
                    if self.load_all_tiles or real_gid in self.optional_gids:
                        # TODO: handle flags? - might never be an issue, though
                        gids = [self._register_gid(real_gid, flags=0)]

                if gids:
                    for gid, flags in gids:
                        self.images[gid] = loader(rect, flags)

        # load image layer images
        for layer in (i for i in self.layers if isinstance(i, TiledImageLayer)):
            source = getattr(layer, 'source', None)
            if source:
                colorkey = getattr(layer, 'trans', None)
                real_gid = len(self.images)
                gid = self._register_gid(real_gid)
                layer.gid = gid
                path = os.path.join(os.path.dirname(self.filename), source)
                loader = self.image_loader(path, colorkey)
                image = loader()
                self.images.append(image)

        # load images in tiles.
        # instead of making a new gid, replace the reference to the tile that
        # was loaded from the tileset
        for real_gid, props in self.tile_properties.items():
            source = props.get('source', None)
            if source:
                colorkey = props.get('trans', None)
                path = os.path.join(os.path.dirname(self.filename), source)
                loader = self.image_loader(path, colorkey)
                image = loader()
                self.images[real_gid] = image

    def get_tile_image(self, x, y, layer_number):
        """Return the tile image for this location

        :param x: x coordinate
        :param y: y coordinate
        :param layer_number: layer number
        :rtype: surface if found, otherwise 0
        """
        return self.get_tile_image_by_gid(self.get_tile_gid(x, y, layer_number))

    def get_tile_image_by_gid(self, gid):
        """Return the tile image for this location

        :param gid: GID of image
        :rtype: surface if found, otherwise ValueError
        """
        self._verify_gid(gid)
        return self.images[gid]

    def get_tile_gid(self, x, y, layer_number):
        """Return the tile image GID for this location

        :param x: x coordinate
        :param y: y coordinate
        :param layer_number: layer number
        :rtype: surface if found, otherwise ValueError
        """
        return self._verify_tile_position(x, y, layer_number)

    def get_tile_properties(self, x, y, layer_number):
        """Return the tile image GID for this location

        :param x: x coordinate
        :param y: y coordinate
        :param layer_number: layer number
        :rtype: python dict if found, otherwise None
        """
        gid = self._verify_tile_position(x, y, layer_number)
        try:
            return self.tile_properties[gid]
        except (IndexError, ValueError):
            msg = "Coords: ({0},{1}) in layer {2} has invalid GID: {3}"
            logger.error(msg.format(x, y, layer_number, gid))
            raise Exception
        except KeyError:
            return None

    def get_tile_locations_by_gid(self, gid):
        """Search map for tile locations by the GID

        Not a fast operation

        :param gid: GID to be searched for
        :rtype: generator of tile locations
        """
        self._verify_gid(gid)

        p = product(range(self.width),
                    range(self.height),
                    range(len(self.layers)))

        return ((x, y, l) for (x, y, l) in p if
                self.layers[l].data[y][x] == gid)

    def get_tile_properties_by_gid(self, gid):
        """Get the tile properties of a tile GID

        :param gid: GID
        :rtype: python dict if found, otherwise None
        """
        self._verify_gid(gid)

        try:
            return self.tile_properties[gid]
        except KeyError:
            return None

    def set_tile_properties(self, gid, properties):
        """Set the tile properties of a tile GID

        :param gid: GID
        :param properties: python dict of properties for GID
        """
        self.tile_properties[gid] = properties

    def get_tile_properties_by_layer(self, layer_number):
        """Get the tile properties of each GID in layer

        :param layer_number: layer number
        :rtype: iterator of (gid, properties) tuples
        """
        layer = self._verify_layer_number(layer_number)
        p = product(range(self.width), range(self.height))

        for gid in set(layer.data[y][x] for x, y in p):
            try:
                yield gid, self.tile_properties[gid]
            except KeyError:
                continue

    def get_layer_by_name(self, name):
        """Return a layer by name

        :param name: Name of layer.  Case-sensitive.
        :rtype: Layer object if found, otherwise ValueError
        """
        try:
            return self.layernames[name]
        except KeyError:
            msg = 'Layer "{0}" not found.'
            logger.error(msg.format(name))
            raise ValueError

    def get_object_by_name(self, name):
        """Find an object

        :param name: Name of object.  Case-sensitive.
        :rtype: Object if found, otherwise ValueError
        """
        for obj in self.objects:
            if obj.name == name:
                return obj
        raise ValueError

    def get_tileset_from_gid(self, gid):
        """Return tileset that owns the gid

        Note: this is a slow operation, so if you are expecting to do this
              often, it would be worthwhile to cache the results of this.

        :param gid: gid of tile image
        :rtype: TiledTileset if found, otherwise ValueError
        """
        try:
            tiled_gid = self.tiledgidmap[gid]
        except KeyError:
            raise ValueError

        for tileset in sorted(self.tilesets, key=attrgetter('firstgid'),
                              reverse=True):
            if tiled_gid >= tileset.firstgid:
                return tileset

        raise ValueError

    @property
    def objectgroups(self):
        """Return iterator of all object groups

        :rtype: Iterator
        """
        return (layer for layer in self.layers
                if isinstance(layer, TiledObjectGroup))

    @property
    def objects(self):
        """Return iterator of all the objects associated with this map

        :rtype: Iterator
        """
        return chain(*self.objectgroups)

    @property
    def visible_layers(self):
        """Return iterator of Layer objects that are set 'visible'

        :rtype: Iterator
        """
        return (l for l in self.layers if l.visible)

    @property
    def visible_tile_layers(self):
        """Return iterator of layer indexes that are set 'visible'

        :rtype: Iterator
        """
        return (i for (i, l) in enumerate(self.layers)
                if l.visible and isinstance(l, TiledTileLayer))

    @property
    def visible_object_groups(self):
        """Return iterator of object group indexes that are set 'visible'

        :rtype: Iterator
        """
        return (i for (i, l) in enumerate(self.layers)
                if l.visible and isinstance(l, TiledObjectGroup))

    def _verify_layer_number(self, layer_number):
        """Verify that layer number is valid.  Returns layer object if true.

        :param layer_number: int
        :return: None
        """
        if layer_number < 0:
            msg = "Layer must be a positive integer.  Got {0} instead."
            logger.error(msg.format(layer_number))
            raise ValueError
        try:
            return self.layers[layer_number]
        except TypeError:
            msg = "Layer must be a positive integer.  Got {1} ({0}) instead."
            logger.error(msg.format(type(layer_number), layer_number))
            raise TypeError
        except IndexError:
            msg = "Layer index {0} is invalid."
            logger.error(msg.format(layer_number))
            raise ValueError

    def _verify_gid(self, gid):
        """Verify that GID is valid.

        :param gid: int
        :return: None
        """
        try:
            # test is if a number
            gid / 1

            if gid < 0:
                msg = "GIDs must not be less than zero.  Got: {0}"
                logger.error(msg.format(gid))
                raise ValueError
            elif gid > self.maxgid + 1:
                msg = "GID value is higher than number of tiles.  Got: {0}"
                logger.error(msg.format(gid))
                raise ValueError
        except TypeError:
            msg = "GIDs must be expressed as a number.  Got: {0}"
            logger.error(msg.format(gid))
            raise TypeError

    def _verify_tile_position(self, x, y, layer_number):
        """Verify tile position is valid, return GID if true, raise if not

        :param x: int
        :param y: int
        :param layer_number: int
        :return: int
        """
        try:
            if not (x >= 0 and y >= 0 and layer_number >= 0):
                raise ValueError

            try:
                return self.layers[layer_number].data[y][x]
            except IndexError:
                msg = "Coords: ({0},{1}) in layer {2} is invalid"
                logger.error(msg.format(x, y, layer_number))
                raise ValueError
        except TypeError:
            msg = "Coords must be expressed as an integer. Got: {0} {1} {2}"
            logger.error(msg.format(x, y, layer_number))
            raise TypeError

    def _register_gid(self, tiled_gid, flags=0):
        """Used to manage the mapping of GIDs between the tmx and pytmx

        :param tiled_gid: GID that is found in data
        :rtype: GID that pytmx uses for the the GID passed
        """
        if tiled_gid:
            try:
                return self.imagemap[(tiled_gid, flags)][0]
            except KeyError:
                gid = self.maxgid
                self.maxgid += 1
                self.imagemap[(tiled_gid, flags)] = (gid, flags)
                self.gidmap[tiled_gid].append((gid, flags))
                self.tiledgidmap[gid] = tiled_gid
                return gid

        else:
            return 0

    def _map_gid(self, tiled_gid):
        """Used to lookup a GID read from a Tiled map file's data

        :param tiled_gid: GID that is found in map data
        :rtype: (GID, flags) for the the GID passed, None if not found
        """
        try:
            return self.gidmap[int(tiled_gid)]
        except KeyError:
            return None
        except TypeError:
            msg = "GIDs must be an integer"
            logger.error(msg)
            raise TypeError


class TiledTileset(TiledElement):
    """ Represents a Tiled Tileset

    External tilesets are supported.  GID/ID's from Tiled are not guaranteed to
    be the same after loaded.
    """
    reserved = "image terraintypes tile".split()

    def __init__(self):
        TiledElement.__init__(self)
        self.tile_properties = dict()

        # defaults from the specification
        self.firstgid = 0
        self.source = None
        self.name = None
        self.tilewidth = 0
        self.tileheight = 0
        self.spacing = 0
        self.margin = 0
        self.trans = None
        self.width = 0
        self.height = 0
        self.offset = (0, 0)


class TiledTileLayer(TiledElement):
    """ Represents a TileLayer
    """
    def __init__(self):
        TiledElement.__init__(self)
        self.data = None

        # defaults from the specification
        self.name = None
        self.opacity = 1.0
        self.visible = True
        self.height = 0
        self.width = 0

    def __iter__(self):
        return self.iter_data()

    def iter_data(self):
        """Generator of data for the layer

        :return: Generator of (x, y, gid) tuples
        """
        for y, x in product(range(self.height), range(self.width)):
            yield x, y, self.data[y][x]

    def tiles(self):
        """Generator of visible tiles with images for the layer

        Images will be returned in the same format that was loaded with the map.
        Positions on the map without a tile image are skipped.

        :return: Generator of (x, y, image) tuples
        """
        images = self.parent.images
        data = self.data
        for y, x in product(range(self.height), range(self.width)):
            image = images[data[y][x]]
            if image:
                yield x, y, image


class TiledObject(TiledElement):
    """ Represents a any Tiled Object

    Supported types: Box, Ellipse, Tile Object, Polyline, Polygon
    """
    reserved = "ellipse polygon polyline image".split()

    def __init__(self):
        TiledElement.__init__(self)

        # defaults from the specification
        self.name = None
        self.type = None
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.rotation = 0
        self.gid = 0
        self.visible = 1

    @property
    def image(self):
        if self.gid:
            return self.parent.images[self.gid]
        return None


class TiledObjectGroup(TiledElement, list):
    """ Represents a Tiled ObjectGroup

    Supports any operation of a normal list.
    """
    reserved = ["object"]

    def __init__(self):
        TiledElement.__init__(self)

        # defaults from the specification
        self.name = None
        self.color = None
        self.opacity = 1
        self.visible = 1


class TiledImageLayer(TiledElement):
    """ Represents Tiled Image Layer
    """
    reserved = ["image"]

    def __init__(self):
        TiledElement.__init__(self)
        self.source = None
        self.trans = None
        self.gid = 0

        # defaults from the specification
        self.name = None
        self.opacity = 1
        self.visible = 1

    @property
    def image(self):
        if self.gid:
            return self.parent.images[self.gid]
        return None
