"""
mapping
~~~~~~~

Performs projection functions.  Map tiles are projected using the
https://en.wikipedia.org/wiki/Web_Mercator projection, which does not preserve
area or length, but is convenient.  We follow these conventions:

- Coordinates are always in the order longitude, latitude.
- Longitude varies between -180 and 180 degrees.  This is the east/west
  location from the Prime Meridian, in Greenwich, UK.  Negative is to the east.
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
    """Project the longitude / latitude to the unit square.

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
    """Inverse project from "web mercator" back to longitude, latitude.

    :param x: The x coordinate, between 0 and 1.
    :param y: The y coordinate, between 0 and 1.

    :return: A pair `(longitude, latitude)` in degrees.
    """
    longitude = x * 360 - 180
    latitude = _math.atan(_math.sinh(_math.pi * (1 - y * 2))) * 180 / _math.pi
    return (longitude, latitude)


class Extent():
    """Store details about an area of web mercator space.

    :param zoom: The (suggested) zoom level to use.  This may be larger than
      the maximum zoom a tile provider can give.
    :param xmin:
    :param xmax: The range of the x coordinates, between 0 and 1.
    :param ymin:
    :param ymax: The range of the y coordinates, between 0 and 1.
    """
    def __init__(self, zoom, xmin, xmax, ymin, ymax):
        self._zoom = zoom
        self._xmin, self._xmax = xmin, xmax
        self._ymin, self._ymax = ymin, ymax
        self._project = self._normal_project

    @property
    def zoom(self):
        """The suggested zoom level.  May be changed."""
        return self._zoom

    @zoom.setter
    def zoom(self, value):
        self._zoom = value

    @property
    def xmin(self):
        """Minimum x value of the region."""
        return self._project(self._xmin, self._ymin)[0]

    @property
    def xmax(self):
        """Maximum x value of the region."""
        return self._project(self._xmax, self._ymax)[0]

    @property
    def xrange(self):
        """A pair of (xmin, xmax)."""
        return (self.xmin, self.xmax)

    @property
    def ymin(self):
        """Minimum y value of the region."""
        return self._project(self._xmin, self._ymin)[1]

    @property
    def ymax(self):
        """Maximum y value of the region."""
        return self._project(self._xmax, self._ymax)[1]

    @property
    def yrange(self):
        """A pair of (ymax, ymin).  Inverted so as to work well with `matplotib`."""
        return (self.ymax, self.ymin)

    @property
    def xtilemin(self):
        """The least x coordinate in tile space we need to cover the region."""
        return int(2 ** self._zoom * self._xmin)

    @property
    def xtilemax(self):
        """The greatest x coordinate in tile space we need to cover the region.
        """
        return int(2 ** self._zoom * self._xmax)

    @property
    def ytilemin(self):
        """The least y coordinate in tile space we need to cover the region."""
        return int(2 ** self._zoom * self._ymin)

    @property
    def ytilemax(self):
        """The greatest y coordinate in tile space we need to cover the region.
        """
        return int(2 ** self._zoom * self._ymax)

    def _normal_project(self, x, y):
        """Project from tile space to coords."""
        return x, y

    def _3857_project(self, x, y):
        return _to_3857(x, y)

    def project_3857(self):
        """Change the coordinate system to conform to EPSG:3857 / EPSG:3785
        which can be useful when working with e.g. geoPandas (or other data
        which is projected in this way).
        """
        self._project = self._3857_project

    def _check_download_size(self):
        num_tiles = ( (self.xtilemax + 1 - self.xtilemin) *
            (self.ytilemax + 1 - self.ytilemin) )
        if num_tiles > 128:
            raise ValueError("Would use {} tiles, which is excessive.  Pass `allow_large = True` to force usage.".format(num_tiles))

    def _adjust_zoom(self, tile_provider):
        old_zoom = self.zoom
        self.zoom = min(self.zoom, tile_provider.maxzoom)
        return old_zoom

    def plot(self, ax, tile_provider, allow_large = False, **kwargs):
        """Use these settings to plot the tiles to a `matplotlib` axes.  This
        method repeatedly calls the `imshow` method, which does not lead to the
        highest quality tiling: compare with :method:`plothq`.  Will
        intelligently use the maximum zoom which the tile provider can give.

        :param ax: The axes object to plot to.
        :param tile_provider: The :class:`tiles.Tiles` object which provides
          tiles.
        :param allow_large: If False (default) then don't use more than 128
          tiles.  A guard against spamming the tile server.
        :param kwargs: Other arguments which will be forwarded to the `imshow`
          matplotlib method.
        """
        old_zoom = self._adjust_zoom(tile_provider)
        try:
            if not allow_large:
                self._check_download_size()
            scale = 2 ** self.zoom
            for x in range(self.xtilemin, self.xtilemax + 1):
                for y in range(self.ytilemin, self.ytilemax + 1):
                    tile = tile_provider.get_tile(x, y, self.zoom)
                    x0, y0 = self._project(x / scale, y / scale)
                    x1, y1 = self._project((x + 1) / scale, (y + 1) / scale)
                    ax.imshow(tile, interpolation="lanczos", extent=(x0,x1,y1,y0), **kwargs)
            ax.set(xlim = self.xrange, ylim = self.yrange)
        finally:
            self.zoom = old_zoom

    def as_one_image(self, tile_provider, allow_large = False):
        """Use these settings to assemble tiles into a single image.  Will
        intelligently use the maximum zoom which the tile provider can give.

        :param ax: The axes object to plot to.
        :param tile_provider: The :class:`tiles.Tiles` object which provides
          tiles.
        :param allow_large: If False (default) then don't use more than 128
          tiles.  A guard against spamming the tile server.
        """
        old_zoom = self._adjust_zoom(tile_provider)
        try:
            if not allow_large:
                self._check_download_size()
            tiles = []
            for x in range(self.xtilemin, self.xtilemax + 1):
                for y in range(self.ytilemin, self.ytilemax + 1):
                    tiles.append(tile_provider.get_tile(x, y, self.zoom))
            xsize, ysize = tiles[0].size
            xs = xsize * (self.xtilemax + 1 - self.xtilemin)
            ys = ysize * (self.ytilemax + 1 - self.ytilemin)
            out = _Image.new("RGB", (xs, ys))
            index = 0
            for x in range(self.xtilemin, self.xtilemax + 1):
                for y in range(self.ytilemin, self.ytilemax + 1):
                    xo = (x - self.xtilemin) * xsize
                    yo = (y - self.ytilemin) * ysize
                    out.paste(tiles[index], (xo, yo))
                    index += 1
            return out
        finally:
            self.zoom = old_zoom

    def plothq(self, ax, tile_provider, allow_large = False, **kwargs):
        """Use these settings to plot the tiles to a `matplotlib` axes.  This
        method uses :package:`pillow` to assemble the tiles into a single image
        before using `matplotlib` to display.  This leads to a better image.
        Will intelligently use the maximum zoom which the tile provider can
        give.

        :param ax: The axes object to plot to.
        :param tile_provider: The :class:`tiles.Tiles` object which provides
          tiles.
        :param allow_large: If False (default) then don't use more than 128
          tiles.  A guard against spamming the tile server.
        :param kwargs: Other arguments which will be forwarded to the `imshow`
          matplotlib method.
        """
        old_zoom = self._adjust_zoom(tile_provider)
        try:
            tile = self.as_one_image(tile_provider, allow_large)
            scale = 2 ** self.zoom
            x0, y0 = self._project(self.xtilemin / scale, self.ytilemin / scale)
            x1, y1 = self._project((self.xtilemax + 1) / scale, (self.ytilemax + 1) / scale)
            ax.imshow(tile, interpolation="lanczos", extent=(x0,x1,y1,y0), **kwargs)
            ax.set(xlim = self.xrange, ylim = self.yrange)
        finally:
            self.zoom = old_zoom


