import pytest
import unittest.mock as mock

import tilemapbase.mapping as mapping

def test_projection_against_pyproj():
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

def test_project_and_back_to_lonlat():
    import random

    for _ in range(1000):
        lon = random.random() * 360 - 180
        lat = random.random() * 85 * 2 - 85

        x, y = mapping.project(lon, lat)
        lo, la = mapping.to_lonlat(x, y)

        assert( lon == pytest.approx(lo) )
        assert( lat == pytest.approx(la) )



##### Extent class

def test_Extent_construct():
    mapping.Extent(0.2, 0.5, 0.3, 0.4)
    mapping.Extent(-0.8, -0.5, 0.3, 0.4)
    with pytest.raises(ValueError):
        mapping.Extent(0.5, 0.2, 0.3, 0.4)
    with pytest.raises(ValueError):
        mapping.Extent(0.2, 0.5, 0.4, 0.3)
    with pytest.raises(ValueError):
        mapping.Extent(0.2, 0.5, -0.1, 0.4)
    with pytest.raises(ValueError):
        mapping.Extent(0.2, 0.5, 0.3, 1.1)

def assert_standard_properties(ex):
    assert ex.xmin == pytest.approx(0.2)
    assert ex.xmax == pytest.approx(0.5)
    assert ex.width == pytest.approx(0.3)
    assert ex.xrange == pytest.approx((0.2, 0.5))
    assert ex.ymin == pytest.approx(0.3)
    assert ex.ymax == pytest.approx(0.4)
    assert ex.height == pytest.approx(0.1)
    assert ex.yrange == pytest.approx((0.4, 0.3))
    assert str(ex) == "Extent((0.2,0.3)->(0.5,0.4) projected as normal)"

def test_Extent_properties():
    ex = mapping.Extent(0.2, 0.5, 0.3, 0.4)
    assert_standard_properties(ex)

def test_Extent_from_centre():
    ex = mapping.Extent.from_centre(0.3, 0.2, xsize=0.1)
    assert ex.xrange == pytest.approx((0.25, 0.35))
    assert ex.yrange == pytest.approx((0.25, 0.15))
    ex = mapping.Extent.from_centre(0.3, 0.2, xsize=0.1, aspect=2)
    assert ex.xrange == pytest.approx((0.25, 0.35))
    assert ex.yrange == pytest.approx((0.225, 0.175))
    ex = mapping.Extent.from_centre(0.3, 0.2, ysize=0.1)
    assert ex.xrange == pytest.approx((0.25, 0.35))
    assert ex.yrange == pytest.approx((0.25, 0.15))
    ex = mapping.Extent.from_centre(0.3, 0.2, ysize=0.1, aspect=2)
    assert ex.xrange == pytest.approx((0.2, 0.4))
    assert ex.yrange == pytest.approx((0.25, 0.15))
    ex = mapping.Extent.from_centre(0.3, 0.2, xsize=0.3, ysize=0.1)
    assert ex.xrange == pytest.approx((0.15, 0.45))
    assert ex.yrange == pytest.approx((0.25, 0.15))

def test_Extent_from_lonlat():
    x, y = mapping.project(32, -10)
    ex = mapping.Extent.from_centre_lonlat(32, -10, xsize=0.2)
    assert ex.xrange == pytest.approx((x-0.1, x+0.1))
    assert ex.yrange == pytest.approx((y+0.1, y-0.1))

    xx, yy = mapping.project(34, -12)
    ex = mapping.Extent.from_lonlat(32, 34, -12, -10)
    assert ex.xrange == pytest.approx((x, xx))
    assert ex.yrange == pytest.approx((yy, y))

