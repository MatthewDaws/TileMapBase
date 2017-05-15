import pytest

import tilemapbase.mapping as mapping

def test_projection():
    import random

    for _ in range(1000):
        lon = random.random() * 360 - 180
        lat = random.random() * 85 * 2 - 85

        x, y = mapping.project(lon, lat)

        xx, yy = mapping.project_3785(lon, lat)
        assert( x == pytest.approx(xx) )
        assert( y == pytest.approx(yy) )

        xx, yy = mapping.project_3857(lon, lat)
        assert( x == pytest.approx(xx) )
        assert( y == pytest.approx(yy) )

def test_to_lonlat():
    import random

    for _ in range(1000):
        lon = random.random() * 360 - 180
        lat = random.random() * 85 * 2 - 85

        x, y = mapping.project(lon, lat)
        lo, la = mapping.to_lonlat(x, y)

        assert( lon == pytest.approx(lo) )
        assert( lat == pytest.approx(la) )