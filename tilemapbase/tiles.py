"""
tiles
~~~~~

Handles reading tiles from a HTTP source, and caching.

Please note that for OpenStreetMap (and derived) tiles:

- Data is "© OpenStreetMap contributors”, see
  http://www.openstreetmap.org/copyright
- Tile set usage is subject to constraints:
  https://operations.osmfoundation.org/policies/tiles/

For Stamen maps, please see:

- http://maps.stamen.com
- For Toner and Terrain maps, Map tiles by <a href="http://stamen.com">Stamen Design</a>,
  under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by
  <a href="http://openstreetmap.org">OpenStreetMap</a>, under
  <a href="http://www.openstreetmap.org/copyright">ODbL</a>.
- For Watercolor: Map tiles by <a href="http://stamen.com">Stamen Design</a>, under
  <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by
  <a href="http://openstreetmap.org">OpenStreetMap</a>, under
  <a href="http://creativecommons.org/licenses/by-sa/3.0">CC BY SA</a>.

For Carto maps, please see:

- https://carto.com/location-data-services/basemaps/
- Free for non-commerical use only

For other providers, copyright and usage rights may vary.
"""

from . import cache as _cache
import os as _os
import io as _io
import requests as _requests
import PIL.Image as _Image
import logging as _logging
import datetime as _datetime

# Singleton
_sqcache = None

def init(cache_filename = None, create = False):
    """Initialise the cache.  To avoid spamming the tile server, we cache the
    resulting tiles.  We are a little paranoid, so by default, the package will
    not work if no cache file exists.  Fix this by running

        init(create=True)

    to build the cache.  Optionally set a filename.
    """
    global _sqcache
    if _sqcache is not None:
        return

    if cache_filename is None:
        home = _os.path.expanduser("~")
        cache_filename = _os.path.join(home, "tilemapbase_cache.db")

    dbexists = _cache.database_exists(cache_filename) 
    if not dbexists and not create:
        msg = """The database cache file {} does no exist and no request made """\
            """to create.\n"""\
            """This could be caused by:\n"""\
            """- Running the package for the first time.  To be paranoid, we do """\
            """not automatically create a new cache.  Run `init(create=True)` """\
            """to initise the cache.\n"""\
            """- You have run the package before, but the cache has been lost. """\
            """Check that the filename is correct."""
        raise Exception(msg.format(cache_filename))

    _sqcache = _cache.SQLiteCache(cache_filename)

def close():
    """Shutdown the cache.  Call to close the connection to the database
    file."""
    global _sqcache
    if _sqcache is not None:
        try:
            _sqcache.close()
        finally:
            _sqcache = None

def _get_cache():
    global _sqcache
    if _sqcache is None:
        init()
    return _sqcache


class Cache(_cache.ConcreteCache):
    """A friendly wrapper around our cache, which decodes the key names.
    For this class, "request strings" are tuples of the form
    `(name, x, y, zoom)`.
    """
    def __init__(self, delegate):
        self._delegate = delegate

    @staticmethod
    def make_request_string(name, x, y, zoom):
        return "{}#{}#{}#{}".format(name, x, y, zoom)

    @staticmethod
    def split_request_string(str_request):
        name, x, y, zoom = str_request.split("#")
        return name, int(x), int(y), int(zoom)

    def get_from_cache(self, key):
        return self._delegate.get_from_cache(self.make_request_string(*key))

    def place_in_cache(self, str_request, obj_as_bytes):
        raise NotImplementedError()

    def query(self):
        return [(self.split_request_string(sr), ti) 
            for (sr, ti) in self._delegate.query()]

    def remove(self, key):
        self._delegate.remove(self.make_request_string(*key))

    def dump(self, dirname):
        """Dump all the files to the given directory.  The directory should
        be empty.  The directory structure will be:
           - dirname
             - Name of tile provider
               - Zoom level
                 - Files in format "x_y.png" or "x_y.jpg" or "x_y"

        We attempt to auto detect PNG and JPG files.
        """
        if _os.listdir(dirname) != []:
            raise Exception("Directory needs to be empty")
        
        for (key, _) in self.query():
            name, x, y, zoom = key
            filename = _os.path.join(dirname, name)
            try:
                _os.mkdir(filename)
            except:
                pass
            filename = _os.path.join(filename, str(zoom))                
            try:
                _os.mkdir(filename)
            except:
                pass
            data, _ = self.get_from_cache(key)
            if data[:4] == b"\x89PNG":
                ext = ".png"
            elif data[6:10] == b"JFIF":
                ext = ".jpg"
            else:
                ext = ""
            filename = _os.path.join(filename, "{}_{}{}".format(x, y, ext))
            with open(filename, "wb") as f:
                f.write(data)

    def clean(self, cutoff):
        """Remove all files from the cache which were written before the
        cutoff.

        :param cutoff: Datetime
        """
        query = list(self.query())
        for (key, time) in query:
            if time < cutoff:
                self.remove(key)


