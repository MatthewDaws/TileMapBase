"""
mapping
~~~~~~~

Performs projection functions.  Map tiles are projected using the
https://en.wikipedia.org/wiki/Web_Mercator projection, which does not preserve
area or length, but is convenient.  We follow these conventions:

- Coordinates are always in the order longitude, latitude.
- Longitude varies between -180 and 180 degrees.  This is the east/west
  location from the Prime Meridian, in Greenwich, UK.  Positive is to the east.
- Latitude varies between -85 and 85 degress (approximately.  More extreme
  values cannot be represented in Web Mercator).  This is the north/south
  location from the equator.  Positive is to the north.

Once projected, the x coordinate varies between 0 and 1, from -180 degrees west
to 180 degrees east.  The y coordinate varies between 0 and 1, from (about) 85
degrees north to -85 degrees south.  Hence the natural ordering from latitude
to y coordinate is reversed.

Web Mercator agrees with the projections EPSG:3857 and EPSG:3785 up to
rescaling and reflecting in the y coordinate.

For more information, see for example
http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames

Typical workflow is to use one of the `extent` methods to construct an
:class:`Extent` object.  This stores details of a rectangle of web mercator
space and how to draw this space.  This object can then be used to plot the
basemap to a `matplotlib` axes object.
"""

import math as _math
import PIL.Image as _Image

_EPSG_RESCALE = 20037508.342789244

def _to_3857(x, y):
    return ((x - 0.5) * 2 * _EPSG_RESCALE,
        (0.5 - y) * 2 * _EPSG_RESCALE)

def _from_3857(x, y):
    xx = 0.5 + (x / _EPSG_RESCALE) * 0.5
    yy = 0.5 - (y / _EPSG_RESCALE) * 0.5
    return xx, yy

def project(longitude, latitude):
    """Project the longitude / latitude coords to the unit square.

    :param longitude: In degrees, between -180 and 180
    :param latitude: In degrees, between -85 and 85

    :return: Coordinates `(x,y)` in the "Web Mercator" projection, normalised
      to be in the range [0,1].
    """
    xtile = (longitude + 180.0) / 360.0
    lat_rad = _math.radians(latitude)
    ytile = (1.0 - _math.log(_math.tan(lat_rad) + (1 / _math.cos(lat_rad))) / _math.pi) / 2.0
    return (xtile, ytile)

def to_lonlat(x, y):
    """Inverse project from "web mercator" coords back to longitude, latitude.

    :param x: The x coordinate, between 0 and 1.
    :param y: The y coordinate, between 0 and 1.

    :return: A pair `(longitude, latitude)` in degrees.
    """
    longitude = x * 360 - 180
    latitude = _math.atan(_math.sinh(_math.pi * (1 - y * 2))) * 180 / _math.pi
    return (longitude, latitude)


