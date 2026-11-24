"""RSI (Relative Strength Index) de Wilder.

Source : ABC Bourse, « Le RSI » https://www.abcbourse.com/apprendre/11_lecon7_1.html
Réglage : 14 séances (celui de Wilder et des fiches ABC « RSI 14 jours »).
Seuils de la leçon : au-dessus de 70 = surachat, en dessous de 30 = survente.
"""

import numpy as np
import pandas as pd


def rsi_wilder(close: pd.Series, n: int = 14) -> pd.Series:
    """RSI de Wilder, entre 0 et 100.

    Étapes :
    1. variation quotidienne d = C(t) - C(t-1) ;
    2. hausse = max(d, 0), baisse = max(-d, 0) ;
    3. première moyenne = moyenne SIMPLE des n premières hausses (resp. baisses) ;
    4. ensuite lissage de Wilder : moy(t) = (moy(t-1) * (n-1) + valeur(t)) / n ;
    5. RS = moyenne des hausses / moyenne des baisses ; RSI = 100 - 100 / (1 + RS).
    """
    delta = close.diff().to_numpy()
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)

    rsi = np.full(len(close), np.nan)
    if len(close) <= n:
        return pd.Series(rsi, index=close.index, name=f"RSI{n}")

    # Étape 3 : initialisation sur les n premières variations (indices 1..n)
    avg_gain = gains[1 : n + 1].mean()
    avg_loss = losses[1 : n + 1].mean()
    rsi[n] = _rsi_from_averages(avg_gain, avg_loss)

    # Étape 4 : lissage de Wilder
    for t in range(n + 1, len(close)):
        avg_gain = (avg_gain * (n - 1) + gains[t]) / n
        avg_loss = (avg_loss * (n - 1) + losses[t]) / n
        rsi[t] = _rsi_from_averages(avg_gain, avg_loss)

    return pd.Series(rsi, index=close.index, name=f"RSI{n}")


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    """RSI à partir des moyennes de hausses et de baisses (cas limites inclus)."""
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0   # aucune baisse : RSI maximal
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)
