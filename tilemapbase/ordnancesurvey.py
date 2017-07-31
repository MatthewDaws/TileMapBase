"""
ordnancesurvey
~~~~~~~~~~~~~~

Supports raster tiles from the Ordnance Survey.  We support the (freely
downloadable) "OS OpenMap Local" and "OS VectorMap Local".

- "OS OpenMap Local" has file-names like "SE00NE.tif" where "SE" is the "grid
  code", "00" is the first digit of the x and y grid reference, and "NE" means
  "North East" i.e. the upper left part of the "00" grid.
- "OS VectorMap Local" has file-name like "SE00.tif" with the same format, but
  2 times less resolution in both coordinates.

The Ordnance Survey National Grid is, briefly, the projection epsg:4326.

- However, the "origin" is taken to be (-1,000,000, -500,000)
- The 500km by 500km square is specified a letter A-Z (not using I), but A
  is the _upper_ left corner (wheras (0,0) is the _lower_ left corner).
- With this, the 100km by 100km square is specified by another letter
- Then the most significant digits in the 100km by 100km square give a two
  digit code specifying a 10km by 10km square.
- Alternative, then entire 5 digit number from 00000 to 99999 is given, to
  specify a coordinate to the nearest meter.
- https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid

"""

import math as _math
import os as _os
import re as _re
import PIL.Image as _Image
from .mapping import _BaseExtent

# Singletons
_openmap_local_lookup = None
_vectormap_local_lookup = None

def init(start_directory):
    """Perform a search for tile files, and so initialise the support.

    :param start_directory: The string name of the directory to search.  May
      also be an iterable of strings to search more than one directory.  All
      sub-directories will be searched for valid filenames.
    """
    global _openmap_local_lookup, _vectormap_local_lookup
    _openmap_local_lookup = dict()
    _vectormap_local_lookup = dict()
    if not isinstance(start_directory, str):
        dirs = list(start_directory)
    else:
        dirs = [start_directory]
    while len(dirs) > 0:
        dirname = dirs.pop()
        dirs.extend(_init_scan_one_directory(dirname))

def _init_scan_one_directory(dir_name):
    global _openmap_local_lookup, _vectormap_local_lookup
    oml = _re.compile("^[A-Z]{2}\d\d[NESW]{2}\.tif$")
    vml = _re.compile("^[A-Z]{2}\d\d.tif$")
    dirs = []
    dir_name = _os.path.abspath(dir_name)
    for entry in _os.scandir(dir_name):
        if entry.is_dir():
            dirs.append(_os.path.abspath(entry.path))
        elif entry.is_file():
            if oml.match(entry.name):
                _openmap_local_lookup[entry.name[:2]] = dir_name
            elif vml.match(entry.name):
                _vectormap_local_lookup[entry.name[:2]] = dir_name
    return dirs

def to_os_national_grid(longitude, latitude):
    """Converts the longitude and latitude coordinates to the Ordnance Survery
    National Grid convention.
    
    :return: `(grid_code, eastings, northings)` where `eastings` and
      `northings` are the residual coordinates in the range [0, 1).
    """
    grid_code, x, y = _code_grid_residual(longitude, latitude)
    xx, yy = _math.floor(x), _math.floor(y)
    return "{} {} {}".format(grid_code, xx, yy), x - xx, y - yy

def _code_grid_residual(longitude, latitude):
    x, y = project(longitude, latitude)
    return _coords_to_code_grid_residual(x, y)
    
def _coords_to_code_grid_residual(x, y):
    codes = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    x500, y500 = _math.floor(x / 500000), _math.floor(y / 500000)
    index = (2 + x500) + (3 - y500) * 5
    if index < 0 or index >= 25:
        raise ValueError()
    grid_code = codes[index]
    
    x, y = x - 500000 * x500, y - 500000 * y500
    x100, y100 = _math.floor(x / 100000), _math.floor(y / 100000)
    index = x100 + (4 - y100) * 5
    if index < 0 or index >= 25:
        raise AssertionError()
    grid_code += codes[index]

    return grid_code, x - x100 * 100000, y - y100 * 100000

def coords_to_os_national_grid(x, y):
    """Convert the projected coordinates `(x,y)` to the Ordnance Survery
    National Grid convention.
    """
    grid_code, x, y = _coords_to_code_grid_residual(x, y)
    xx, yy = _math.floor(x), _math.floor(y)
    return "{} {} {}".format(grid_code, xx, yy)

