"""
This is a temporary test (which will be renamed to stop it running) to check we are moving
from pyproj 1 to pyproj 2+ 

"""

import pyproj
import random

def sqrt_diff(p1, p2):
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

def test_to_web_mercator():
    p3857 = pyproj.Proj({"init": "epsg:3857"})
    p3785 = pyproj.Proj({"init": "epsg:3785"})

    #crs_4326 = pyproj.CRS("WGS84")
    crs_4326 = pyproj.CRS("epsg:4326")
    crs_3857 = pyproj.CRS("epsg:3857")
    crs_3785 = pyproj.CRS("epsg:3785")
    t1 = pyproj.Transformer.from_crs(crs_4326, crs_3857).transform
    t2 = pyproj.Transformer.from_crs(crs_4326, crs_3785).transform

    for _ in range(10000):
        x = random.random() * 360 - 180
        y = random.random() * 170 - 85
        assert( p3857(x, y) == p3785(x, y) )
        #assert( p3857(x, y) == t1(y, x) )
        assert( sqrt_diff(p3857(x, y), t1(y, x)) < 1e-16 )
        #assert( p3785(x, y) == t2(y, x) )
        assert( sqrt_diff(p3785(x, y), t2(y, x)) < 1e-16 )

def test_to_bng():
    crs_4326 = pyproj.CRS("epsg:4326")
    bng = pyproj.Proj(init="epsg:27700")
    wgs84 = pyproj.Proj(init="epsg:4326")    
    def project(lon, lat):
        return pyproj.transform(wgs84, bng, lon, lat)

    bng_new = pyproj.CRS("epsg:27700")
    project2 = pyproj.Transformer.from_crs(crs_4326, bng_new).transform

    assert( project(-1.55532, 53.80474) == project2(53.80474, -1.55532) )
    assert( project(-5.71808, 50.06942) == project2(50.06942, -5.71808) )
    assert( project(-3.02516, 58.64389) == project2(58.64389, -3.02516) )