class Extent():
    """Store details about an area of web mercator space.  Can be switched to
    be projected in EPSG:3857 / EPSG:3785.

    :param xmin:
    :param xmax: The range of the x coordinates, between 0 and 1.
    :param ymin:
    :param ymax: The range of the y coordinates, between 0 and 1.
    """
    def __init__(self, xmin, xmax, ymin, ymax, projection_type="normal"):
        self._xmin, self._xmax = xmin, xmax
        self._ymin, self._ymax = ymin, ymax
        if projection_type == "normal":
            self.project = self._normal_project
        elif projection_type == "epsg:3857":
            self.project = self._3857_project
        else:
            raise ValueError()
        self._project_str = projection_type

    @staticmethod
    def from_centre(x, y, xsize=None, ysize=None, aspect=1.0):
        """Construct a new instance centred on the given location in Web
        Mercator space, with a given width and/or height.  If only one of the
        width or height is specified, the aspect ratio is used.
        """
        if xsize is None and ysize is None:
            raise ValueError("Must specify at least one of width and height")
        x, y, aspect = float(x), float(y), float(aspect)
        if xsize is not None:
            xsize = float(xsize)
        if ysize is not None:
            ysize = float(ysize)
        if xsize is None:
            xsize = ysize * aspect
        if ysize is None:
            ysize = xsize / aspect
        xmin, xmax = x - xsize / 2, x + xsize / 2
        xmin, xmax = max(0, xmin), min(1.0, xmax)
        ymin, ymax = y - ysize / 2, y + ysize / 2
        ymin, ymax = max(0, ymin), min(1.0, ymax)
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
        """Map the box, in longitude/latitude space, to the web mercator
        projection."""
        xmin, ymin = project(longitude_min, latitude_max)
        xmax, ymax = project(longitude_max, latitude_min)
        return Extent(xmin, xmax, ymin, ymax)

    @property
    def xmin(self):
        """Minimum x value of the region."""
        return self.project(self._xmin, self._ymin)[0]

    @property
    def xmax(self):
        """Maximum x value of the region."""
        return self.project(self._xmax, self._ymax)[0]

    @property
    def width(self):
        return self.xmax - self.xmin

    @property
    def xrange(self):
        """A pair of (xmin, xmax)."""
        return (self.xmin, self.xmax)

    @property
    def ymin(self):
        """Minimum y value of the region."""
        return self.project(self._xmin, self._ymin)[1]

    @property
    def ymax(self):
        """Maximum y value of the region."""
        return self.project(self._xmax, self._ymax)[1]

    @property
    def height(self):
        return self.ymax - self.ymin

    @property
    def yrange(self):
        """A pair of (ymax, ymin).  Inverted so as to work well with
        `matplotib`.
        """
        return (self.ymax, self.ymin)

    def __repr__(self):
        return "Extent(({},{})->({},{}) projected as {})".format(self.xmin, self.ymin,
                      self.xmax, self.ymax, self._project_str)

    def clone(self, projection_type=None):
        """A copy"""
        if projection_type is None:
            projection_type = self._project_str
        return Extent(self._xmin, self._xmax, self._ymin, self._ymax, projection_type)

    def _normal_project(self, x, y):
        """Project from tile space to coords."""
        return x, y

    def _3857_project(self, x, y):
        return _to_3857(x, y)

    def to_project_3857(self):
        """Change the coordinate system to conform to EPSG:3857 / EPSG:3785
        which can be useful when working with e.g. geoPandas (or other data
        which is projected in this way).
        
        :return: A new instance of :class:`Extent`
        """
        return self.clone("epsg:3857")

    def to_project_web_mercator(self):
        """Change the coordinate system back to the default, the unit square.

        :return: A new instance of :class:`Extent`
        """
        return self.clone("normal")

    def with_centre(self, xc, yc):
        """Create a new :class:`Extent` object with the centre moved to these
        coorindates and the same rectangle size.
        """
        oldxc = (self._xmin + self._xmax) / 2
        oldyc = (self._ymin + self._ymax) / 2
        return Extent(self._xmin + xc - oldxc, self._xmax + xc - oldxc,
            self._ymin + yc - oldyc, self._ymax + yc - oldyc, self._project_str)

    def with_centre_lonlat(self, longitude, latitude):
        """Create a new :class:`Extent` object with the centre the given
        longitude / latitude and the same rectangle size.
        """
        xc, yc = project(longitude, latitude)
        return self.with_centre(xc, yc)
    
    def to_aspect(self, aspect):
        """Return a new instance with the given aspect ratio.  Shrinks the
        rectangle as necessary."""
        new_xrange = self.height * aspect
        new_yrange = self.height
        if new_xrange > self.width:
            new_xrange = self.width
            new_yrange = self.width / aspect
        midx = (self._xmin + self._xmax) / 2
        midy = (self._ymin + self._ymax) / 2
        return Extent(midx - new_xrange / 2, midx + new_xrange / 2,
                      midy - new_yrange / 2, midy + new_yrange / 2,
                      self._project_str)
        

