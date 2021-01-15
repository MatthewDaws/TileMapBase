from setuptools import setup

def find_version():
    import os
    with open(os.path.join("tilemapbase", "__init__.py")) as file:
        for line in file:
            if line.startswith("__version__"):
                start = line.index('"')
                end = line[start+1:].index('"')
                return line[start+1:][:end]

try:
    import pypandoc
    pypandoc.convert_file("readme.md", "rst", outputfile="README.rst")
except Exception as ex:
    print("NOT REFRESHING README.rst")
    print("Exception was", ex)

with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name = 'tilemapbase',
    packages = ['tilemapbase'],
    version = find_version(),
    install_requires = ['requests', 'pillow'],
    python_requires = '>=3.6',
    description = 'Use OpenStreetMap tiles as basemaps in python / matplotlib',
    long_description = long_description,
    author = 'Matt Daws',
    author_email = 'matthew.daws@gmail.com',
    url = 'https://github.com/MatthewDaws/TileMapBase',
    license = 'MIT',
    keywords = ['basemap', 'OpenStreetMap', "tiles"],
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering :: GIS"   
    ]
)