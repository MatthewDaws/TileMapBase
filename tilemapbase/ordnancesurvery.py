"""
ordnancesurvery
~~~~~~~

Supports raster tiles from the Ordnance Survey.  We support the (freely
downloadable) "OS OpenMap Local" and "OS VectorMap Local".

- "OS OpenMap Local" has file-names like "SE00NE.tif" where "SE" is the "grid
  code", "00" is the first digit of the x and y grid reference, and "NE" means
  "North East" i.e. the upper left part of the "00" grid
- "OS VectorMap Local" has file-name like "SE00.tif" with the same format, but
  2 times less resolution in both coorindates.

"""

import math as _math
import os as _os
import re as _re
import PIL.Image as _Image

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
    
    :return: `(grid_code, eastings, northings)`
    """
    grid_code, x, y = _code_grid_residual(longitude, latitude)
    xx, yy = _math.floor(x), _math.floor(y)
    return "{} {} {}".format(grid_code, xx, yy), x - xx, y - yy

def _code_grid_residual(longitude, latitude):
    codes = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    x, y = project(longitude, latitude)
    
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