def os_national_grid_to_coords(grid_position):
    """Convert a OS national grid reference like `SE 29383 34363` to
    coordinates, e.g. `(429383, 434363)`."""
    try:
        code, x, y = grid_position.split(" ")
        x, y = int(x), int(y)
        codes = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
        index0 = codes.index(code[0])
        x500, y500 = (index0 % 5) - 2, 3 - (index0 // 5)
        index1 = codes.index(code[1])
        x100, y100 = (index1 % 5), 4 - (index1 // 5)
        return 500000 * x500 + 100000 * x100 + x, 500000 * y500 + 100000 * y100 + y
    except:
        raise ValueError("Should be a grid reference like 'SE 12345 12345'.")


class TileNotFoundError(Exception):
    pass


class TileSource():
    """Abstract base class / interface."""
    def __call__(self, grid_position):
        """Fetch a tile.  Raises :class:`TileNotFoundError` with a suitable
        error message on error.
        
        :param grid_position: An OS national grid reference, such as
          "SE 12345 12345".

        :return: The file as a :class:`PIL.Image` object.
        """
        raise NotImplementedError()

    @property
    def tilesize(self):
        """The size of each tile in pixels."""
        raise NotImplementedError()

    @property
    def size_in_meters(self):
        """The size of each tile in meters."""
        raise NotImplementedError()


class OpenMapLocal(TileSource):
    """Uses tiles from the OS OpenMap Local collection, see
    https://www.ordnancesurvey.co.uk/business-and-government/products/os-open-map-local.html
    """
    def __init__(self):
        global _openmap_local_lookup
        if _openmap_local_lookup is None:
            raise Exception("Must call `init` first to find tiles.")
        self._source = _openmap_local_lookup        

    def __call__(self, grid_position):
        try:
            code, x, y = grid_position.split()
            x, y = int(x), int(y)
        except Exception:
            raise ValueError("{} appears not to be a valid national grid reference".format(grid_position))
        if code not in self._source:
            raise TileNotFoundError("No tiles loaded for square {}".format(code))
        dirname = self._source[code]
        squarex = _math.floor(x / 10000)
        squarey = _math.floor(y / 10000)
        x -= squarex * 10000
        y -= squarey * 10000
        if x < 5000 and y < 5000:
            part = "SW"
        elif x < 5000 and y >= 5000:
            part = "NW"
        elif x >= 5000 and y < 5000:
            part = "SE"
        else:
            part = "NE"
        filename = "{}{}{}{}.tif".format(code, squarex, squarey, part)
        return _Image.open(_os.path.join(dirname, filename))

    @property
    def tilesize(self):
        return 5000

    @property
    def size_in_meters(self):
        return 5000


class Extent(_BaseExtent):
    """Store details about an area of OS national grid space.  The region must
    be inside the box `-1,000,000 <= x < 1,500,000` and
    `-500,000 < y <= 1,999,999` but this is a much larger range than the UK
    and so not all coordinates will correspond to valid tiles.

    :param xmin:
    :param xmax: The range of the x coordinates.
    :param ymin:
    :param ymax: The range of the y coordinates.
    """
    def __init__(self, xmin, xmax, ymin, ymax):
        super().__init__(xmin, xmax, ymin, ymax)
        if not (-1000000 <= xmin and xmax < 1500000 and -500000 < ymin and ymax < 2000000):
            raise ValueError("Not with range")
        self.project = self._project

    @property
    def yrange(self):
        """A pair of (ymin, ymax)."""
        return (self.ymin, self.ymax)

    @staticmethod
    def from_centre(x, y, xsize=None, ysize=None, aspect=1.0):
        """Construct a new instance centred on the given location, with a given
        width and/or height.  If only one of the width or height is specified,
        the aspect ratio is used.
        """
        xmin, xmax, ymin, ymax = _BaseExtent.from_centre(x, y, xsize, ysize, aspect)
        return Extent(xmin, xmax, ymin, ymax)

    @staticmethod
    def from_centre_lonlat(longitude, latitude, xsize=None, ysize=None, aspect=1.0):
        """Construct a new instance centred on the given location with a given
        width and/or height.  If only one of the width or height is specified,
        the aspect ratio is used.
        """
        x, y = project(longitude, latitude)
        return Extent.from_centre(x, y, xsize, ysize, aspect)

    @staticmethod
    def from_lonlat(longitude_min, longitude_max, latitude_min, latitude_max):
        """Construct a new instance from longitude/latitude space."""
        xmin, ymin = project(longitude_min, latitude_max)
        xmax, ymax = project(longitude_max, latitude_min)
        return Extent(xmin, xmax, ymin, ymax)

    @staticmethod
    def from_centre_grid(grid_position, xsize=None, ysize=None, aspect=1.0):
        """Construct a new instance centred on the given location with a given
        width and/or height.  The centre location is given as a OS grid
        reference, such as "SE 29383 34363".  If only one of the width or
        height is specified, the aspect ratio is used.
        """
        x, y = os_national_grid_to_coords(grid_position)
        return Extent.from_centre(x, y, xsize, ysize, aspect)

    def _project(self, x, y):
        # For compatibility with the base class
        return x, y

    def __repr__(self):
        return "Extent(({},{})->({},{}) in OS National Grid)".format(self.xmin,
                self.ymin, self.xmax, self.ymax)

    def with_centre(self, xc, yc):
        """Create a new :class:`Extent` object with the centre moved to these
        coordinates and the same rectangle size.
        """
        oldxc = (self._xmin + self._xmax) / 2
        oldyc = (self._ymin + self._ymax) / 2
        return Extent(self._xmin + xc - oldxc, self._xmax + xc - oldxc,
            self._ymin + yc - oldyc, ymax = self._ymax + yc - oldyc)

    def with_centre_lonlat(self, longitude, latitude):
        """Create a new :class:`Extent` object with the centre the given
        longitude / latitude and the same rectangle size.
        """
        xc, yc = project(longitude, latitude)
        return self.with_centre(xc, yc)

    def to_aspect(self, aspect):
        """Return a new instance with the given aspect ratio.  Shrinks the
        rectangle as necessary."""
        return Extent(*self._to_aspect(aspect))

    def with_absolute_translation(self, dx, dy):
        """Return a new instance translated by this amount.  Clips `y` to the
        allowed region of [0,1].
        
        :param dx: Amount to add to `x` value (on the 0 to 1 scale).
        :param dy: Amount to add to `y` value (on the 0 to 1 scale).
        """
        return Extent(self._xmin + dx, self._xmax + dx, self._ymin + dy, self._ymax + dy)

    def with_translation(self, dx, dy):
        """Return a new instance translated by this amount.  The values are
        relative to the current size, so `dx==1` means translate one whole
        rectangle size (to the right).
        
        :param dx: Amount to add to `x` value relative to current width.
        :param dy: Amount to add to `y` value relative to current height.
        """
        dx = dx * (self._xmax - self._xmin)
        dy = dy * (self._ymax - self._ymin)
        return self.with_absolute_translation(dx, dy)

    def with_scaling(self, scale):
        """Return a new instance with the same midpoint, but with the width/
        height divided by `scale`.  So `scale=2` will zoom in."""
        midx = (self._xmin + self._xmax) / 2
        midy = (self._ymin + self._ymax) / 2
        xs = (self._xmax - self._xmin) / scale / 2
        ys = (self._ymax - self._ymin) / scale / 2
        return Extent(midx - xs, midx + xs, midy - ys, midy + ys , self._project_str)

    def with_scaling(self, scale):
        """Return a new instance with the same midpoint, but with the width/
        height divided by `scale`.  So `scale=2` will zoom in."""
        return Extent(*self._with_scaling(scale))


class Plotter():
    """Convert a :class:`Extent` instance to an actual representation in terms
    of tiles.  
    
    :param extent: The base :class:`Extent` instance.
    :param source: Instance of :class:`TileSource` giving the source of tiles.
    """
    def __init__(self, extent, source):
        self._extent = extent
        self._source = source

    def _quant(self, x):
        return _math.floor(x / self._source.size_in_meters)

    def _unquant(self, x):
        return x * self._source.size_in_meters

    @property
    def extent(self):
        """The :class:`Extent` we were built with."""
        return self._extent

    def plotlq(self, ax, **kwargs):
        """Use these settings to plot the tiles to a `matplotlib` axes.  This
        method repeatedly calls the `imshow` method, which does not lead to the
        highest quality tiling: compare with :method:`plot`.

        :param ax: The axes object to plot to.
        :param kwargs: Other arguments which will be forwarded to the `imshow`
          matplotlib method.
        """
        xs, xe = self._quant(self._extent.xmin), self._quant(self._extent.xmax)
        ys, ye = self._quant(self._extent.ymin), self._quant(self._extent.ymax)
        for x in range(xs, xe+1):
            for y in range(ys, ye+1):
                xx, yy = self._unquant(x), self._unquant(y)
                code = coords_to_os_national_grid(xx, yy)
                tile = self._source(code)
                ax.imshow(tile, interpolation="lanczos",
                    extent=(xx, xx + self._source.size_in_meters, yy, yy + self._source.size_in_meters),
                    **kwargs)
        ax.set(xlim = self.extent.xrange, ylim = self.extent.yrange)

    def as_one_image(self):
        """Use these settings to assemble tiles into a single image.

        :return: A :class:`PIL.Image` instance.
        """
        xs, xe = self._quant(self._extent.xmin), self._quant(self._extent.xmax)
        ys, ye = self._quant(self._extent.ymin), self._quant(self._extent.ymax)
        xsize = (1 + xe - xs) * self._source.tilesize
        ysize = (1 + ye - ys) * self._source.tilesize
        out = _Image.new("RGB", (xsize, ysize))
        for x in range(xs, xe+1):
            for y in range(ys, ye+1):
                xx, yy = self._unquant(x), self._unquant(y)
                code = coords_to_os_national_grid(xx, yy)
                tile = self._source(code)
                xo, yo = (x - xs) * self._source.tilesize, (ye - y) * self._source.tilesize
                out.paste(tile, (xo, yo))
        return out

##### (Optional) usage of pyproj

try:
    import pyproj as _pyproj
except:
    import logging
    logging.getLogger(__name__).error("Failed to load module 'pyproj'.")
    _pyproj = None

if _pyproj is not None:
    _bng = _pyproj.Proj(init="epsg:27700")
    _wgs84 = _pyproj.Proj(init="epsg:4326")
    
def project(longitude, latitude):
    global _bng, _wgs84
    return _pyproj.transform(_wgs84, _bng, longitude, latitude)
