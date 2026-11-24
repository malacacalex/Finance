"""MACD et sa ligne de signal.

Source : ABC Bourse, « La MACD » https://www.abcbourse.com/apprendre/11_lecon3.html
- MACD = EMA(12) - EMA(26) ; signal = EMA(9) de la MACD ; histogramme = MACD - signal.
- Achat quand la MACD croise sa ligne de signal à la hausse, vente à la baisse.
- Règle de validation de la leçon : le croisement n'est valable que si MACD et signal
  étaient du même côté depuis au moins 14 séances avant le croisement.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .moving_averages import ema


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Renvoie un DataFrame avec les colonnes macd, signal, hist."""
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def last_cross(df: pd.DataFrame, min_sessions: int = 14) -> dict | None:
    """Décrit le DERNIER croisement MACD / signal.

    Renvoie un dictionnaire :
    - direction : "haussier" (MACD passe au-dessus) ou "baissier" ;
    - date, age (séances écoulées depuis le croisement) ;
    - sessions_before : nb de séances du même côté AVANT le croisement ;
    - validated : sessions_before >= min_sessions (règle ABC Bourse).
    None s'il n'y a eu aucun croisement.
    """
    side = np.sign(df["hist"].dropna())           # +1 : MACD au-dessus, -1 : en dessous
    side = side[side != 0]
    if len(side) < 2:
        return None
    changes = np.flatnonzero(side.to_numpy()[1:] != side.to_numpy()[:-1]) + 1
    if len(changes) == 0:
        return None

    i = changes[-1]                                # indice de la séance du croisement
    previous = changes[-2] if len(changes) > 1 else 0
    sessions_before = i - previous                 # durée de l'état précédent
    return {
        "direction": "haussier" if side.iloc[i] > 0 else "baissier",
        "date": side.index[i],
        "age": len(side) - 1 - i,
        "sessions_before": int(sessions_before),
        "validated": bool(sessions_before >= min_sessions),
    }
