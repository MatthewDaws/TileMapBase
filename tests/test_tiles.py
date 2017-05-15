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

    dbexists.assert_called()
    name = dbexists.call_args[0][0]
    cache.assert_called_with(None, name)

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

@mock.patch("tilemapbase.tiles._get_cache")
def test_Tiles(cache, image):
    cache.return_value = mock.MagicMock()
    cache.return_value.fetch.return_value = image

    t = tiles.Tiles("example{}/{}/{}.jpg", "TEST")
    x = t.get_tile(10,20,5)

    assert(cache.return_value.fetch.call_args[0][0] == "TEST#10#20#5")
    assert(x.width == 256)
    assert(x.height == 256)

@mock.patch("requests.get")
@mock.patch("tilemapbase.tiles._get_cache")
def test_TilesExecutor(cache, get):
    t = tiles.Tiles("example{zoom}/{x}/{y}.jpg", "TEST")
    te = tiles._TilesExecutor(t)

    te.fetch("TEST#10#20#5")

    assert(get.call_args[0][0] == "example5/10/20.jpg")

@mock.patch("requests.get")
@mock.patch("tilemapbase.tiles._get_cache")
def test_OSM(cache, get):
    tiles.OSM._get_cache().executor.fetch("OSM#5#10#20")

    assert(get.call_args[0][0] == "http://a.tile.openstreetmap.org/20/5/10.png")
