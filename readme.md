[![Build Status](https://travis-ci.org/MatthewDaws/TileMapBase.svg?branch=master)](https://travis-ci.org/MatthewDaws/TileMapBase) 

# TileMapBase

Uses OpenStreetMap tiles, or other tile servers, to produce "basemaps" for use with matplotlib.  Uses a SQLite database to cache the tiles, so you can experiment with map production without re-downloading the same tiles.  Supports Open Data tiles from the
UK Ordnance Survey.


## Requirements

Pure python.  Uses [requests](http://docs.python-requests.org/en/master/) to make HTTP requests for tiles, and [pillow](https://python-pillow.org/) for image manipulation.


## Install

    pip install tilemapbase

or build from source:

    python setup.py install

or directly from GitHub:

    pip install https://github.com/MatthewDaws/TileMapBase/zipball/master


## Example

- [Example](https://github.com/MatthewDaws/TileMapBase/blob/master/notebooks/Example.ipynb) - Jupyter notebook showing examples.
- [Ordnance Survey](https://github.com/MatthewDaws/TileMapBase/blob/master/notebooks/Ordnance%20Survey.ipynb) - Ordnance survey examples.
- [Notebooks](https://github.com/MatthewDaws/TileMapBase/blob/master/notebooks/) - Other examples.


## OpenStreetMap data

OpenStreetMap Data is "© OpenStreetMap contributors”, see http://www.openstreetmap.org/copyright

Please remember that tile set usage is subject to constraints: https://operations.osmfoundation.org/policies/tiles/

## Ordnance Survery data

[Contains OS data © Crown copyright and database right (2017)](http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
