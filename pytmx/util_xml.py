import struct
import array
import logging
import os.path
import six.moves
from six.moves import zip
from six.moves import map
from itertools import product
from collections import OrderedDict
from collections import namedtuple
from collections import defaultdict
from xml.etree import ElementTree

from pytmx import *

__all__ = ['parse_map',
           'parse_tileset',
           'parse_layer',
           'parse_objectgroup',
           'parse_object',
           'parse_imagelayer',
           'parse_properties',
           'from_xml']

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)


def convert_to_bool(text):
    # properly convert strings to a bool
    try:
        return bool(int(text))
    except:
        pass

    text = str(text).lower()
    if text == "true":
        return True
    if text == "yes":
        return True
    if text == "false":
        return False
    if text == "no":
        return False

    raise ValueError

# used to change the unicode string returned from xml to proper python types.
types = defaultdict(lambda: str)
types.update({
    "version": float,
    "orientation": str,
    "width": int,
    "height": int,
    "tilewidth": int,
    "tileheight": int,
    "firstgid": int,
    "source": str,
    "name": str,
    "spacing": int,
    "margin": int,
    "trans": str,
    "id": int,
    "opacity": float,
    "visible": convert_to_bool,
    "encoding": str,
    "compression": str,
    "gid": int,
    "type": str,
    "x": float,
    "y": float,
    "value": str,
    "rotation": float,
})

# internal flags
TRANS_FLIPX = 1
TRANS_FLIPY = 2
TRANS_ROT = 4

# Tiled gid flags
GID_TRANS_FLIPX = 1 << 31
GID_TRANS_FLIPY = 1 << 30
GID_TRANS_ROT = 1 << 29

flag_names = (
    'flipped_horizontally',
    'flipped_vertically',
    'flipped_diagonally',)

TileFlags = namedtuple('TileFlags', flag_names)


def from_xml(filename, tiled_map):
    etree = ElementTree.parse(filename).getroot()
    parse_map(etree, tiled_map)


def handle_image_node(node):
    """Return dict that describes the image defined in the node

    :param node: ElementTree node
    :return: dictionary that describes the image
    """
    d = dict()
    d['source'] = node.get('source')
    d['trans'] = node.get('trans', None)
    d['width'] = int(node.get('width'))
    d['height'] = int(node.get('height'))
    return d


def decode_gid(raw_gid):
    """Decode a GID from data

    as of 0.7.0 it determines if the tile should be flipped when rendered
    as of 0.8.0 bit 30 determines if GID is rotated

    :param raw_gid: 32-bit number from layer data
    :return: gid, flags
    """
    flags = TileFlags(
        raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX,
        raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY,
        raw_gid & GID_TRANS_ROT == GID_TRANS_ROT)
    gid = raw_gid & ~(GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT)
    return gid, flags


def parse_properties(node):
    """Parse a node and return a dict that represents a tiled "property"

    the "properties" from tiled's tmx have an annoying quality that "name"
    and "value" is included. here we mangle it to get that junk out.
    """
    d = dict()
    for child in node.iterfind('properties'):
        for subnode in child.iterfind('property'):
            d[subnode.get('name')] = subnode.get('value')
    return d


def cast_and_set_attributes_from_node_items(object_, items):
    for key, value in items:
        casted_value = types[key](value)
        setattr(object_, key, casted_value)


def contains_invalid_property_name(object_, items):
    for k, v in items:
        if hasattr(object_, k):
            msg = '{0} "{1}" has a property called "{2}"'
            logger.error(msg.format(object_.__class__.__name__, object_, k,
                                    object_.__class__.__name__))
            return True

        if object_.reserved is not None:
            if k in object_.reserved:
                return True

    return False


def set_properties(object_, node):
    """
    read the xml attributes and tiled "properties" from a xml node and fill
    in the values into the object's dictionary.  Names will be checked to
    make sure that they do not conflict with reserved names.
    """
    cast_and_set_attributes_from_node_items(object_, node.items())
    properties = parse_properties(node)
    if contains_invalid_property_name(object_, properties.items()):
        msg = "This name(s) is reserved for {0} objects and cannot be used."
        logger.error(msg.format(object_.__class__.__name__))
        logger.error("Please change the name(s) in Tiled and try again.")
        raise ValueError

    object_.properties = properties


