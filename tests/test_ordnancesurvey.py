import pytest
import unittest.mock as mock

import tilemapbase.ordnancesurvery as ons
import os

def test_project():
    assert ons.project(-1.55532, 53.80474) == pytest.approx((429383.15535285, 434363.0962841))
    assert ons.project(-5.71808, 50.06942) == pytest.approx((134041.0757941, 25435.9074222))
    assert ons.project(-3.02516, 58.64389) == pytest.approx((340594.489913, 973345.118179))
    
def test_to_os_national_grid():
    assert ons.to_os_national_grid(-1.55532, 53.80474) == ("SE 29383 34363",
        pytest.approx(0.155352845), pytest.approx(0.096284069))
    assert ons.to_os_national_grid(-5.71808, 50.06942) == ("SW 34041 25435",
        pytest.approx(0.0757940984), pytest.approx(0.90742218543))
    assert ons.to_os_national_grid(-3.02516, 58.64389) == ("ND 40594 73345",
        pytest.approx(0.4899132418), pytest.approx(0.118179377))

def test_os_national_grid_to_coords():
    assert ons.os_national_grid_to_coords("SE 29383 34363") == (429383, 434363)
    assert ons.os_national_grid_to_coords("SW 34041 25435") == (134041, 25435)
    assert ons.os_national_grid_to_coords("ND 40594 73345") == (340594, 973345)
    with pytest.raises(ValueError):
        assert ons.os_national_grid_to_coords("IXJ23678412 123 12")

def test_init():
    ons.init(os.path.join("tests", "test_os_map_data"))
    base = os.path.abspath(os.path.join("tests", "test_os_map_data", "data"))

    assert ons._openmap_local_lookup == {
        "AH" : os.path.join(base, "one"),
        "AA" : os.path.join(base, "two") }
    assert ons._vectormap_local_lookup == {
        "BG" : os.path.join(base, "one") }

def test_Extent_construct():
    ons.Extent(429383, 430000, 434363, 440000)

    with pytest.raises(ValueError):
        ons.Extent(-1200000, 430000, 434363, 440000)

    ex = ons.Extent.from_centre(1000, 0, 1000, 4000)
    assert ex.xrange == (500, 1500)
    assert ex.yrange == (2000, -2000)

    ex = ons.Extent.from_centre(1000, 0, 1000, aspect=2.0)
    assert ex.xrange == (500, 1500)
    assert ex.yrange == (250, -250)
    
    ex = ons.Extent.from_centre_lonlat(-1.55532, 53.80474, 2000)
    assert ex.xrange == pytest.approx((428383.15535285, 430383.15535285))
    assert ex.yrange == pytest.approx((435363.0962841, 433363.0962841))

    ex = ons.Extent.from_lonlat(-5.71808, -1.55532, 53.80474, 50.06942)
    assert ex.xrange == pytest.approx((134041.075794, 429383.15535285))
    assert ex.yrange == pytest.approx((434363.0962841, 25435.907422))

    ex = ons.Extent.from_centre_grid("ND 40594 73345", ysize=2000, aspect=0.5)
    assert ex.xrange == (340094, 341094)
    assert ex.yrange == (974345, 972345)
