|Build Status|

TileMapBase
===========

Uses OpenStreetMap tiles, or other tile servers, to produce "basemaps"
for use with matplotlib. Uses a SQLite database to cache the tiles, so
you can experiment with map production without re-downloading the same
tiles. Supports Open Data tiles from the UK Ordnance Survey.

Requirements
------------

Pure python. Uses
`requests <http://docs.python-requests.org/en/master/>`__ to make HTTP
requests for tiles, and `pillow <https://python-pillow.org/>`__ for
image manipulation.

Install
-------

::

    pip install tilemapbase

or build from source:

::

    python setup.py install

or directly from GitHub:

::

    pip install https://github.com/MatthewDaws/TileMapBase/zipball/master

Example
-------

-  `Example <https://github.com/MatthewDaws/TileMapBase/blob/master/notebooks/Example.ipynb>`__
   - Jupyter notebook showing examples.
-  `Ordnance
   Survey <https://github.com/MatthewDaws/TileMapBase/blob/master/notebooks/Ordnance%20Survey.ipynb>`__
   - Ordnance survey examples.
-  `Notebooks <https://github.com/MatthewDaws/TileMapBase/blob/master/notebooks/>`__
   - Other examples.

OpenStreetMap data
------------------

OpenStreetMap Data is "© OpenStreetMap contributors”, see
http://www.openstreetmap.org/copyright

Please remember that tile set usage is subject to constraints:
https://operations.osmfoundation.org/policies/tiles/

-  As of 25/05/2019 `OSM requires a user agent for all
   requests <https://operations.osmfoundation.org/policies/tiles/>`__,
   with a warning "Faking another app’s User-Agent WILL get you
   blocked." We hence default to using "TileMapBase" as a user agent.

Ordnance Survery data
---------------------

`Contains OS data © Crown copyright and database right
(2017) <http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/>`__

.. |Build Status| image:: https://travis-ci.org/MatthewDaws/TileMapBase.svg?branch=master
   :target: https://travis-ci.org/MatthewDaws/TileMapBase
