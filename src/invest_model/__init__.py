"""Modèle d'aide à l'investissement en 4 piliers (graphique, financier, informations, hasard).

Organisation (voir docs/conception.md) :
- indicators/ : fonctions pures de calcul des indicateurs techniques (RSI, MACD, ...)
- pillars/    : un module par pilier, qui transforme les données en notes -2..+2
- scoring.py  : combinaison quantitatif / qualitatif puis entre piliers
- decision.py : score final -> signal ACHETER / ATTENDRE / VENDRE
- report/     : export Excel, graphiques, synthèse Markdown
"""

__version__ = "0.1.0"