class Plotter():
    """Convert a :class:`Extent` instance to an actual representation in terms
    of tiles.  You can either specify a known zoom level of tiles, or specify
    a width and/or height in pixels, and allow the zoom level to be chosen
    appropriately.  If both a width and height are specified, then the greatest
    zoom level is used.
    
    :param extent: The base :class:`Extent` instance.
    :param tile_provider: The :class:`tiles.Tiles` object which provides
      tiles.
    :param zoom: If not `None`, then use this zoom level (will be clipped to
      the best zoom to tile provider can give).
    :param width: Optional target width in pixels.
    :param height: Optional target height in pixels.
    :param tile_size: The (square) tile size, defaults to 256 pixels.
    """
    def __init__(self, extent, tile_provider, zoom=None, width=None, height=None):
        if zoom is None and width is None and height is None:
            raise ValueError("Need to specify one of zoom, width or height")
        if zoom is not None and (width is not None or height is not None):
            raise ValueError("Cannot specify both a zoom and a width or height")
        
        self._extent = extent.to_project_web_mercator()
        self._original_extent = extent
        self._tile_provider = tile_provider
        if zoom is not None:
            self._zoom = zoom
        else:
            options = []
            if width is not None:
                options.append(self._needed_zoom(self._extent.xmax - self._extent.xmin, width))
            if height is not None:
                options.append(self._needed_zoom(self._extent.ymax - self._extent.ymin, height))
            self._zoom = max(options)
        self._zoom = min(self._zoom, self._tile_provider.maxzoom)

    def _needed_zoom(self, web_mercator_range, pixel_range):
        scale = web_mercator_range / pixel_range
        return max(0, int(-_math.log2(scale * self._tile_provider.tilesize)))

    @property
    def extent(self):
        return self._original_extent
    
    @property
    def extent_in_web_mercator(self):
        self._extent
    
    @property
    def zoom(self):
        """The actual zoom level to be used."""
        return self._zoom
    
    @property
    def xtilemin(self):
        """The least x coordinate in tile space we need to cover the region."""
        return int(2 ** self._zoom * self._extent.xmin)

    @property
    def xtilemax(self):
        """The greatest x coordinate in tile space we need to cover the region.
        """
        return int(2 ** self._zoom * self._extent._xmax)

    @property
    def ytilemin(self):
        """The least y coordinate in tile space we need to cover the region."""
        return int(2 ** self._zoom * self._extent._ymin)

    @property
    def ytilemax(self):
        """The greatest y coordinate in tile space we need to cover the region.
        """
        return int(2 ** self._zoom * self._extent._ymax)

    def _check_download_size(self):
        num_tiles = ( (self.xtilemax + 1 - self.xtilemin) *
            (self.ytilemax + 1 - self.ytilemin) )
        if num_tiles > 128:
            raise ValueError("Would use {} tiles, which is excessive.  Pass `allow_large = True` to force usage.".format(num_tiles))

    def plotlq(self, ax, allow_large = False, **kwargs):
        """Use these settings to plot the tiles to a `matplotlib` axes.  This
        method repeatedly calls the `imshow` method, which does not lead to the
        highest quality tiling: compare with :method:`plot`.

        :param ax: The axes object to plot to.
        :param allow_large: If False (default) then don't use more than 128
          tiles.  A guard against spamming the tile server.
        :param kwargs: Other arguments which will be forwarded to the `imshow`
          matplotlib method.
        """
        if not allow_large:
            self._check_download_size()
        scale = 2 ** self.zoom
        for x in range(self.xtilemin, self.xtilemax + 1):
            for y in range(self.ytilemin, self.ytilemax + 1):
                tile = self._tile_provider.get_tile(x, y, self.zoom)
                x0, y0 = self.extent.project(x / scale, y / scale)
                x1, y1 = self.extent.project((x + 1) / scale, (y + 1) / scale)
                ax.imshow(tile, interpolation="lanczos", extent=(x0,x1,y1,y0), **kwargs)
        ax.set(xlim = self.extent.xrange, ylim = self.extent.yrange)

    def as_one_image(self, allow_large = False):
        """Use these settings to assemble tiles into a single image.

        :param ax: The axes object to plot to.
        :param tile_provider: The :class:`tiles.Tiles` object which provides
          tiles.
        :param allow_large: If False (default) then don't use more than 128
          tiles.  A guard against spamming the tile server.tile_provider
          
        :return: A :class:`PIL.Image` instance.
        """
        if not allow_large:
            self._check_download_size()
        size = self._tile_provider.tilesize
        xs = size * (self.xtilemax + 1 - self.xtilemin)
        ys = size * (self.ytilemax + 1 - self.ytilemin)
        out = _Image.new("RGB", (xs, ys))
        for x in range(self.xtilemin, self.xtilemax + 1):
            for y in range(self.ytilemin, self.ytilemax + 1):
                tile = self._tile_provider.get_tile(x, y, self.zoom)
                xo = (x - self.xtilemin) * size
                yo = (y - self.ytilemin) * size
                out.paste(tile, (xo, yo))
        return out

    def plot(self, ax, allow_large = False, **kwargs):
        """Use these settings to plot the tiles to a `matplotlib` axes.  This
        method uses :package:`pillow` to assemble the tiles into a single image
        before using `matplotlib` to display.  This leads to a better image.

        :param ax: The axes object to plot to.
        :param allow_large: If False (default) then don't use more than 128
          tiles.  A guard against spamming the tile server.
        :param kwargs: Other arguments which will be forwarded to the `imshow`
          matplotlib method.
        """
        tile = self.as_one_image(allow_large)
        scale = 2 ** self.zoom
        x0, y0 = self.extent.project(self.xtilemin / scale, self.ytilemin / scale)
        x1, y1 = self.extent.project((self.xtilemax + 1) / scale, (self.ytilemax + 1) / scale)
        ax.imshow(tile, interpolation="lanczos", extent=(x0,x1,y1,y0), **kwargs)
        ax.set(xlim = self.extent.xrange, ylim = self.extent.yrange)