def get_cache():
    """Get access to the underlying DB cache.  For advanced usage only."""
    return Cache(_get_cache())


class _TilesExecutor(_cache.Executor):
    """Private class to run the HTTP request."""
    def __init__(self, parent):
        self.parent = parent
        self.logger = _logging.getLogger(__name__)

    def fetch(self, request):
        url = self.parent._request_http(request)
        self.logger.info("Requesting %s", url)
        # TODO: I didn't understand the default value of headers.
        #       So not to rely on any, avoid setting it if unset.
        if self.parent.headers is not None:
            response = _requests.get(url, headers=self.parent.headers)
        else:
            response = _requests.get(url)
        if not response.ok:
            raise IOError("Failed to download {}.  Got {}".format(url, response))
        try:
            _Image.open(_io.BytesIO(response.content))
        except:
            raise IOError("Received invalid tile from {}.".format(url), response)
        return response.content


class Tiles():
    """Class to fetch a tile as an image; transparently handles caching issues.
    Tiles will be expired from the cache after 2 months.
    
    :param request_string: A string which when used with `format` will give
      a well-formed URL for the tile.  For example, for standard OSM this is
      "http://a.tile.openstreetmap.org/{zoom}/{x}/{y}.png".
    :param source_name: A short, human-readable name, e.g. "OSM".  Should be
      unique, as also used by the cache.
    :param tilesize: The size of the (square) tiles, defaults to 256.
    :param maxzoom: The maximum tile zoom level, defaults to 19.
    :param headers: Dictionary of http headers for server requests
    """
    def __init__(self, request_string, source_name, tilesize=256, maxzoom = 19, headers = None):
        self.request = request_string
        self.name = source_name
        self.headers = headers
        self._maxzoom = maxzoom
        self._tilesize = tilesize
        self._cache = None

    def get_tile(self, x, y, zoom):
        """Attempt to fetch the tile at the specified coords and zoom level.

        :param x: X coord of the tile; must be between 0 (inclusive) and
          `2**zoom` (exclusive).
        :param y: Y coord of the tile.
        :param zoom: Integer, greater than or equal to 0.  19 is the commonly
          supported maximum zoom.

        :return: `None` for (cache related) failure, or a :package:`Pillow`
          image object of the tile.
        """
        tile = self._get_cache().fetch(self._request_string(x, y, zoom))
        if tile is None:
            return None
        try:
            fp = _io.BytesIO(tile)
            return _Image.open(fp)
        except:
            raise RuntimeError("Failed to decode data for {} - {}x{} @ {} zoom".format(self.name, x, y, zoom))

    @property
    def maxzoom(self):
        """The maximum zoom level supported by this tile provider."""
        return self._maxzoom

    @property
    def tilesize(self):
        """The size of the tiles."""
        return self._tilesize

    def _request_string(self, x, y, zoom):
        """Encodes the tile coords, zoom, and name into a string for the
        database."""
        return Cache.make_request_string(self.name, x, y, zoom)

    def _request_http(self, request_string):
        parts = request_string.split("#")
        if parts[0] != self.name:
            raise ValueError("Build for '{}' but asked to decode '{}'".format(self.name, parts[0]))
        x, y, zoom = [int(t) for t in parts[1:]]
        return self.request.format(x=x, y=y, zoom=zoom)

    # Lazy initialisation
    def _get_cache(self):
        if self._cache is None:
            dbcache = _get_cache()
            executor = _TilesExecutor(self)
            self._cache = _cache.Cache(executor, dbcache)
            self._cache.expire_time = _datetime.timedelta(days=60)
        return self._cache


