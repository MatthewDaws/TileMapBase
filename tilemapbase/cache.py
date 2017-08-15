"""
cache
~~~~~

Provides a base class for caching objects which are associated with a "request"
object.  Concrete implementation using a sqlite database.

A "request" object is simply any object such that `str(obj)` returns a unique
identifier of the request.  Any object which can be converted to `bytes` by
`bytes(obj)` can be cached (and will be returned as a `bytes` object).
"""

import datetime as _datetime
import sqlite3 as _sqlite3
import os as _os
from . import utils as _utils

class Executor():
    """A base class for executing a request, if the cache does not already have
    access to the object requested.  Any class with this interface will work.
    """

    def fetch(self, request):
        """Attempt to fetch the request, returning an object (typically a
        :class:`bytes` instance, or object which can be converted to
        :class:`bytes`).  May return `None` or raise an exception on failure.
        """
        raise NotImplementedError()


class ConcreteCache():
    """Abstract base class for a class which implements storing and retrieving
    objects.  Each object should be timestamped with its last update time.
    """
    def get_from_cache(self, str_request):
        """Return `None` on failure to find.
        
        :return: Pair of (object, last_update_time)
        """
        raise NotImplementedError()

    def place_in_cache(self, str_request, obj_as_bytes):
        """Write the object to the cache.  Should use the current time when
        storing the "last update time"."""
        raise NotImplementedError()

    def query(self):
        """List all `str_request` objects which are in the cache.

        :return: List of pairs `(str_request, last_update_time)`
        """
        raise NotImplementedError()

    def remove(self, str_request):
        """Remove the item from the cache."""
        raise NotImplementedError()


class Cache(Executor):
    """A base class for a "cache".  Implements the business logic, but defers
    to two members for storing/retrieving objects, and fetching new objects.

    :param executor: The :class:`Executor` instance to delegate to if the cache
      cannot satisfy the request.
    :param cache: The :class:`ConcereteCache` instance to use for storing
      objects.
    """
    def __init__(self, executor, cache):
        self._executor = executor
        self._cache = cache
        self._expire_time = None
        pass

    def no_timeout(self):
        """Set so that no cache objects expire."""
        self._expire_time = None

    @property
    def expire_time(self):
        """The duration after which cached objects will "expire" (be removed
        from the cache).   `None` indicates no time-out.
        """
        return self._expire_time

    @expire_time.setter
    def expire_time(self, duration):
        self._expire_time = duration

    def fetch(self, request):
        str_request = str(request)

        cache = self._cache.get_from_cache(str_request)
        if self.expire_time is not None and cache is not None:
            since_refresh = _datetime.datetime.now() - cache[1]
            if since_refresh > self.expire_time:
                cache = None

        if cache is None:
            obj = self._executor.fetch(request)
            if obj is not None:
                self._cache.place_in_cache(str_request, bytes(obj))
        else:
            obj = cache[0]
        return obj


def database_exists(db_filename):
    """Attempt to open the file as a SQLite database and see if there is a
    table "cache".  Returns `True` if there is (with any schema) and `False`
    for any error.
    """
    try:
        _os.stat(db_filename)
        conn = _sqlite3.connect(db_filename)
        try:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            tables = [x[0] for x in tables]
            return "cache" in tables
        except Exception:
            return False
        finally:
            conn.close()
    except Exception:
        return False


class SQLiteCache(ConcreteCache):
    """Uses a SQLite database to implement a cache.  There is one table,
    "cache", and objects are stored by the string of their "request".

    :param db_filename: The filename of the database.  If the database exists,
      we check for the existance of a table "cache", and create it if it
      doesn't exist.
    """
    def __init__(self, db_filename):
        if not database_exists(db_filename):
            self._make_database(db_filename)
        self._filename = db_filename
        self._connection_provider = _utils.PerThreadProvider(self._new)

    def _new(self):
        return _sqlite3.connect(self._filename)

    def _make_database(self, db_filename):
        conn = _sqlite3.connect(db_filename)
        try:
            conn.execute("CREATE table cache (request STRING UNIQUE, data BLOB, create_time STRING)")
        finally:
            conn.close()

    _ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"

    def get_from_cache(self, str_request):
        conn = self._connection_provider.get()
        row = conn.execute("SELECT data, create_time FROM cache WHERE request=?", (str_request,)).fetchone()
        if row is None:
            return None
        update_time = _datetime.datetime.strptime(row[1], self._ISO_FORMAT)
        return row[0], update_time

    def place_in_cache(self, str_request, obj_as_bytes):
        update_time = _datetime.datetime.strftime(_datetime.datetime.now(), self._ISO_FORMAT)
        data = (str_request, obj_as_bytes, update_time)
        with self._connection_provider.get() as conn:
            conn.execute("INSERT OR REPLACE INTO cache(request, data, create_time) VALUES (?,?,?)", data)

    def query(self):
        conn = self._connection_provider.get()
        cursor = conn.execute("SELECT request, create_time FROM cache")
        out = []
        for row in cursor:
            update_time = _datetime.datetime.strptime(row[1], self._ISO_FORMAT)
            out.append((row[0], update_time))
        return out

    def remove(self, str_request):
        with self._connection_provider.get() as conn:
            conn.execute("DELETE FROM cache WHERE request=?", (str_request,))

    def close(self):
        """Close the underlying database connection (for this thread)."""
        self._connection_provider.get().close()