##### Geopandas compatibility code

_NATIVE_LONLAT = 4326
_WEB_MERCATOR = 3857

def _parse_crs(crs):
    if crs is None:
        return _NATIVE_LONLAT
    try:
        parts = crs["init"].split(":")
        if parts[0].upper() != "EPSG":
            raise ValueError("Unknown projection '{}'".format(crs["init"]))
        code = int(parts[1])
        if code == _NATIVE_LONLAT:
            return _NATIVE_LONLAT
        if code == 3857 or code == 3785:
            return _WEB_MERCATOR
        raise ValueError("Unsupported projection '{}'".format(crs["init"]))
    except Exception:
        raise ValueError("Unknown crs data: '{}'".format(crs))

def extent_from_frame(frame, buffer=0):
    """Minimal interface to compute an :class:`Extent` from a geoPandas
    DataFrame.
    
    The dataframe must either have no projection set (`frame.crs == None`)
    or be projected in EPSG:4326, or be projected in EPSG:3857 / 3785.

    :param frame: geoDataFrame to compute bounds from.
    :param pixel_width: Aimed for width.  Height will be computed from the
      bounds.
    :param buffer: The percentage buffer to apply around the bounds.  Pass e.g.
      10 to expand the region by 10%.
    """
    proj = _parse_crs(frame.crs)
    bounds = frame.total_bounds
    if proj == _WEB_MERCATOR:
        minimum = to_lonlat(*_from_3857(bounds[0], bounds[1]))
        maximum = to_lonlat(*_from_3857(bounds[2], bounds[3]))
        bounds = [minimum[0], minimum[1], maximum[0], maximum[1]]

    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    buffer = max(width, height) * buffer / 100

    width = (bounds[2] - bounds[0]) / 2 + buffer
    height = (bounds[3] - bounds[1]) / 2 + buffer
    x, y = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
    e = Extent.from_lonlat(x - width, x + width, y - height, y + height)
    if proj == _WEB_MERCATOR:
        return e.to_project_3857()
    return e

def points_from_frame(frame):
    """Takes the geometry from the passed data frame, looks for point objects
    and extracts the coordinates.  Useful for ploting, as doing this is usually
    much faster than using the geoPandas `plot` methods.
    
    The dataframe must either have no projection set (`frame.crs == None`)
    or be projected in EPSG:4326, or be projected in EPSG:3857 / 3785.
    Returned coordinates will then either be projected to the unit square,
    or to EPSG:3857 / 3785, as appropriate.
    
    Typical usage might be `pyplot.scatter(*point_from_frame(frame))`
    
    :param frame; A :class:`GeoDataFrame` instance, or other object with a
      `geometry` property.
    
    :return: Pair (x,y) of lists of coordinates.
    """
    proj = _parse_crs(frame.crs)
    xcs, ycs = [], []
    if proj == _NATIVE_LONLAT:
        for point in frame.geometry:
            c = project(*point.coords[0])
            xcs.append(c[0])
            ycs.append(c[1])
    else:
        for point in frame.geometry:
            xcs.append(point.coords[0][0])
            ycs.append(point.coords[0][1])
    return xcs, ycs


##### (Optional) usage of pyproj

try:
    import pyproj as _pyproj
except:
    import logging
    logging.getLogger(__name__).error("Failed to load module 'pyproj'.")
    _pyproj = None

if _pyproj is not None:
    _proj3857 = _pyproj.Proj({"init":"EPSG:3857"})
    _proj3785 = _pyproj.Proj({"init":"EPSG:3785"})

def project_3785(longitude, latitude):
    """Project using :module:`pyproj` and EPSG:3785."""
    global _proj3785
    xx, yy = _proj3785(longitude, latitude)
    return _from_3857(xx, yy)

def project_3857(longitude, latitude):
    """Project using :module:`pyproj` and EPSG:3857."""
    global _proj3857
    xx, yy = _proj3857(longitude, latitude)
    return _from_3857(xx, yy)
