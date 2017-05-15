"""
utils
~~~~~

Some utility functions.

- Logging.  Supports configuring logging to the real stdout to support sensible
  logging when using e.g. a Jupyter notebook.

"""


def start_logging():
    import logging, sys
    logger = logging.getLogger("tilemapbase")
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler(sys.__stdout__)

    fmt = logging.Formatter("{asctime} {levelname} {name} - {message}", style="{")
    ch.setFormatter(fmt)

    logger.addHandler(ch)