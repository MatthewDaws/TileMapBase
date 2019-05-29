import pytest
import unittest.mock as mock

import tilemapbase.ordnancesurvey as ons
import os, re

def test_project():
    assert ons.project(-1.55532, 53.80474) == pytest.approx((429383.15535285, 434363.0962841))
    assert ons.project(-5.71808, 50.06942) == pytest.approx((134041.0757941, 25435.9074222))
    assert ons.project(-3.02516, 58.64389) == pytest.approx((340594.489913, 973345.118179))

def test_to_latlon():
    assert ons.to_lonlat(429383.15535285, 434363.0962841) == pytest.approx((-1.55532, 53.80474))
    assert ons.to_lonlat(134041.0757941, 25435.9074222) == pytest.approx((-5.71808, 50.06942))

def test_to_os_national_grid():
    assert ons.to_os_national_grid(-1.55532, 53.80474) == ("SE 29383 34363",
        #pytest.approx(0.155352845), pytest.approx(0.096284069))
        pytest.approx(0.15221664), pytest.approx(0.096820819))
    assert ons.to_os_national_grid(-5.71808, 50.06942) == ("SW 34041 25435",
        #pytest.approx(0.0757940984), pytest.approx(0.90742218543))
        pytest.approx(0.073081686), pytest.approx(0.907697877))
    assert ons.to_os_national_grid(-3.02516, 58.64389) == ("ND 40594 73345",
        #pytest.approx(0.4899132418), pytest.approx(0.118179377))
        pytest.approx(0.48627711), pytest.approx(0.118587372))

    with pytest.raises(ValueError):
        print(ons.to_os_national_grid(-10, 10))

def test_os_national_grid_to_coords():
    assert ons.os_national_grid_to_coords("SE 29383 34363") == (429383, 434363)
    assert ons.os_national_grid_to_coords("SW 34041 25435") == (134041, 25435)
    assert ons.os_national_grid_to_coords("ND 40594 73345") == (340594, 973345)
    with pytest.raises(ValueError):
        assert ons.os_national_grid_to_coords("IXJ23678412 123 12")

def test_init():
    ons.init(os.path.join("tests", "test_os_map_data"))
    base = os.path.abspath(os.path.join("tests", "test_os_map_data", "data"))

    assert ons._lookup["openmap_local"] == {
        "AH" : os.path.join(base, "one"),
        "AA" : os.path.join(base, "two") }
    assert ons._lookup["vectormap_district"] == {
        "BG" : os.path.join(base, "one") }
    mini = os.path.abspath(os.path.join("tests", "test_os_map_data", "mini"))
    assert ons._lookup["miniscale"] == {"MiniScale_one.tif" : mini,
        "MiniScale_two.tif" : mini}

def test__separate_init():
    base = os.path.abspath(os.path.join("tests", "test_os_map_data", "data"))
    callback = mock.Mock()
    ons._separate_init(re.compile("^[A-Za-z]{2}\d\d\.tif$"),
        os.path.join("tests", "test_os_map_data"),
        callback)
    assert callback.call_args_list == [mock.call("BG76.tif", os.path.join(base, "one"))]

@pytest.fixture
def omll():
    files = {"openmap_local" : {"SE" : "se_dir"}}
    with mock.patch("tilemapbase.ordnancesurvey._lookup", new=files):
        yield None

@pytest.fixture
def image_mock():
    with mock.patch("tilemapbase.ordnancesurvey._Image") as i:
        yield i

