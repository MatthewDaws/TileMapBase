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
        return self._xmin

    @property
    def xmax(self):
        """Maximum x value of the region."""
        return self._xmax

    @property
    def xrange(self):
        """A pair of (xmin, xmax)."""
        return (self._xmin, self._xmax)

    @property
    def ymin(self):
        """Minimum y value of the region."""
        return self._ymin

    @property
    def ymax(self):
        """Maximum y value of the region."""
        return self._ymax

    @property
    def yrange(self):
        """A pair of (ymax, ymin).  Inverted so as to work well with `matplotib`."""
        return (self._ymax, self._ymin)

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

    def _check_download_size(self):
        num_tiles = ( (self.xtilemax + 1 - self.xtilemin) *
            (self.ytilemax + 1 - self.ytilemin) )
        if num_tiles > 128:
            raise ValueError("Would use {} tiles, which is excessive.  Pass `allow_large = True` to force usage.".format(num_tiles))

    def _adjust_zoom(self, tile_provider):
        old_zoom = self.zoom
        self.zoom = min(self.zoom, tile_provider.maxzoom)
        return old_zoom

    def plot(self, ax, tile_provider, allow_large = False):
        """Use these settings to plot the tiles to a `matplotlib` axes.  This
        method repeatedly calls the `imshow` method, which does not lead to the
        highest quality tiling: compare with :method:`plothq`.  Will
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
            scale = 2 ** self.zoom
            for x in range(self.xtilemin, self.xtilemax + 1):
                for y in range(self.ytilemin, self.ytilemax + 1):
                    tile = tile_provider.get_tile(x, y, self.zoom)
                    x0 = x / scale
                    x1 = (x + 1) / scale
                    y0 = y / scale
                    y1 = (y + 1) / scale
                    ax.imshow(tile, interpolation="lanczos", extent=(x0,x1,y1,y0))
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

    def plothq(self, ax, tile_provider, allow_large = False):
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
        """
        old_zoom = self._adjust_zoom(tile_provider)
        try:
            tile = self.as_one_image(tile_provider, allow_large)
            scale = 2 ** self.zoom
            x0 = self.xtilemin / scale
            x1 = (self.xtilemax + 1) / scale
            y0 = self.ytilemin / scale
            y1 = (self.ytilemax + 1) / scale
            ax.imshow(tile, interpolation="lanczos", extent=(x0,x1,y1,y0))
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
    :param pixel_height: Aimed for height, in pixels
    :param tile_size: The size of tiles from the server, defaults to 256.

    :return: An instance of :class:`Extent` giving details of the optimal area.
    """
    xmin, ymin = project(longitude_min, latitude_min)
    xmax, ymax = project(longitude_max, latitude_max)
    xrange = xmax - xmin
    yrange = ymax - ymin

    xscale = xrange / pixel_width
    yscale = yrange / pixel_height
    scale = min(xscale, yscale)

    width = pixel_width * scale / 2
    height = pixel_height * scale / 2
    xmid = (xmin + xmax) / 2
    ymid = (ymin + ymax) / 2

    xmin, xmax = xmid - width, xmid + width
    ymin, ymax = ymid - height, ymid + height
    zoom = max(0, int(-_math.log2(scale * tile_size)))

    return Extent(zoom, xmin, xmax, ymin, ymax)


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
    size = 20037508.342789244
    global _proj3785
    xx, yy = _proj3785(longitude, latitude)
    xx = 0.5 + (xx / size) * 0.5
    yy = 0.5 - (yy / size) * 0.5
    return xx, yy

def project_3857(longitude, latitude):
    """Project using :module:`pyproj` and EPSG:3857."""
    size = 20037508.342789244
    global _proj3857
    xx, yy = _proj3857(longitude, latitude)
    xx = 0.5 + (xx / size) * 0.5
    yy = 0.5 - (yy / size) * 0.5
    return xx, yy
