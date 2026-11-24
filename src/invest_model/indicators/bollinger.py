"""Bandes de Bollinger.

Source : ABC Bourse, « Les Bandes de Bollinger »
https://www.abcbourse.com/apprendre/11_lecon4.html
Réglage traditionnel cité par la leçon : moyenne mobile 20 séances, +/- 2 écarts-types.
Lecture de la leçon :
- sortie d'une bande dans le sens de la tendance = continuation ;
- sortie puis réintégration des bandes = figure de retournement ;
- resserrement des bandes = un mouvement important se prépare.
"""

import pandas as pd

from .moving_averages import sma


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    """Bandes de Bollinger : milieu (MM n), haute, basse, %B et largeur.

    Écart-type de POPULATION (division par n, ddof=0), comme dans la définition
    de John Bollinger.
    - %B = (C - basse) / (haute - basse) : 0 sur la bande basse, 1 sur la haute ;
    - largeur = (haute - basse) / milieu : sert à repérer les resserrements.
    """
    mid = sma(close, n)
    std = close.rolling(window=n, min_periods=n).std(ddof=0)
    upper = mid + k * std
    lower = mid - k * std
    return pd.DataFrame({
        "mid": mid,
        "upper": upper,
        "lower": lower,
        "pct_b": (close - lower) / (upper - lower),
        "width": (upper - lower) / mid,
    })


def bollinger_state(close: pd.Series, bands: pd.DataFrame, lookback: int = 3) -> str:
    """Classe la dernière séance selon la lecture ABC Bourse.

    - "sortie_haute" / "sortie_basse" : la clôture est hors des bandes ;
    - "reintegration_basse" : clôture dans les bandes, mais au moins une clôture
      sous la bande basse dans les `lookback` séances précédentes (retournement haussier) ;
    - "reintegration_haute" : symétrique (retournement baissier) ;
    - "interieur" : sinon.
    """
    c, up, lo = close.iloc[-1], bands["upper"].iloc[-1], bands["lower"].iloc[-1]
    if c > up:
        return "sortie_haute"
    if c < lo:
        return "sortie_basse"

    recent_close = close.iloc[-1 - lookback : -1]
    recent_up = bands["upper"].iloc[-1 - lookback : -1]
    recent_lo = bands["lower"].iloc[-1 - lookback : -1]
    if (recent_close < recent_lo).any():
        return "reintegration_basse"
    if (recent_close > recent_up).any():
        return "reintegration_haute"
    return "interieur"
