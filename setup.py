from distutils.core import setup

def find_version():
    import os
    with open(os.path.join("tilemapbase", "__init__.py")) as file:
        for line in file:
            if line.startswith("__version__"):
                start = line.index('"')
                end = line[start+1:].index('"')
                return line[start+1:end]

setup(
    name = 'tilemapbase',
    packages = ['tilemapbase'],
    version = find_version(),
    description = 'Use OpenStreetMap tiles as basemaps in python / matplotlib',
    author = 'Matt Daws',
    author_email = 'matthew.daws@gmail.com',
    url = 'https://github.com/MatthewDaws/TileMapBase',
    #download_url = 'https://github.com/MatthewDaws/TileMapBase/archive/0.1.tar.gz',
    keywords = ['basemap', 'OpenStreetMap', "tiles"],
    classifiers = []
)