def test_OpenMapLocal(omll, image_mock):
    oml = ons.OpenMapLocal()

    oml("SE 12345 54321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "SE15SW.tif"))

    oml("SE 16345 54321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "SE15SE.tif"))

    oml("SE 22345 55321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "SE25NW.tif"))

    oml("SE 15345 75321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "SE17NE.tif"))

    with pytest.raises(ons.TileNotFoundError):
        oml("SF 1456 12653")

    with pytest.raises(ValueError):
        oml("SF 145612653")

    assert oml.tilesize == 5000
    assert oml.size_in_meters == 5000

@pytest.fixture
def vmd():
    files = {"vectormap_district" : {"SE" : "se_dir"}}
    with mock.patch("tilemapbase.ordnancesurvey._lookup", new=files):
        yield None

def test_VectorMapDistrict(vmd, image_mock):
    oml = ons.VectorMapDistrict()

    oml("SE 12345 54321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "SE15.tif"))

    oml("SE 16345 54321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "SE15.tif"))

    oml("SE 22345 55321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "SE25.tif"))

    oml("SE 15345 75321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "SE17.tif"))

    with pytest.raises(ons.TileNotFoundError):
        oml("SF 1456 12653")

    with pytest.raises(ValueError):
        oml("SF 145612653")

    assert oml.tilesize == 4000
    assert oml.size_in_meters == 10000

@pytest.fixture
def tfk():
    files = {"25k_raster" : {"SE" : "se_dir"}}
    with mock.patch("tilemapbase.ordnancesurvey._lookup", new=files):
        yield None

def test_TwentyFiveRaster(tfk, image_mock):
    oml = ons.TwentyFiveRaster()

    oml("SE 12345 54321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "se15.tif"))

    oml("SE 16345 54321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "se15.tif"))

    oml("SE 22345 55321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "se25.tif"))

    oml("SE 15345 75321")
    image_mock.open.assert_called_with(os.path.join("se_dir", "se17.tif"))

    with pytest.raises(ons.TileNotFoundError):
        oml("SF 1456 12653")

    with pytest.raises(ValueError):
        oml("SF 145612653")

    assert oml.tilesize == 4000
    assert oml.size_in_meters == 10000

@pytest.fixture
def tfs():
    files = {"250k_raster" : "250kdir"}
    with mock.patch("tilemapbase.ordnancesurvey._lookup", new=files):
        yield None

def test_TwoFiftyScale(tfs, image_mock):
    ts = ons.TwoFiftyScale()
    assert ts.tilesize == 4000
    assert ts.size_in_meters == 100000

    ts("SE 1234 43231")
    image_mock.open.assert_called_with(os.path.join("250kdir", "SE.tif"))

def mock_dir_entry(name):
    m = mock.Mock()
    m.is_dir.return_value = False
    m.is_file.return_value = True
    m.name = name
    return m

def test_MasterMap_init():
    with mock.patch("os.path.abspath") as abspath_mock:
        abspath_mock.return_value = "spam"
        with mock.patch("os.scandir") as scandir_mock:
            scandir_mock.return_value = [mock_dir_entry("eggs"),
                mock_dir_entry("se3214.tif"), mock_dir_entry("sD1234.tif"),
                mock_dir_entry("sa6543.png")]
            
            ons.MasterMap.init("test")

            abspath_mock.assert_called_with("test")
            scandir_mock.assert_called_with("spam")
    
    assert set(ons.MasterMap.found_tiles()) == {("se", "32", "14"),
        ("sD", "12", "34"), ("sa", "65", "43")}

    ons._lookup["MasterMap"] == {"spam" : ["se3214.tif", "sD1234.tif", "sa6543.png"]}

@pytest.fixture
def mm_dir():
    files = {"MasterMap" : {"spam" : ["sA1342.png"]}}
    with mock.patch("tilemapbase.ordnancesurvey._lookup", new=files):
        yield None

def test_MasterMap(mm_dir, image_mock):
    source = ons.MasterMap()
    with pytest.raises(ons.TileNotFoundError):
        source("SD 12345 65432")

    tile = source("SA 13876 42649")
    assert tile == image_mock.open.return_value
    image_mock.open.assert_called_with(os.path.join("spam", "sA1342.png"))

    assert source.tilesize == 3200
    assert source.size_in_meters == 1000

    source.tilesize = 1243
    assert source.tilesize == 1243

@pytest.fixture
def mini():
    files = {"miniscale" : {"mini_one.tif" : "dirone", "mini_two.tif" : "dirtwo"}}
    with mock.patch("tilemapbase.ordnancesurvey._lookup", new=files):
        yield None

def test_MiniScale(mini, image_mock):
    ts = ons.MiniScale()
    assert ts.tilesize == 1000
    assert ts.size_in_meters == 100000
    assert set(ts.filenames) == {"mini_one.tif", "mini_two.tif"}
    ts.filename = "mini_two.tif"
    assert ts.filename == "mini_two.tif"

    tile = ts("SE 1234 43231")
    image_mock.open.assert_called_with(os.path.join("dirtwo", "mini_two.tif"))
    image = image_mock.open.return_value
    image.crop.assert_called_with((4000,8000,5000,9000))
    assert tile is image.crop.return_value

    assert ts.bounding_box == (0, 0, 700000, 1300000)

def test_MiniScale_cache(mini, image_mock):
    ts = ons.MiniScale()
    ts.filename = "mini_two.tif"
    tile = ts("SE 1234 43231")
    image_mock.reset_mock()
    ts("SD 1 2")
    assert image_mock.open.call_args_list == []

    ts.filename = "mini_one.tif"
    ts("SD 1 2")
    image_mock.open.assert_called_with(os.path.join("dirone", "mini_one.tif"))

@pytest.fixture
def overview():
    files = {"overview" : {"mini_one.tif" : "dirone", "mini_two.tif" : "dirtwo"}}
    with mock.patch("tilemapbase.ordnancesurvey._lookup", new=files):
        yield None

def test_OverView(overview, image_mock):
    ts = ons.OverView()
    assert ts.tilesize == 100
    assert ts.size_in_meters == 50000
    ts.filename = "mini_one.tif"
    tile = ts("SD 1 2")
    assert image_mock.open.call_args_list == [mock.call(os.path.join("dirone", "mini_one.tif"))]
    assert tile == image_mock.open.return_value.crop.return_value

    # Should cache...
    image_mock.reset_mock()
    ts("SD 1 2")
    assert image_mock.open.call_args_list == []

    ts.tilesize = 50
    assert ts.size_in_meters == 25000

    with pytest.raises(ValueError):
        ts.tilesize = 5.5

    with pytest.raises(ValueError):
        ts.tilesize = 0

def test_Extent_construct():
    ex = ons.Extent.from_centre(1000, 0, 1000, 4000)
    assert ex.xrange == (500, 1500)
    assert ex.yrange == (-2000, 2000)

    ex = ons.Extent.from_centre(1000, 0, 1000, aspect=2.0)
    assert ex.xrange == (500, 1500)
    assert ex.yrange == (-250, 250)
    
    ex = ons.Extent.from_centre_lonlat(-1.55532, 53.80474, 2000)
    assert ex.xrange == pytest.approx((428383.15535285, 430383.15535285))
    assert ex.yrange == pytest.approx((433363.0962841, 435363.0962841))

    ex = ons.Extent.from_lonlat(-5.71808, -1.55532, 53.80474, 50.06942)
    assert ex.xrange == pytest.approx((134041.075794, 429383.15535285))
    assert ex.yrange == pytest.approx((25435.907422, 434363.0962841))

    ex = ons.Extent.from_centre_grid("ND 40594 73345", ysize=2000, aspect=0.5)
    assert ex.xrange == (340094, 341094)
    assert ex.yrange == (972345, 974345)

def test_Extent_mutations():
    # 1000 x 5000
    ex = ons.Extent(1000, 2000, 4000, 9000)
    ex1 = ex.with_centre(10000, 20000)
    assert ex1.xrange == (10000-500, 10000+500)
    assert ex1.yrange == (20000-2500, 20000+2500)

    ex2 = ex.with_centre_lonlat(-3.02516, 58.64389) 
    assert ex2.xrange == pytest.approx((340094.489913, 341094.489913))
    assert ex2.yrange == pytest.approx((973345.118179-2500, 973345.118179+2500))

    ex3 = ex.to_aspect(2.0)
    assert ex3.xrange == (1000, 2000)
    assert ex3.yrange == (6500-250, 6500+250)
    ex3 = ex.to_aspect(0.5)
    assert ex3.xrange == (1000, 2000)
    assert ex3.yrange == (6500-1000, 6500+1000)
    ex3 = ex.to_aspect(0.1)
    assert ex3.xrange == (1250, 1750)
    assert ex3.yrange == (4000, 9000)

    ex4 = ex.with_absolute_translation(100, 200)
    assert ex4.xrange == (1100, 2100)
    assert ex4.yrange == (4200, 9200)

    ex5 = ex.with_translation(0.5, 1)
    assert ex5.xrange == (1500, 2500)
    assert ex5.yrange == (9000, 14000)
    
    ex6 = ex.with_scaling(0.5)
    assert ex6.xrange == (1500 - 1000, 2500)
    assert ex6.yrange == (6500 - 5000, 6500 + 5000)

@pytest.fixture
def source():
    s = mock.Mock()
    s.size_in_meters = 1000
    s.tilesize = 2000
    return s

def test_TileScalar(source, image_mock):
    ts = ons.TileScalar(source, 500)
    assert ts.tilesize == 500
    assert ts.size_in_meters == 1000
    assert ts.bounding_box == source.bounding_box

    tile = ts("SN 1234 54321")
    source.assert_called_with("SN 1234 54321")
    assert tile == source.return_value.convert.return_value.resize.return_value
    source.return_value.convert.assert_called_with("RGB")
    source.return_value.convert.return_value.resize.assert_called_with((500, 500), image_mock.LANCZOS)

def test_Plotter_plotlq(source):
    ex = ons.Extent(1100, 1900, 4200, 5500)
    plotter = ons.Plotter(ex, source)
    ax = mock.Mock()
    plotter.plotlq(ax, bob="fish")

    assert source.call_args_list == [
        mock.call("SV 1000 4000"), mock.call("SV 1000 5000") ]
    assert ax.imshow.call_args_list == [
        mock.call(source.return_value, interpolation="lanczos", extent=(1000, 2000, 4000, 5000), bob="fish"),
        mock.call(source.return_value, interpolation="lanczos", extent=(1000, 2000, 5000, 6000), bob="fish")
        ]

def test_Plotter_as_one_image(source, image_mock):
    ex = ons.Extent(1100, 1900, 4200, 5500)
    plotter = ons.Plotter(ex, source)
    ax = mock.Mock()
    out = plotter.as_one_image()

    assert source.call_args_list == [
        mock.call("SV 1000 4000"), mock.call("SV 1000 5000") ]
    image_mock.new.assert_called_with("RGB", (2000, 4000))
    im = image_mock.new.return_value
    assert out is im
    assert im.paste.call_args_list == [
        mock.call(source.return_value, (0, 2000)),
        mock.call(source.return_value, (0, 0))
        ]

def test_Plotter_plot(source, image_mock):
    ex = ons.Extent(1100, 1900, 4200, 5500)
    plotter = ons.Plotter(ex, source)
    ax = mock.Mock()
    plotter.plot(ax, bob="fish")

    assert source.call_args_list == [
        mock.call("SV 1000 4000"), mock.call("SV 1000 5000") ]
    assert ax.imshow.call_args_list == [
        mock.call(image_mock.new.return_value, interpolation="lanczos", extent=(1000, 2000, 4000, 6000), bob="fish"),
        ]

def test_Plotter_ignore_errors(source, image_mock):
    source.side_effect = Exception
    ex = ons.Extent(1100, 1900, 4200, 5500)
    plotter = ons.Plotter(ex, source)
    ax = mock.Mock()
    plotter.plotlq(ax, bob="fish")

    assert ax.imshow.call_args_list == [
        mock.call(source.blank.return_value, interpolation="lanczos", extent=(1000, 2000, 4000, 5000), bob="fish"),
        mock.call(source.blank.return_value, interpolation="lanczos", extent=(1000, 2000, 5000, 6000), bob="fish")
        ]

def test_TileSplitter(source):
    source.tilesize = 1000
    source.size_in_meters = 500
    with pytest.raises(ValueError):
        ons.TileSplitter(source, 3)

    ts = ons.TileSplitter(source, 500)
    assert ts.tilesize == 500
    assert ts.size_in_meters == 250

    tile = ts("SV 1000 4000")
    assert source.call_args_list == [mock.call("SV 1000 4000")]
    image = source.return_value
    assert image.crop.call_args_list == [mock.call((0,0,500,500)),
        mock.call((0,500,500,1000)), mock.call((500,0,1000,500)),
        mock.call((500,500,1000,1000))]
    assert tile is image.crop.return_value

    # Should be cached...
    source.reset_mock()
    tile = ts("SV 1250 4000")
    assert source.call_args_list == []
