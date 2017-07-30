import pytest
import unittest.mock as mock

import tilemapbase.ordnancesurvery as ons
import os

def test_project():
    assert ons.project(-1.55532, 53.80474) == pytest.approx((429383.15535285, 434363.0962841))
    
def test_to_os_national_grid():
    assert ons.to_os_national_grid(-1.55532, 53.80474) == ("SE 29383 34363",
        pytest.approx(0.155352845), pytest.approx(0.096284069))
    assert ons.to_os_national_grid(-5.71808, 50.06942) == ("SW 34041 25435",
        pytest.approx(0.0757940984), pytest.approx(0.90742218543))
    assert ons.to_os_national_grid(-3.02516, 58.64389) == ("ND 40594 73345",
        pytest.approx(0.4899132418), pytest.approx(0.118179377))

def our_os_path():
    with mock.patch("os.path") as mock_path:
        def our_abspath(x):
            print(x)
            raise Exception()
        mock_path.abspath = our_abspath
        yield mock_path

def our_os_scandir():
    with mock.patch("os.scandir") as mock_scan:
        def our_scan(x):
            print(x)
            raise Exception()
        mock_scan.side_effect = our_scan
        yield mock_scan

def test_init():
    ons.init(os.path.join("tests", "test_os_map_data"))
    base = os.path.abspath(os.path.join("tests", "test_os_map_data", "data"))

    assert ons._openmap_local_lookup == {
        "AH" : os.path.join(base, "one"),
        "AA" : os.path.join(base, "two") }
    assert ons._vectormap_local_lookup == {
        "BG" : os.path.join(base, "one") }
