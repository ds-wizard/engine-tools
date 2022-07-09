"""DSW Template Development Kit

Template Development Kit for `Data Stewardship Wizard`_.

.. _Data Stewardship Wizard:
   https://ds-wizard.org

"""
from .cli import main
from .consts import APP, VERSION

__app__ = APP
__version__ = VERSION

__all__ = ['__app__', '__version__', 'main']
