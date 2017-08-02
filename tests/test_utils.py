import pytest
import unittest.mock as mock

import tilemapbase.utils as utils
import PIL.Image

def test_logging():
    with mock.patch("sys.__stdout__") as stdmock:
        utils.start_logging()
        import logging
        logger = logging.getLogger("tilemapbase")
        logger.debug("Fish")

        call = stdmock.write.call_args_list[0]
        assert call[0][0].endswith("DEBUG tilemapbase - Fish")

def test_Cache():
    c = utils.Cache()

    c[5] = "Spam"
    assert 5 in c
    assert c[5] == "Spam"
    assert 6 not in c

def test_Cache_evict():
    c = utils.Cache(2)
    c[5] = "a"
    c[6] = "b"
    c[7] = "c"
    assert set(c.keys()) == {6,7}
    assert c[6] == "b"
    assert c[7] == "c"

    c[8] = "d"
    assert set(c.keys()) == {7,8}
    assert c[7] == "c"

    c[9] = "e"
    assert set(c.keys()) == {7,9}

@pytest.fixture
def random_image():
    image = PIL.Image.new("RGB", (200, 100))
    import random
    b = bytes([random.randint(0, 255) for _ in range(200*100*3)])
    image.frombytes(b)
    return image

def test_ImageCache(random_image):
    c = utils.ImageCache()
    c[5] = random_image
    c[7] = "spam"

    assert c[7] == "spam"
    image = c[5]
    assert image.mode == random_image.mode
    assert image.size == random_image.size
    assert image.tobytes() == random_image.tobytes()

@pytest.fixture
def random_pal_image():
    image = PIL.Image.new("P", (200, 100))
    import random
    b = bytes([random.randint(0, 255) for _ in range(200*100*3)])
    image.frombytes(b)
    image.putpalette([random.randint(0, 255) for _ in range(3 * 256)])
    return image

def test_ImageCache(random_pal_image):
    c = utils.ImageCache()
    c[5] = random_pal_image
    c[7] = "spam"

    assert c[7] == "spam"
    image = c[5]
    assert image.mode == random_pal_image.mode
    assert image.size == random_pal_image.size
    assert image.tobytes() == random_pal_image.tobytes()
    assert image.getpalette() == random_pal_image.getpalette()
