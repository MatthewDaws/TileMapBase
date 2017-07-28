import pytest

import tilemapbase.ordnancesurvery as ons

def test_project():
    assert ons.project(-1.55532, 53.80474) == pytest.approx((429383.15535285, 434363.0962841))
    
def test_to_os_national_grid():
    assert ons.to_os_national_grid(-1.55532, 53.80474) == ("SE", None, None)
    