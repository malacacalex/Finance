"""Points pivots (méthode standard), supports et résistances.

Source : ABC Bourse, « Les Points pivots » https://www.abcbourse.com/apprendre/11_pivots.html
et l'outil https://www.abcbourse.com/analyses/pivots (pivots quotidiens, 5 niveaux).
Avec H, B, C = plus haut, plus bas, clôture de la période PRÉCÉDENTE :
    P  = (H + B + C) / 3
    S1 = 2P - H        R1 = 2P - B
    S2 = P - (H - B)   R2 = P + (H - B)
Règle de la leçon : achat quand le cours franchit le pivot à la hausse, vente à la baisse.
"""

import pandas as pd


def classic_pivots(high: float, low: float, close: float) -> dict:
    """Pivot et niveaux à partir du plus haut, plus bas et clôture d'UNE période."""
    p = (high + low + close) / 3
    return {
        "S2": p - (high - low),
        "S1": 2 * p - high,
        "P": p,
        "R1": 2 * p - low,
        "R2": p + (high - low),
    }


def daily_pivots(ohlc: pd.DataFrame) -> dict:
    """Pivots quotidiens.

    - "en_vigueur" : calculés sur l'avant-dernière séance = niveaux qui s'appliquaient
      pendant la dernière séance (on compare la dernière clôture à ceux-là : comparer
      une clôture aux pivots calculés sur la même séance serait circulaire) ;
    - "prochaine" : calculés sur la dernière séance = niveaux de la séance suivante.
    """
    prev, last = ohlc.iloc[-2], ohlc.iloc[-1]
    return {
        "en_vigueur": classic_pivots(prev["High"], prev["Low"], prev["Close"]),
        "prochaine": classic_pivots(last["High"], last["Low"], last["Close"]),
        "date_reference": ohlc.index[-2],
    }


def weekly_pivots(ohlc: pd.DataFrame) -> dict:
    """Pivots hebdomadaires (semaines du lundi au vendredi).

    - "en_vigueur" : calculés sur la semaine précédant celle de la dernière séance ;
    - "prochaine" : calculés sur la semaine de la dernière séance (utiles pour la
      semaine suivante : niveaux de stop et d'objectif).
    """
    weeks = ohlc.resample("W-FRI").agg({"High": "max", "Low": "min", "Close": "last"}).dropna()
    current, previous = weeks.iloc[-1], weeks.iloc[-2]
    last_day = ohlc.index[-1]
    return {
        "en_vigueur": classic_pivots(previous["High"], previous["Low"], previous["Close"]),
        "prochaine": classic_pivots(current["High"], current["Low"], current["Close"]),
        "date_reference": weeks.index[-2],
        # Si la dernière séance n'est pas un vendredi, la semaine en cours est
        # incomplète : les niveaux "prochaine" sont provisoires.
        "semaine_complete": bool(last_day.weekday() == 4),
    }


def pivot_position_score(close: float, levels: dict) -> int:
    """Note -2..+2 selon la position du cours par rapport aux niveaux en vigueur.

    C > R1 -> +2 ; P <= C <= R1 -> +1 ; S1 <= C < P -> -1 ; C < S1 -> -2.
    """
    if close > levels["R1"]:
        return 2
    if close >= levels["P"]:
        return 1
    if close >= levels["S1"]:
        return -1
    return -2