def extent(longitude_min, longitude_max, latitude_min, latitude_max,
        pixel_width, pixel_height, tile_size=256):
    """Map the box, in longitude/latitude space, to the web mercator projection
    and conform to the display box of the given size.  Calculates a suitable
    zoom level so that the tiles will be downscaled, by a factor less than 2.

    The smaller overall scale is chosen, so the returned window may be smaller
    than the requested box, in order to preserve the square aspect ratio.

    :param longitude_min:
    :param longitude_max: Range of longitude
    :param latitude_min:
    :param latitude_max: Range of latitude
    :param pixel_width: Aimed for width, in pixels
    :param pixel_height: Aimed for height, in pixels.  If None, then compute
      automatically to produce a square aspect ratio.
    :param tile_size: The size of tiles from the server, defaults to 256.

    :return: An instance of :class:`Extent` giving details of the optimal area.
    """
    xmin, ymin = project(longitude_min, latitude_max)
    xmax, ymax = project(longitude_max, latitude_min)
    xrange = xmax - xmin
    yrange = ymax - ymin

    xscale = xrange / pixel_width
    if pixel_height is not None:
        yscale = yrange / pixel_height
        scale = min(xscale, yscale)
    else:
        scale = xscale

    width = pixel_width * scale / 2
    if pixel_height is not None:
        height = pixel_height * scale / 2
    else:
        height = yrange / 2
    xmid = (xmin + xmax) / 2
    ymid = (ymin + ymax) / 2

    xmin, xmax = xmid - width, xmid + width
    ymin, ymax = ymid - height, ymid + height
    zoom = max(0, int(-_math.log2(scale * tile_size)))

    return Extent(zoom, xmin, xmax, ymin, ymax)

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

def extent_from_frame(frame, pixel_width, buffer):
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
    e = extent(x - width, x + width, y - height, y + height, pixel_width, None)
    if proj == _WEB_MERCATOR:
        e.project_3857()
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
