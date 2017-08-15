"""
utils
~~~~~

Some utility functions.

- Logging.  Supports configuring logging to the real stdout to support sensible
  logging when using e.g. a Jupyter notebook.
- Cache.
"""

import collections as _collections
import bz2 as _bz2
import PIL.Image as _Image
import threading as _threading

def start_logging():
    """Set the logging system to log to the (real) `stdout`.  Suitable for
    logging to the console when using a Jupyter notebook, for example.
    """
    import logging, sys
    logger = logging.getLogger("tilemapbase")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.__stdout__)

    fmt = logging.Formatter("{asctime} {levelname} {name} - {message}", style="{")
    ch.setFormatter(fmt)

    logger.addHandler(ch)


class Cache(_collections.UserDict):
    """Simple cache.  Implements the dictionary interface.  Objects are evicted
    from the cache by evicting the object least recently accessed.  Ties are
    broken by order of insertion.

    :param maxcount: The maximum number of objects to cache.
    """
    def __init__(self, maxcount=32):
        self._maxcount = maxcount
        self._access_count = 0
        self._accesses = {}
        super().__init__()
    
    def __setitem__(self, key, value):
        if len(self.data) == self._maxcount and key not in self.data:
            self._evict()
        self._accesses[key] = self._access_count
        self._access_count += 1
        self.data[key] = value

    def __getitem__(self, key):
        self._accesses[key] = self._access_count
        self._access_count += 1
        return self.data[key]

    def __delitem__(self, key):
        del self.data[key]
        del self._accesses[key]

    def _evict(self):
        toremove = -1
        for key, value in self._accesses.items():
            if toremove == -1 or toremove > value:
                toremove = value
                removekey = key
        self.__delitem__(removekey)

class ImageCache(Cache):
    """A subclass of :class:`Cache` which supports compressing :mod:`Pillow`
    images using `bzip2`.  For map tiles, this can save memory.  In practise,
    it is very slow...
    
    Any input object supporting a method `tobytes` will be compressed.  Any
    `bytes` object will be decompressed.
    """
    def __init__(self, maxcount=32):
        super().__init__(maxcount)

    class _CompressedImage():
        def __init__(self, mode, size, data):
            self.mode = mode
            self.size = size
            self.data = data

    def __setitem__(self, key, value):
        try:
            b = value.tobytes()
            assert isinstance(b, bytes)
            if value.mode == "P":
                b = b + bytes(value.getpalette())
            data = _bz2.compress(b)
            value = self._CompressedImage(value.mode, value.size, data)
        except:
            pass
        super().__setitem__(key, value)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        if isinstance(value, self._CompressedImage):
            image = _Image.new(value.mode, value.size)
            data = _bz2.decompress(value.data)
            if value.mode == "P":
                pal = data[-768:]
                image.putpalette(list(pal))
                data = data[:-768]
            image.frombytes(data)
            value = image
        return value

class PerThreadProvider():
    """Using a Factory, provide objects for which there must be one per
    thread.  Contains caching and clean-up code.
    
    :param factory: A callable to be invoked to generate a new object.
    """
    def __init__(self, factory):
        self._factory = factory
        self._cache = dict()
        self._desc = None

    def get(self):
        """Return a cached instance of the `object`, or if this is a new
        thread, build an new object and return it."""
        self._clean()
        our_id = _threading.get_ident() 
        if our_id not in self._cache:
            self._cache[our_id] = self._factory()
        return self._cache[our_id]

    def _clean(self):
        active_ids = {thread.ident for thread in _threading.enumerate()}
        our_ids = set(self._cache.keys())
        our_ids.difference_update(active_ids)
        for thread_id in our_ids:
            if self._desc is not None:
                self._desc(self._cache[thread_id])
            del self._cache[thread_id]

    def active_objects(self):
        """List of active objects"""
        return list(self._cache.values())

    def set_destructor(self, destructor):
        """Set a callable to be invoke on each `object` before it is
        cleared from the cache."""
        self._desc = destructor
