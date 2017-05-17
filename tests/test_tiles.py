import pytest
import unittest.mock as mock
import os
import PIL.Image

import tilemapbase.tiles as tiles

@mock.patch("tilemapbase.cache.database_exists")
@mock.patch("tilemapbase.cache.SQLiteCache")
def test_init(cache, dbexists):
    tiles._sqcache = None
    tiles.init()

    assert( dbexists.called )
    name = dbexists.call_args[0][0]
    cache.assert_called_with(name)

@mock.patch("tilemapbase.cache.database_exists")
@mock.patch("tilemapbase.cache.SQLiteCache")
def test_init_throws(cache, dbexists):
    dbexists.return_value = False
    tiles._sqcache = None
    with pytest.raises(Exception):
        tiles.init()
    with pytest.raises(Exception):
        tiles._get_cache()

@pytest.fixture
def image():
    filename = os.path.join("notebooks", "test.jpg")
    with open(filename, "br") as f:
        return f.read()

import collections
Response = collections.namedtuple("Response", ["ok", "content"])

@mock.patch("tilemapbase.tiles._sqcache")
@mock.patch("requests.get")
def test_Tiles(get, sqcache, image):
    sqcache.get_from_cache.return_value = None
    get.return_value = Response(True, image)

    t = tiles.Tiles("example{zoom}/{x}/{y}.jpg", "TEST")
    x = t.get_tile(10,20,5)

    assert(x.width == 256)
    assert(x.height == 256)
    assert(get.call_args[0][0] == "example5/10/20.jpg")
    assert(sqcache.place_in_cache.call_args[0][0] == "TEST#10#20#5")

@mock.patch("tilemapbase.tiles._sqcache")
@mock.patch("requests.get")
def test_OSM(get, sqcache):
    sqcache.get_from_cache.return_value = None
    get.return_value = Response(True, None)

    tiles.OSM.get_tile(5,10,20)

    assert(get.call_args[0][0] == "http://a.tile.openstreetmap.org/20/5/10.png")
