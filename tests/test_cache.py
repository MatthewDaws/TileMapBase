import pytest
import unittest.mock as mock
import datetime, sqlite3, os

import tilemapbase.cache as cache

class CacheTest(cache.ConcreteCache):
    def __init__(self):
        self.get = None
        self.gets = []
        self.placed = []

    def get_from_cache(self, str_request):
        self.gets.append(str_request)
        return self.get

    def place_in_cache(self, str_request, obj_as_bytes):
        self.placed.append((str_request, obj_as_bytes))

@pytest.fixture()
def cache_test():
    executor = mock.MagicMock()
    concrete_cache = mock.MagicMock()
    c = cache.Cache(executor, concrete_cache)
    obj_expected = bytes([1,2,12,18])
    executor.fetch.return_value = obj_expected
    concrete_cache.get_from_cache.return_value = None
    return c, executor, concrete_cache, obj_expected

def test_Cache_notInCache_requests(cache_test):
    c, executor, _, _ = cache_test
    c.fetch("spam")
    executor.fetch.assert_called_with("spam")

def test_Cache_notInCache_places(cache_test):
    c, executor, ccache, expected_obj = cache_test
    obj = c.fetch("spam")
    assert( obj == expected_obj )
    ccache.place_in_cache.assert_called_with("spam", expected_obj)

def test_Cache_inCacheDoesntRequest(cache_test):
    c, executor, ccache, expected_obj = cache_test
    ccache.get_from_cache.return_value = (expected_obj, None)
    obj = c.fetch("spam")
    assert( obj == expected_obj )
    assert( executor.fetch.call_count == 0 )

def test_Cache_withTimeout(cache_test):
    c, executor, ccache, expected_obj = cache_test
    c.expire_time = datetime.timedelta(days=1)
    now = datetime.datetime(2016,4,10,12,30)
    ccache.get_from_cache.return_value = (expected_obj, now)
    
    with mock.patch("datetime.datetime") as datetime_mock:
        datetime_mock.now.return_value = now
        obj = c.fetch("spam")
        assert( executor.fetch.call_count == 0 )
        assert( obj == expected_obj )

def test_Cache_withTimeout_doesExpire(cache_test):
    c, executor, ccache, expected_obj = cache_test
    c.expire_time = datetime.timedelta(days=1)
    now = datetime.datetime(2016,4,10,12,30)
    ccache.get_from_cache.return_value = (expected_obj, now)
    
    with mock.patch("datetime.datetime") as datetime_mock:
        datetime_mock.now.return_value = now + datetime.timedelta(days=1, minutes=1)
        obj = c.fetch("spam")
        executor.fetch.assert_called_with("spam")
        ccache.place_in_cache.assert_called_with("spam", expected_obj)


@pytest.fixture
def db_cache():
    try:
        c = cache.SQLiteCache("test.db")
        try:
            yield c
        finally:
            c.close()
    finally:
        try:
            os.remove("test.db")
        except Exception:
            pass

def test_database_exists():
    try:
        assert( cache.database_exists("test.db") == False )

        sqlite3.connect("test.db")
        assert( cache.database_exists("test.db") == False )

        conn = sqlite3.connect("test.db")
        conn.execute("CREATE table cache (name)")
        conn.execute("CREATE table other (thing)")
        conn.close()
        assert( cache.database_exists("test.db") == True )
    finally:
        os.remove("test.db")

def test_sqcache_emplace(db_cache):
    assert(db_cache.get_from_cache("spam") is None)

    now = datetime.datetime(2016,4,10,12,30)
    strftime = datetime.datetime.strftime
    strptime = datetime.datetime.strptime
    with mock.patch("datetime.datetime") as datetime_mock:
        datetime_mock.now.return_value = now
        datetime_mock.strftime = strftime
        datetime_mock.strptime = strptime
        db_cache.place_in_cache("spam", b"eggs")
        db_cache.place_in_cache("spam1", b"eggs1")
        assert(db_cache.get_from_cache("spam") == (b"eggs", now))
        assert(db_cache.get_from_cache("spam1") == (b"eggs1", now))

def test_sqcache_query(db_cache):
    assert db_cache.query() == []

    now = datetime.datetime.now()
    db_cache.place_in_cache("spam", b"eggs")
    
    q = db_cache.query()
    assert len(q) == 1
    assert q[0][0] == "spam"
    assert abs((q[0][1] - now).total_seconds()) < 1

    db_cache.place_in_cache("spam1", b"eggs")
    q = db_cache.query()
    assert len(q) == 2
    assert set(name for name, _ in q) == {"spam", "spam1"}

def test_sqcache_update(db_cache):
    db_cache.place_in_cache("spam", b"eggs")
    q = db_cache.query()
    assert len(q) == 1
    assert q[0][0] == "spam"

    db_cache.place_in_cache("spam", b"eggs")
    q = db_cache.query()
    assert len(q) == 1
    assert q[0][0] == "spam"

def test_sqcache_remove(db_cache):
    db_cache.place_in_cache("spam", b"eggs")
    db_cache.place_in_cache("spam1", b"eggs")
    assert len(db_cache.query()) == 2

    db_cache.remove("spam")
    q = db_cache.query()
    assert len(q) == 1
    assert q[0][0] == "spam1"