def parse_map(node, tiled_map=None):
    """Parse a map from ElementTree xml node

    :param node: ElementTree xml node
    :return: TiledMap Instance
    """
    if tiled_map is None:
        tiled_map = TiledMap()
    set_properties(tiled_map, node)
    tiled_map.background_color = node.get('backgroundcolor', None)

    # ***         do not change this load order!         *** #
    # ***    gid mapping errors will occur if changed    *** #

    for subnode in node.findall('layer'):
        layer = parse_layer(subnode, tiled_map)
        tiled_map.layernames[layer.name] = layer
        tiled_map.layers.append(layer)
    for subnode in node.findall('imagelayer'):
        tiled_map.layers.append(parse_imagelayer(subnode, tiled_map))
    for subnode in node.findall('objectgroup'):
        tiled_map.layers.append(parse_objectgroup(subnode, tiled_map))
    for subnode in node.findall('tileset'):
        tiled_map.tilesets.append(parse_tileset(subnode, tiled_map))

    # for o in [o for o in tiled_map.objects if o.gid]:
    #     # gid/tile properties are defined in the tileset, but also apply
    #     # to objects, sometimes.  here we get the gid/tile props and update them
    #     p = tiled_map.get_tile_properties_by_gid(o.gid)
    #     if p:
    #         o.properties.update(p)
    #
    #     # tiled stores the origin of GID objects by the lower right corner
    #     # this is different for all other types, so is is flipped here
    #     try:
    #         tileset = tiled_map.get_tileset_from_gid(o.gid)
    #     except ValueError:
    #         msg = 'attempted to lookup invalid gid %s in object %s'
    #         logger.error(msg, o.gid, o)
    #     else:
    #         if tiled_map.invert_y:
    #             o.y -= tileset.tileheight
    #         o.height = tileset.tileheight
    #         o.width = tileset.tilewidth

    tiled_map.reload_images()
    return tiled_map


def parse_objectgroup(node, parent):
    """Parse an Object Group from ElementTree xml node

    :param node: ElementTree xml node
    :return: TiledObjectGroup Instance
    """
    og = TiledObjectGroup()
    set_properties(og, node)
    for child in node.iterfind('object'):
        object_ = parse_object(child)
        og.append(object_)

    return og


def parse_tileset(node, parent):
    """Parse a Tileset from ElementTree xml node

    A bit of mangling is done to allow tilesets with external TSX files

    :param node: ElementTree xml node
    :return: TiledTileset Instance
    """
    tileset = TiledTileset()

    # if true, then node references an external tileset
    source = node.get('source', None)
    if source:
        if source[-4:].lower() == ".tsx":

            # external tilesets don't save the gid, store it for later
            tileset.firstgid = int(node.get('firstgid'))

            # we need to mangle the path b/c tiled stores relative paths
            dirname = os.path.dirname(parent.filename)
            path = os.path.abspath(os.path.join(dirname, source))
            try:
                node = ElementTree.parse(path).getroot()
            except IOError:
                msg = "Cannot load external tileset: {0}"
                logger.error(msg.format(path))
                raise Exception

        else:
            msg = "Found external tileset, but cannot handle type: {0}"
            logger.error(msg.format(tileset.source))
            raise Exception

    set_properties(tileset, node)

    for child in node.getiterator('tile'):
        p = parse_properties(child)
        tiled_gid = int(child.get("id"))

        # handle tiles that have their own image
        image_node = child.get('image', None)
        if image_node:
            p.update(handle_image_node(image_node))
        else:
            p['width'] = tileset.tilewidth
            p['height'] = tileset.tileheight

        tileset.tile_properties[tiled_gid] = p

    # handle the optional 'tileoffset' node
    offset = node.find('tileoffset')
    if offset:
        tileset.offset = (offset.get('x', 0), offset.get('y', 0))
    else:
        tileset.offset = (0, 0)

    image_node = node.find('image')
    if image_node is not None:
        for k, v in handle_image_node(image_node).items():
            setattr(tileset, k, v)

    return tileset