"""We have to have functions for OSM realted requests so users can pass their own
user agent strings
"""
def build_OSM(headers={"User-Agent":"TileMapBase"}):
    """Standard Open Street Map tile server."""
    OSM = Tiles("http://a.tile.openstreetmap.org/{zoom}/{x}/{y}.png", "OSM", headers=headers)
    return OSM

def build_OSM_Humanitarian(headers={"User-Agent":"TileMapBase"}):
    """Humanitarian Open Street Map tile server."""
    OSM_Humanitarian = Tiles("http://a.tile.openstreetmap.fr/hot/{zoom}/{x}/{y}.png ", "OSM_HUMANITARIAN", headers=headers)
    return OSM_Humanitarian

"""Stamen, Toner, Standard."""
Stamen_Toner = Tiles("http://tile.stamen.com/toner/{zoom}/{x}/{y}.png", "STAMEN_TONER")

"""Stamen, Toner, Hybrid."""
Stamen_Toner_Hybrid = Tiles("http://tile.stamen.com/toner-hybrid/{zoom}/{x}/{y}.png", "STAMEN_TONER_Hybrid")

"""Stamen, Toner, Labels."""
Stamen_Toner_Labels = Tiles("http://tile.stamen.com/toner-labels/{zoom}/{x}/{y}.png", "STAMEN_TONER_Labels")

"""Stamen, Toner, Lines."""
Stamen_Toner_Lines = Tiles("http://tile.stamen.com/toner-lines/{zoom}/{x}/{y}.png", "STAMEN_TONER_Lines")

"""Stamen, Toner, Background."""
Stamen_Toner_Background = Tiles("http://tile.stamen.com/toner-background/{zoom}/{x}/{y}.png", "STAMEN_TONER_Background")

"""Stamen, Toner, Lite."""
Stamen_Toner_Lite = Tiles("http://tile.stamen.com/toner-lite/{zoom}/{x}/{y}.png", "STAMEN_TONER_Lite")

"""Stamen, Terrain."""
Stamen_Terrain = Tiles("http://tile.stamen.com/terrain/{zoom}/{x}/{y}.jpg", "STAMEN_TERRAIN")

"""Stamen, Terrain, Labels"""
Stamen_Terrain_Labels = Tiles("http://tile.stamen.com/terrain-labels/{zoom}/{x}/{y}.jpg", "STAMEN_TERRAIN_Labels")

"""Stamen, Terrain, Lines"""
Stamen_Terrain_Lines = Tiles("http://tile.stamen.com/terrain-lines/{zoom}/{x}/{y}.jpg", "STAMEN_TERRAIN_Lines")

"""Stamen, Terrain, Background"""
Stamen_Terrain_Background = Tiles("http://tile.stamen.com/terrain-background/{zoom}/{x}/{y}.jpg", "STAMEN_TERRAIN_Background")

"""Stamen, Watercolour"""
Stamen_Watercolour = Tiles("http://tile.stamen.com/watercolor/{zoom}/{x}/{y}.jpg", "STAMEN_WATERCOLOUR")

"""Carto, Light"""
Carto_Light = Tiles("http://a.basemaps.cartocdn.com/light_all/{zoom}/{x}/{y}.png", "CARTO_LIGHT")

"""Carto, Light, Labels"""
Carto_Light_Labels = Tiles("http://a.basemaps.cartocdn.com/light_only_labels/{zoom}/{x}/{y}.png", "CARTO_LIGHT_LABELS")

"""Carto, Light, No labels"""
Carto_Light_No_Labels = Tiles("http://a.basemaps.cartocdn.com/light_nolabels/{zoom}/{x}/{y}.png", "CARTO_LIGHT_NOLABELS")

"""Carto, Dark"""
Carto_Dark = Tiles("http://a.basemaps.cartocdn.com/dark_all/{zoom}/{x}/{y}.png", "CARTO_DARK")

"""Carto, Dark, Labels"""
Carto_Dark_Labels = Tiles("http://a.basemaps.cartocdn.com/dark_only_labels/{zoom}/{x}/{y}.png", "CARTO_DARK_LABELS")

"""Carto, Dark, No labels"""
Carto_Dark_No_Labels = Tiles("http://a.basemaps.cartocdn.com/dark_nolabels/{zoom}/{x}/{y}.png", "CARTO_DARK_NOLABELS")