def test_Extent_from_3857():
    x, y = mapping._to_3857(0.2, 0.3)
    ex = mapping.Extent.from_centre(0.2, 0.3, xsize=0.1).to_project_3857()
    ex1 = mapping.Extent.from_centre_3857(x, y, xsize=0.1)
    assert ex1.xrange == pytest.approx(ex.xrange)
    assert ex1.yrange == pytest.approx(ex.yrange)

    xx, yy = mapping._to_3857(0.25, 0.4)
    ex = mapping.Extent.from_3857(x, xx, y, yy)
    ex1 = mapping.Extent(0.2, 0.25, 0.3, 0.4).to_project_3857()
    assert ex1.xrange == pytest.approx(ex.xrange)
    assert ex1.yrange == pytest.approx(ex.yrange)

def test_Extent_projection():
    ex = mapping.Extent(0.2, 0.5, 0.3, 0.4)
    ex1 = ex.to_project_3857()
    ex2 = ex.to_project_web_mercator()
    assert_standard_properties(ex)
    assert_standard_properties(ex2)
    x, y = mapping._to_3857(0.2, 0.3)
    xx, yy = mapping._to_3857(0.5, 0.4)
    assert ex1.xmin == pytest.approx(x)
    assert ex1.xmax == pytest.approx(xx)
    assert ex1.width == pytest.approx(xx - x)
    assert ex1.xrange == pytest.approx((x, xx))
    assert ex1.ymin == pytest.approx(y)
    assert ex1.ymax == pytest.approx(yy)
    assert ex1.height == pytest.approx(yy - y)
    assert ex1.yrange == pytest.approx((yy, y))
    assert str(ex1).endswith(" projected as epsg:3857)")

def test_Extent_with_centre():
    ex = mapping.Extent(0.2, 0.5, 0.3, 0.4)
    ex1 = ex.with_centre(0.3, 0.4)
    assert ex1.xrange == pytest.approx((.15, .45))
    assert ex1.yrange == pytest.approx((.45, .35))
    ex1 = ex.with_centre(0, 0.4)
    assert ex1.xrange == pytest.approx((-.15, .15))
    assert ex1.yrange == pytest.approx((.45, .35))
    ex1 = ex.with_centre(0, 0.01)
    assert ex1.xrange == pytest.approx((-.15, .15))
    assert ex1.yrange == pytest.approx((0.1, 0))
    ex1 = ex.with_centre(0, 0.98)
    assert ex1.xrange == pytest.approx((-.15, .15))
    assert ex1.yrange == pytest.approx((1, 0.9))

def test_Extent_with_centre_lonlat():
    x, y = mapping.project(32, 15)
    ex = mapping.Extent(0.2, 0.4, 0.3, 0.5)
    ex1 = ex.with_centre_lonlat(32, 15)
    assert ex1.xrange == pytest.approx((x-.1, x+.1))
    assert ex1.yrange == pytest.approx((y+.1, y-.1))

def test_Extent_to_aspect():
    ex = mapping.Extent(0.2, 0.5, 0.3, 0.4)
    
    ex1 = ex.to_aspect(3)
    assert ex1.xrange == pytest.approx(ex.xrange)
    assert ex1.yrange == pytest.approx(ex.yrange)

    ex1 = ex.to_aspect(1)
    assert ex1.xrange == pytest.approx((0.3, 0.4))
    assert ex1.yrange == pytest.approx(ex.yrange)

    ex1 = ex.to_aspect(6)
    assert ex1.xrange == pytest.approx(ex.xrange)
    assert ex1.yrange == pytest.approx((0.375, 0.325))

def test_Extent_with_absolute_translation():
    ex = mapping.Extent(0.2, 0.5, 0.3, 0.4)
    ex1 = ex.with_absolute_translation(0.6, 0.2)
    assert ex1.xrange == pytest.approx((0.8, 1.1))
    assert ex1.yrange == pytest.approx((0.6, 0.5))

    ex1 = ex.with_absolute_translation(0.6, 0.7)
    assert ex1.xrange == pytest.approx((0.8, 1.1))
    assert ex1.yrange == pytest.approx((1, 0.9))

    ex1 = ex.with_absolute_translation(0.6, -0.4)
    assert ex1.xrange == pytest.approx((0.8, 1.1))
    assert ex1.yrange == pytest.approx((.1, 0))