def parse_layer(node, parent):
    """Parse a Tile Layer from ElementTree xml node

    :param node: ElementTree xml node
    :return: TiledTileLayer Instance
    """
    layer = TiledTileLayer()
    set_properties(layer, node)
    data = None
    next_gid = None
    data_node = node.find('data')

    encoding = data_node.get('encoding', None)
    if encoding == 'base64':
        from base64 import b64decode
        data = b64decode(data_node.text.strip())

    elif encoding == 'csv':
        next_gid = map(int, "".join(
            line.strip() for line in data_node.text.strip()
        ).split(","))

    elif encoding:
        msg = 'encoding type: {0} is not supported.'
        logger.error(msg.format(encoding))
        raise Exception

    compression = data_node.get('compression', None)
    if compression == 'gzip':
        import gzip
        with gzip.GzipFile(fileobj=six.BytesIO(data)) as fh:
            data = fh.read()

    elif compression == 'zlib':
        import zlib
        data = zlib.decompress(data)

    elif compression:
        msg = 'compression type: {0} is not supported.'
        logger.error(msg.format(compression))
        raise Exception

    # if data is None, then it was not decoded or decompressed, so
    # we assume here that it is going to be a bunch of tile elements
    # TODO: this will/should raise an exception if there are no tiles
    if encoding == next_gid is None:
        def get_children(parent):
            for child in parent.iterfind('tile'):
                yield int(child.get('gid'))

        next_gid = get_children(data_node)

    elif data:
        if type(data) == bytes:
            fmt = struct.Struct('<L')
            iterator = (data[i:i + 4] for i in range(0, len(data), 4))
            next_gid = (fmt.unpack(i)[0] for i in iterator)
        else:
            msg = 'layer data not in expected format ({0})'
            logger.error(msg.format(type(data)))
            raise Exception

    init = lambda: [0] * layer.width

    # H (16-bit) may be a limitation for very detailed maps
    layer.data = tuple(array.array('H', init()) for i in range(layer.height))
    for (y, x) in product(range(layer.height), range(layer.width)):
        layer.data[y][x] = parent._register_gid(*decode_gid(next(next_gid)))

    return layer


def parse_object(node):
    """Parse an Object from ElementTree xml node

    :param node: ElementTree xml node
    :return: TiledObject Instance
    """

    def read_points(text):
        """parse a text string of float tuples and return [(x,...),...]
        """
        return tuple(tuple(map(float, i.split(','))) for i in text.split())

    object_ = TiledObject()
    set_properties(object_, node)

    points = None
    polygon = node.find('polygon')
    if polygon is not None:
        points = read_points(polygon.get('points'))
        object_.closed = True

    polyline = node.find('polyline')
    if polyline is not None:
        points = read_points(polyline.get('points'))
        object_.closed = False

    if points:
        x1 = x2 = y1 = y2 = 0
        for x, y in points:
            if x < x1: x1 = x
            if x > x2: x2 = x
            if y < y1: y1 = y
            if y > y2: y2 = y
        object_.width = abs(x1) + abs(x2)
        object_.height = abs(y1) + abs(y2)
        object_.points = tuple(
            [(i[0] + object_.x, i[1] + object_.y) for i in points])

    return object_


def parse_imagelayer(node, parent):
    """Parse an Image Layer from ElementTree xml node

    :param node: ElementTree xml node
    :return: TiledImageLayer instance
    """
    image_layer = TiledImageLayer()
    set_properties(image_layer, node)
    image_layer.name = node.get('name', None)
    image_layer.opacity = node.get('opacity', image_layer.opacity)
    image_layer.visible = node.get('visible', image_layer.visible)
    image_node = node.find('image')
    image_layer.source = image_node.get('source')
    image_layer.trans = image_node.get('trans', None)
    return image_layer
