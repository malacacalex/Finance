"""Permet `python -m invest_model ...` sans installer la commande `invest`."""

import sys

from .cli import main

sys.exit(main())