def test_Extent_with_translation():
    ex = mapping.Extent(0.2, 0.5, 0.3, 0.4)
    ex1 = ex.with_translation(2, -1)
    assert ex1.xrange == pytest.approx((0.8, 1.1))
    assert ex1.yrange == pytest.approx((0.3, 0.2))

def test_Extent_with_scaling():
    ex = mapping.Extent(0.2, 0.5, 0.3, 0.4)
    ex1 = ex.with_scaling(1)
    assert ex1.xrange == pytest.approx(ex1.xrange)
    assert ex1.yrange == pytest.approx(ex1.yrange)

    ex1 = ex.with_scaling(2)
    assert ex1.xrange == pytest.approx((0.35 - 0.075, 0.35 + 0.075))
    assert ex1.yrange == pytest.approx((0.375, 0.325))




###### Plotter tests

@pytest.fixture
def ex():
    return mapping.Extent(0.2, 0.5, 0.3, 0.4)

@pytest.fixture
def tile_provider():
    tp = mock.Mock()
    tp.maxzoom = 19
    tp.tilesize = 256
    return tp

def test_Plotter_constructs(ex, tile_provider):
    with pytest.raises(ValueError):
        mapping.Plotter(ex, tile_provider)
    with pytest.raises(ValueError):
        mapping.Plotter(ex, tile_provider, zoom=2, width=100)
    with pytest.raises(ValueError):
        mapping.Plotter(ex, tile_provider, zoom=2, height=100)

    plot = mapping.Plotter(ex, tile_provider, zoom=10)
    assert plot.zoom == 10
    assert plot.extent is ex
    assert plot.extent_in_web_mercator.xrange == ex.xrange
    assert plot.extent_in_web_mercator.yrange == ex.yrange

    assert plot.xtilemin == int(1024*0.2)
    assert plot.xtilemax == int(1024*0.5)
    assert plot.ytilemin == int(1024*0.3)
    assert plot.ytilemax == int(1024*0.4)

def test_Plotter_auto_zoom(ex, tile_provider):
    tile_provider.tilesize = 256
    plot = mapping.Plotter(ex, tile_provider, width=100)
    # Tile is 256 wide, needed width is 0.3, or 76.8
    # Each zoom level doubles that
    assert plot.zoom == 1
    plot = mapping.Plotter(ex, tile_provider, width=1000)
    assert plot.zoom == 4
    plot = mapping.Plotter(ex, tile_provider, width=76)
    assert plot.zoom == 0
    plot = mapping.Plotter(ex, tile_provider, width=77)
    assert plot.zoom == 1

    tile_provider.tilesize = 512
    plot = mapping.Plotter(ex, tile_provider, width=1000)
    assert plot.zoom == 3
    plot = mapping.Plotter(ex, tile_provider, width=5033164)
    assert plot.zoom == 15
    plot = mapping.Plotter(ex, tile_provider, width=5033165)
    assert plot.zoom == 16

    plot = mapping.Plotter(ex, tile_provider, height=1000)
    assert plot.zoom == 5
    plot = mapping.Plotter(ex, tile_provider, width=1000, height=1000)
    assert plot.zoom == 5

def imshow_calls_to_list(ax_mock):
    out = []
    for call in ax_mock.imshow.call_args_list:
        assert len(call[0]) == 1
        assert call[1]["interpolation"] == "lanczos"
        out.append((call[0][0], call[1]["extent"]))
    return out

