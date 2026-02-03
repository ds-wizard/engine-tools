"""DSW Template Development Kit

Template Development Kit for `Data Stewardship Wizard`_.

.. _Data Stewardship Wizard:
   https://ds-wizard.org

"""
from . import consts
from .cli import main


__app__ = consts.APP
__version__ = consts.VERSION

__all__ = ['__app__', '__version__', 'main']
