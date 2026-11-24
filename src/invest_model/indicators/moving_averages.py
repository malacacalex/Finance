"""Moyennes mobiles.

Source : ABC Bourse, « Les moyennes mobiles »
https://www.abcbourse.com/apprendre/11_lecon2.html
"""

import pandas as pd


def sma(close: pd.Series, n: int) -> pd.Series:
    """Moyenne mobile SIMPLE sur n séances : somme des n dernières clôtures / n.

    Les n-1 premières valeurs sont NaN (pas assez d'historique).
    """
    return close.rolling(window=n, min_periods=n).mean()


def ema(close: pd.Series, n: int) -> pd.Series:
    """Moyenne mobile EXPONENTIELLE sur n séances (utilisée par la MACD).

    Formule récursive : EMA(t) = a * C(t) + (1 - a) * EMA(t-1), avec a = 2 / (n + 1).
    `adjust=False` applique exactement cette récurrence, initialisée sur la première clôture.
    """
    return close.ewm(span=n, adjust=False).mean()