def test_Plotter_plotlq_1x1(ex, tile_provider):
    plot = mapping.Plotter(ex, tile_provider, width=50)
    ax = mock.Mock()
    plot.plotlq(ax)

    assert tile_provider.get_tile.call_args_list == [ mock.call(0,0,0) ]
    tile, extent = imshow_calls_to_list(ax)[0]
    assert tile == tile_provider.get_tile.return_value
    assert extent == pytest.approx((0,1,1,0))
    ax.set.assert_called_with(xlim=(0.2, 0.5), ylim=(0.4, 0.3))

def test_Plotter_plotlq_2x2(ex, tile_provider):
    plot = mapping.Plotter(ex, tile_provider, width=100)
    ax = mock.Mock()
    plot.plotlq(ax)

    assert tile_provider.get_tile.call_args_list == [ mock.call(0,0,1), mock.call(1,0,1) ]
    imshow = imshow_calls_to_list(ax)
    assert len(imshow) == 2
    tile, extent = imshow[0]
    assert tile == tile_provider.get_tile.return_value
    assert extent == pytest.approx((0,0.5,0.5,0))
    tile, extent = imshow[1]
    assert tile == tile_provider.get_tile.return_value
    assert extent == pytest.approx((0.5,1,0.5,0))
    ax.set.assert_called_with(xlim=(0.2, 0.5), ylim=(0.4, 0.3))

@pytest.fixture
def new_image():
    with mock.patch("PIL.Image.new") as image_mock:
        yield image_mock

def test_Plotter_as_one_image_1x1(ex, tile_provider, new_image):
    plot = mapping.Plotter(ex, tile_provider, width=50)
    image = plot.as_one_image()

    assert new_image.called_with("RGB", (256,256))
    assert image == new_image.return_value
    assert tile_provider.get_tile.call_args_list == [ mock.call(0,0,0) ]
    tile = tile_provider.get_tile.return_value
    image.paste.assert_called_with(tile, (0,0))

def test_Plotter_as_one_image_2x2(ex, tile_provider, new_image):
    plot = mapping.Plotter(ex, tile_provider, width=100)
    image = plot.as_one_image()

    assert new_image.called_with("RGB", (512,256))
    assert image == new_image.return_value
    assert tile_provider.get_tile.call_args_list == [ mock.call(0,0,1), mock.call(1,0,1) ]
    tile = tile_provider.get_tile.return_value
    assert image.paste.call_args_list == [ mock.call(tile,(0,0)), mock.call(tile,(256,0)) ]

def test_Plotter_plot_2x2(ex, tile_provider, new_image):
    plot = mapping.Plotter(ex, tile_provider, width=100)
    ax = mock.Mock()
    plot.plot(ax)

    image = new_image.return_value
    imshow = imshow_calls_to_list(ax)
    assert len(imshow) == 1
    tile, extent = imshow[0]
    assert tile == image
    assert extent == pytest.approx((0,1,0.5,0))
    ax.set.assert_called_with(xlim=(0.2, 0.5), ylim=(0.4, 0.3))

def test_Plotter_too_many_tiles(ex, tile_provider):
    plot = mapping.Plotter(ex, tile_provider, width=10000)
    with pytest.raises(ValueError):
        plot.plot(mock.Mock())

def test_Plotter_plot_epsg(ex, tile_provider, new_image):
    ex = ex.to_project_3857()
    plot = mapping.Plotter(ex, tile_provider, width=100)
    ax = mock.Mock()
    plot.plot(ax)

    image = new_image.return_value
    imshow = imshow_calls_to_list(ax)
    assert len(imshow) == 1
    tile, extent = imshow[0]
    assert tile == image
    x, y = mapping._to_3857(0,0)
    xx, yy = mapping._to_3857(1,0.5)
    assert extent == pytest.approx((x,xx,yy,y))
    kwargs = ax.set.call_args_list[0][1]
    x, y = mapping._to_3857(0.2,0.3)
    xx, yy = mapping._to_3857(0.5,0.4)
    kwargs["xlim"] == pytest.approx((x,xx))
    kwargs["ylim"] == pytest.approx((yy,y))
