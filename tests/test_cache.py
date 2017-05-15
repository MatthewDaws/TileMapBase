import pytest
import unittest.mock as mock
import datetime, sqlite3, os

import tilemapbase.cache as cache

class CacheTest(cache.Cache):
    def __init__(self):
        self.executor_mock = mock.MagicMock()
        super().__init__(self.executor_mock)
        self.get = None
        self.gets = []
        self.placed = []

    def _get_from_cache(self, str_request):
        self.gets.append(str_request)
        return self.get

    def _place_in_cache(self, str_request, obj_as_bytes):
        self.placed.append((str_request, obj_as_bytes))

def test_Cache_notInCache_requests():
    c = CacheTest()
    c.fetch("spam")
    c.executor_mock.fetch.assert_called_with("spam")

@pytest.fixture()
def cache_test():
    c = CacheTest()
    obj_expected = bytes([1,2,12,18])
    c.executor_mock.fetch.return_value = obj_expected
    return c

def test_Cache_notInCache_places(cache_test):
    obj = cache_test.fetch("spam")
    assert( obj == cache_test.executor_mock.fetch.return_value )
    assert( cache_test.placed == [("spam", cache_test.executor_mock.fetch.return_value)] )

def test_Cache_inCacheDoesntRequest(cache_test):
    cache_test.get = (cache_test.executor_mock.fetch.return_value, None)

    obj = cache_test.fetch("spam")
    assert( obj == cache_test.executor_mock.fetch.return_value )
    assert( cache_test.gets == ["spam"] )
    assert( cache_test.placed == [] )

def test_Cache_withTimeout(cache_test):
    cache_test.expire_time = datetime.timedelta(days=1)
    now = datetime.datetime(2016,4,10,12,30)
    cache_test.get = (cache_test.executor_mock.fetch.return_value, now)
    
    with mock.patch("datetime.datetime") as datetime_mock:
        datetime_mock.now.return_value = now
        obj = cache_test.fetch("spam")
        assert( cache_test.gets == ["spam"] )
        assert( cache_test.placed == [] )

def test_Cache_withTimeout_doesExpire(cache_test):
    cache_test.expire_time = datetime.timedelta(days=1)
    now = datetime.datetime(2016,4,10,12,30)
    cache_test.get = (cache_test.executor_mock.fetch.return_value, now)
    
    with mock.patch("datetime.datetime") as datetime_mock:
        datetime_mock.now.return_value = now + datetime.timedelta(days=1, minutes=1)
        obj = cache_test.fetch("spam")
        assert( cache_test.gets == ["spam"] )
        assert( cache_test.placed == [("spam", cache_test.executor_mock.fetch.return_value)] )

def test_time_patch():
    now = datetime.datetime(2016,4,10,12,30)
    with mock.patch("datetime.datetime") as datetime_mock:
        datetime_mock.now.return_value = now
        c = cache.Cache(None)
        assert( str(c.time()) == "2016-04-10 12:30:00" )


class ExecutorTest(cache.Executor):
    def __init__(self):
        self.answer = None
    
    def fetch(self, request):
        return self.answer


@pytest.fixture
def db_cache():
    try:
        c = cache.SQLiteCache(ExecutorTest(), "test.db")
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

def test_sqcache_create(db_cache):
    assert(db_cache._get_from_cache("spam") is None)

    now = datetime.datetime(2016,4,10,12,30)
    strftime = datetime.datetime.strftime
    strptime = datetime.datetime.strptime
    with mock.patch("datetime.datetime") as datetime_mock:
        datetime_mock.now.return_value = now
        datetime_mock.strftime = strftime
        datetime_mock.strptime = strptime
        db_cache._place_in_cache("spam", b"eggs")
        db_cache._place_in_cache("spam1", b"eggs1")
        assert(db_cache._get_from_cache("spam") == (b"eggs", now))
        assert(db_cache._get_from_cache("spam1") == (b"eggs1", now))
