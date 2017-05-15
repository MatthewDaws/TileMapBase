"""
cache
~~~~~

Provides a base class for caching objects which are associated with a "request"
object.  Concrete implementation using a sqlite database.
"""

import datetime as _datetime
import sqlite3 as _sqlite3
import os as _os

class Request():
    """A class for making a request for an object.  The :method:`str` needs
    to uniquely identify the request, as this is used by the cache.

    In practise, any class with a :method:`str` which is unique to each request
    can be used.  (I.e. use duck-typing).
    """
    pass

    def __str__(self):
        raise NotImplementedError()


class CacheObject():
    """A base class for the returned object from the executor.  All that is
    required of such an object `x` is that it can be converted as `bytes(x)`.
    """

    def __bytes__(self):
        raise NotImplementedError()


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


class Cache(Executor):
    """A base class for a "cache".

    :param executor: The :class:`Executor` instance to delegate to if the cache
      cannot satisfy the request.
    """
    def __init__(self, executor):
        self._executor = executor
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

    @property
    def executor(self):
        raise NotImplementedError()

    @executor.setter
    def executor(self, value):
        self._executor = value

    def fetch(self, request):
        str_request = str(request)

        cache = self._get_from_cache(str_request)
        if self.expire_time is not None and cache is not None:
            since_refresh = _datetime.datetime.now() - cache[1]
            if since_refresh > self.expire_time:
                cache = None

        if cache is None:
            obj = self._executor.fetch(request)
            if obj is not None:
                self._place_in_cache(str_request, bytes(obj))
        else:
            obj = cache[0]
        return obj

    def _get_from_cache(self, str_request):
        """Return `None` on failure to find.
        
        :return: Pair of (object, last_update_time)
        """
        raise NotImplementedError()

    def _place_in_cache(self, str_request, obj_as_bytes):
        """Write the object to the cache.  Should use the current time when
        storing the "last update time"."""
        raise NotImplementedError()

    def time(self):
        return _datetime.datetime.now()


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


class SQLiteCache(Cache):
    """Uses a SQLite database to implement a cache.  There is one table,
    "cache", and objects are stored by the string of their "request".

    :param executor: The :class:`Executor` to make requests with.
    :param db_filename: The filename of the database.  If the database exists,
      we check for the existance of a table "cache", and create it if it
      doesn't exist.
    """
    def __init__(self, executor, db_filename):
        super().__init__(executor)
        if not database_exists(db_filename):
            self._make_database(db_filename)
        self.conn = _sqlite3.connect(db_filename)

    def _make_database(self, db_filename):
        conn = _sqlite3.connect(db_filename)
        try:
            conn.execute("CREATE table cache (request STRING UNIQUE, data BLOB, create_time STRING)")
        finally:
            conn.close()

    _ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"

    def _get_from_cache(self, str_request):
        row = self.conn.execute("SELECT data, create_time FROM cache WHERE request=?", (str_request,)).fetchone()
        #print("From DB: {} -> {}".format(str_request, row))
        if row is None:
            return None
        update_time = _datetime.datetime.strptime(row[1], self._ISO_FORMAT)
        return row[0], update_time

    def _place_in_cache(self, str_request, obj_as_bytes):
        update_time = _datetime.datetime.strftime(_datetime.datetime.now(), self._ISO_FORMAT)
        data = (str_request, obj_as_bytes, update_time)
        #print("Writing {}".format(data))
        with self.conn:
            self.conn.execute("INSERT INTO cache(request, data, create_time) VALUES (?,?,?)", data)

    def close(self):
        """Close the underlying database connection."""
        self.conn.close()