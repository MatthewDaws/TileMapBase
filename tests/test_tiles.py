import pytest
import unittest.mock as mock
import os, shutil
import PIL.Image
import datetime

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

def test_Cache():
    cache_mock = mock.Mock()
    tile_cache_test = tiles.Cache(cache_mock)
    assert tile_cache_test.make_request_string("SPAM",1,2,3) == "SPAM#1#2#3"
    assert tile_cache_test.split_request_string("SPAM#5#6#77") == ("SPAM", 5, 6, 77)

    data = tile_cache_test.get_from_cache(("SPAM", 6, 3, 12))
    cache_mock.get_from_cache.assert_called_with("SPAM#6#3#12")
    assert data is cache_mock.get_from_cache.return_value

    with pytest.raises(NotImplementedError):
        tile_cache_test.place_in_cache("", None)

    cache_mock.query.return_value = [("SPAM#2#5#32", "eggs")]
    data = tile_cache_test.query()
    cache_mock.query.assert_called_with()
    assert data == [(("SPAM", 2, 5, 32), "eggs")]

    tile_cache_test.remove(("SPAM", 6, 3, 12))
    cache_mock.remove.assert_called_with("SPAM#6#3#12")
    
@pytest.fixture
def dumpdir():
    name = "test_dump_dir"
    try:
        shutil.rmtree(name)
    except:
        pass
    try:
        os.mkdir(name)
    except:
        pass
    yield name
    try:
        shutil.rmtree(name)
    except:
        pass

def test_Cache_dump(dumpdir):
    cache_mock = mock.Mock()
    tile_cache_test = tiles.Cache(cache_mock)
    cache_mock.query.return_value = [
        ("ONE#1#2#5", None),
        ("ONE#1#3#5", None),
        ("ONE#4#5#6", None),
        ("TWO#1#2#5", None)
        ]
    def get_data(key):
        if key == "ONE#1#2#5":
            return (b"\x89PNG", None)
        elif key == "ONE#1#3#5":
            return (b"123456JFIF", None)
        elif key == "ONE#4#5#6":
            return (b"asdfhgsdgjsdhjkg", None)
        elif key == "TWO#1#2#5":
            return (b"asdfhgsdgjsdhjkg", None)
        else:
            raise AssertionError()
    cache_mock.get_from_cache.side_effect = get_data
    tile_cache_test.dump(dumpdir)
    assert set( os.listdir(dumpdir) ) == {"ONE", "TWO"}
    assert set( os.listdir(os.path.join(dumpdir, "ONE")) ) == {"5", "6"}
    assert set( os.listdir(os.path.join(dumpdir, "ONE", "5")) ) == {"1_2.png", "1_3.jpg"}
    assert set( os.listdir(os.path.join(dumpdir, "ONE", "6")) ) == {"4_5"}
    assert set( os.listdir(os.path.join(dumpdir, "TWO")) ) == {"5"}
    assert set( os.listdir(os.path.join(dumpdir, "TWO", "5")) ) == {"1_2"}

def test_Cache_dump_must_be_empty(dumpdir):
    cache_mock = mock.Mock()
    tile_cache_test = tiles.Cache(cache_mock)

    with open(os.path.join(dumpdir, "matt.txt"), "w") as f:
        f.write("Nope")

    with pytest.raises(Exception):
        tile_cache_test.dump(dumpdir)
    
def test_Cache_clean():
    cache_mock = mock.Mock()
    tile_cache_test = tiles.Cache(cache_mock)

    cache_mock.query.return_value = [
        ("ONE#1#2#5", datetime.datetime(2017,5,6)),
        ("ONE#1#3#5", datetime.datetime(2017,5,5)),
        ("ONE#4#5#6", datetime.datetime(2017,5,4,12,30)),
        ("TWO#1#2#5", datetime.datetime(2017,5,4))
        ]
    tile_cache_test.clean(datetime.datetime(2017,5,4,12,30,1))

    cache_mock.remove.call_args_list == [
        mock.call("ONE#4#5#6"), mock.call("TWO#1#2#5") ]
