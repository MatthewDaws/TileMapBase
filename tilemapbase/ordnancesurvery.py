"""
ordnancesurvery
~~~~~~~

Supports raster tiles from the Ordnance Survey

"""

import math as _math
import PIL.Image as _Image

def to_os_national_grid(longitude, latitude):
    """Converts the longitude and latitude coordinates to the Ordnance Survery
    National Grid convention.
    
    :return: `(grid_code, eastings, northings)`
    """
    codes = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    x, y = project(longitude, latitude)
    
    x500, y500 = _math.floor(x / 500000), _math.floor(y / 500000)
    index = (2 + x500) + (3 - y500) * 5
    if index < 0 or index >= 25:
        raise ValueError()
    grid_code = codes[index]
    
    x100, y100 = x - 500000 * x500, y - 500000 * y500
    x100, y100 = _math.floor(x100 / 100000), _math.floor(y100 / 100000)
    index = x100 + (4 - y100) * 5
    if index < 0 or index >= 25:
        raise AssertionError()
    grid_code += codes[index]

    return grid_code, None, None


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
