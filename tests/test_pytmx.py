"""
some tests for pytmx

WIP - all code that isn't abandoned is WIP
"""
import os.path
from itertools import repeat
from unittest import TestCase
from mock import Mock, MagicMock
from mock import patch

import pytmx
import pytmx.util_xml
from pytmx.util_xml import convert_to_bool
from pytmx.util_xml import contains_invalid_property_name
from pytmx.util_xml import cast_and_set_attributes_from_node_items
from pytmx import TiledElement, TiledMap


class TiledMapTest(TestCase):
    filename = os.path.join('tests', 'test01.tmx')

    def setUp(self):
        self.m = pytmx.TiledMap(self.filename)

    def test_import_pytmx_doesnt_import_pygame(self):
        import pytmx
        import sys
        self.assertTrue('pygame' not in sys.modules)

    def test_get_tile_image_valid(self):
        # just run and hope exceptions are not raised
        self.m.get_tile_image(0, 0, 0)

    def test_get_tile_image_invalid(self):
        with self.assertRaises(ValueError):
            self.m.get_tile_image(-1, -1, -1)
        with self.assertRaises(ValueError):
            self.m.get_tile_image(99999, 99999, 99999)
        with self.assertRaises(TypeError):
            self.m.get_tile_image('a', 'a', 'a')

    def test_get_tile_image_by_gid_valid(self):
        image = self.m.get_tile_image_by_gid(1)
        self.assertIsNotNone(image)

    def test_get_tile_image_by_gid_invalid(self):
        with self.assertRaises(ValueError):
            self.m.get_tile_image_by_gid(-1)
        with self.assertRaises(ValueError):
            self.m.get_tile_image_by_gid(99999)
        with self.assertRaises(TypeError):
            self.m.get_tile_image_by_gid('a')

    def test_get_tile_image_by_gid_zero(self):
        image = self.m.get_tile_image_by_gid(0)
        self.assertIsNone(image)

    def test_get_tile_gid_valid(self):
        # just run and hope exceptions are not raised
        self.m.get_tile_gid(0, 0, 0)

    def test_get_tile_gid_invalid(self):
        with self.assertRaises(ValueError):
            self.m.get_tile_gid(-1, -1, -1)
        with self.assertRaises(ValueError):
            self.m.get_tile_gid(99999, 99999, 99999)
        with self.assertRaises(TypeError):
            self.m.get_tile_gid('a', 'a', 'a')

    def test_get_layer_by_name_valid(self):
        # just run and hope exceptions are not raised
        self.m.get_layer_by_name("Grass and Water")

    def test_get_layer_by_name_invalid(self):
        with self.assertRaises(ValueError):
            self.m.get_layer_by_name("spam and eggs")
        with self.assertRaises(ValueError):
            self.m.get_layer_by_name(123)

    def test_get_object_by_name_valid(self):
        # just run and hope exceptions are not raised
        self.m.get_object_by_name("Castle")

    def test_get_object_by_name_invalid(self):
        with self.assertRaises(ValueError):
            self.m.get_object_by_name("just spam and no eggs")
        with self.assertRaises(ValueError):
            self.m.get_object_by_name(123)

    def test_get_tile_properties_by_gid_valid(self):
        expected = {'name': 'grass'}
        value = self.m.get_tile_properties_by_gid(17)
        self.assertEqual(expected, value)

    def test_get_tile_properties_by_gid_invalid(self):
        value = self.m.get_tile_properties_by_gid(0)
        self.assertIsNone(value)

    def test_verify_tile_position_valid(self):
        # just run and hope exceptions are not raised
        self.m._verify_tile_position(0, 0, 0)

    def test_verify_tile_position_invalid(self):
        with self.assertRaises(ValueError):
            self.m._verify_tile_position(-1, -1, -1)
        with self.assertRaises(ValueError):
            self.m._verify_tile_position(99999, 99999, 99999)
        with self.assertRaises(TypeError):
            self.m._verify_tile_position('a', 'a', 'a')

    def test_verify_gid_valid(self):
        # just run and hope exceptions are not raised
        self.m._verify_gid(0)
        self.m._verify_gid(1)

    def test_verify_gid_invalid(self):
        with self.assertRaises(ValueError):
            self.m._verify_gid(-1)
        with self.assertRaises(ValueError):
            self.m._verify_gid(99999)
        with self.assertRaises(TypeError):
            self.m._verify_gid('a')

    def test_verify_layer_number_valid(self):
        # just run and hope exceptions are not raised
        self.m._verify_layer_number(0)

    def test_verify_layer_number_invalid(self):
        with self.assertRaises(ValueError):
            self.m._verify_layer_number(-1)
        with self.assertRaises(ValueError):
            self.m._verify_layer_number(99999)
        with self.assertRaises(TypeError):
            self.m._verify_layer_number('a')


class handle_bool_TestCase(TestCase):

    def test_when_passed_true_it_should_return_true(self):
        self.assertTrue(convert_to_bool("true"))

    def test_when_passed_yes_it_should_return_true(self):
        self.assertTrue(convert_to_bool("yes"))

    def test_when_passed_false_it_should_return_false(self):
        self.assertFalse(convert_to_bool("false"))

    def test_when_passed_no_it_should_return_false(self):
        self.assertFalse(convert_to_bool("no"))

    def test_when_passed_zero_it_should_return_false(self):
        self.assertFalse(convert_to_bool("0"))

    def test_when_passed_non_zero_it_should_return_true(self):
        self.assertTrue(convert_to_bool("1337"))

    def test_when_passed_garbage_it_should_raise_value_error(self):
        with self.assertRaises(ValueError):
            convert_to_bool("garbage")

    def test_when_passed_None_it_should_raise_value_error(self):
        with self.assertRaises(ValueError):
            convert_to_bool(None)


class TiledElementTestCase(TestCase):

    def test_when_property_is_reserved_contains_invalid_property_name_returns_true(self):
        element = Mock(spec=TiledElement, autospec=True)
        element.name = 'foo'
        element._reserved = ['foo', 'foo_bar']

        # test reserved
        items = zip(element._reserved, repeat(None))
        self.assertTrue(contains_invalid_property_name(element, items))

        # test if attribute is already set (name)
        items = (('name', None),)
        self.assertTrue(contains_invalid_property_name(element, items))

    def test_when_property_is_not_reserved_contains_invalid_property_name_returns_false(self):
        element = MagicMock()
        self.assertFalse(contains_invalid_property_name(element, list()))

    @patch("pytmx.util_xml.contains_invalid_property_name")
    def test_set_properties_raises_value_error_if_invalid_property_name_in_node(self, mock_parse_properties):
        mock_parse_properties.return_value = True
        element = MagicMock()
        mock_node = MagicMock()
        mock_node.items.return_value = list()
        with self.assertRaises(ValueError):
            pytmx.util_xml.set_properties(element, mock_node)

    def test_repr(self):
        element = TiledElement()
        element.name = "Foo"
        self.assertEqual("<TiledElement: \"Foo\">", element.__repr__())
