"""Pilier 1 — Graphique (analyse technique).

5 outils notés de -2 à +2 (grilles dans config/parametres.yaml, section technique) :
RSI, MACD, bandes de Bollinger, moyennes mobiles 20/50/100, points pivots.
Le quantitatif du pilier est la moyenne pondérée des 5 notes.
"""

from __future__ import annotations

import pandas as pd

from ..grids import note_from_bounds, weighted_mean
from ..indicators import bollinger, bollinger_state, daily_pivots, last_cross, macd, rsi_wilder, sma, weekly_pivots
from ..indicators.pivots import pivot_position_score
from .result import PillarResult

LESSONS = {
    "rsi": "https://www.abcbourse.com/apprendre/11_lecon7_1.html",
    "macd": "https://www.abcbourse.com/apprendre/11_lecon3.html",
    "bollinger": "https://www.abcbourse.com/apprendre/11_lecon4.html",
    "moyennes_mobiles": "https://www.abcbourse.com/apprendre/11_lecon2.html",
    "pivots": "https://www.abcbourse.com/apprendre/11_pivots.html",
}

BOLLINGER_LABELS = {
    "sortie_haute": "Clôture au-dessus de la bande haute (continuation haussière)",
    "sortie_basse": "Clôture sous la bande basse (continuation baissière)",
    "reintegration_basse": "Retour dans les bandes par le bas (retournement haussier)",
    "reintegration_haute": "Retour dans les bandes par le haut (retournement baissier)",
    "interieur": "À l'intérieur des bandes de Bollinger",
}


def analyse_technical(prices: pd.DataFrame, cfg: dict) -> PillarResult:
    """Calcule les indicateurs et les notes du pilier Graphique."""
    close = prices["Close"]
    last = float(close.iloc[-1])
    rows = []          # lignes du tableau de détail
    notes = {}         # indicateur -> note

    # --- 1. RSI 14 -------------------------------------------------------
    rsi_cfg = cfg["rsi"]
    rsi = rsi_wilder(close, rsi_cfg["periode"])
    rsi_last = float(rsi.iloc[-1])
    notes["rsi"] = note_from_bounds(rsi_last, rsi_cfg["grille"]["bornes"], rsi_cfg["grille"]["plus_haut_mieux"])
    zone = "survente" if rsi_last < 30 else "surachat" if rsi_last >= 70 else "zone neutre"
    rows.append(("rsi", f"RSI {rsi_cfg['periode']} jours", round(rsi_last, 1),
                 f"Le RSI {rsi_cfg['periode']} jours est de {rsi_last:.1f} % : {zone}"))

    # --- 2. MACD ---------------------------------------------------------
    m_cfg = cfg["macd"]
    m = macd(close, m_cfg["rapide"], m_cfg["lente"], m_cfg["signal"])
    cross = last_cross(m, m_cfg["seances_validation"])
    above = m["macd"].iloc[-1] > m["signal"].iloc[-1]
    if cross and cross["validated"] and cross["age"] <= m_cfg["croisement_recent"]:
        notes["macd"] = 2 if cross["direction"] == "haussier" else -2
    else:
        notes["macd"] = 1 if above else -1
    position = "au-dessus de" if above else "sous"
    text = f"La MACD évolue {position} sa ligne de signal"
    if cross:
        status = "validé" if cross["validated"] else "non validé"
        text += (f" ; dernier croisement {cross['direction']} il y a {cross['age']} séance(s), "
                 f"{status} ({cross['sessions_before']} séances du même côté avant, "
                 f"règle ABC : {m_cfg['seances_validation']})")
    rows.append(("macd", "MACD (12, 26, 9)", round(float(m["hist"].iloc[-1]), 3), text))

    # --- 3. Bandes de Bollinger -------------------------------------------
    b_cfg = cfg["bollinger"]
    bands = bollinger(close, b_cfg["periode"], b_cfg["ecarts_types"])
    state = bollinger_state(close, bands, b_cfg["retour_seances"])
    notes["bollinger"] = b_cfg["notes"][state]
    width = bands["width"].dropna()
    squeeze_pct = float((width.iloc[-126:] < width.iloc[-1]).mean())   # rang sur ~6 mois
    text = BOLLINGER_LABELS[state] + f" ; %B = {bands['pct_b'].iloc[-1]:.2f}"
    if squeeze_pct <= 0.10:
        text += " ; RESSERREMENT des bandes (mouvement important possible)"
    rows.append(("bollinger", f"Bollinger ({b_cfg['periode']}, {b_cfg['ecarts_types']})",
                 round(float(bands["pct_b"].iloc[-1]), 2), text))

    # --- 4. Moyennes mobiles ---------------------------------------------
    mas = {n: sma(close, n) for n in cfg["moyennes_mobiles"]}
    below_price = [n for n, s in mas.items() if last > s.iloc[-1]]
    notes["moyennes_mobiles"] = cfg["moyennes_mobiles_notes"][str(len(below_price))]
    above_price = [n for n in mas if n not in below_price]
    parts = []
    if below_price:
        parts.append("au-dessus des MM " + "/".join(map(str, below_price)))
    if above_price:
        parts.append("en dessous des MM " + "/".join(map(str, above_price)))
    n_short, n_long = cfg["moyennes_mobiles"][0], cfg["moyennes_mobiles"][1]
    golden = _recent_ma_cross(mas[n_short], mas[n_long], n_short, n_long)
    text = "Cours " + " et ".join(parts) + (f" ; {golden}" if golden else "")
    rows.append(("moyennes_mobiles", "Moyennes mobiles " + "/".join(map(str, mas)),
                 len(below_price), text))

    # --- 5. Points pivots (quotidiens et hebdomadaires) ------------------
    p_cfg = cfg["pivots"]
    daily = daily_pivots(prices)
    weekly = weekly_pivots(prices)
    s_day = pivot_position_score(last, daily["en_vigueur"])
    s_week = pivot_position_score(last, weekly["en_vigueur"])
    notes["pivots"] = weighted_mean({"q": s_day, "h": s_week},
                                    {"q": p_cfg["poids_quotidien"], "h": p_cfg["poids_hebdo"]})
    text = (f"Quotidien : cours {_pivot_zone(last, daily['en_vigueur'])} (note {s_day:+d}) ; "
            f"hebdo : cours {_pivot_zone(last, weekly['en_vigueur'])} (note {s_week:+d})")
    rows.append(("pivots", "Points pivots (quotidien + hebdo)", round(daily["en_vigueur"]["P"], 2), text))

    # --- Tableau de détail et note du pilier -----------------------------
    details = pd.DataFrame(rows, columns=["cle", "Indicateur", "Valeur", "Lecture"])
    details["Note"] = details["cle"].map(notes)
    details["Poids"] = details["cle"].map(cfg["poids_indicateurs"])
    details["Leçon ABC Bourse"] = details["cle"].map(LESSONS)
    quanti = weighted_mean(notes, cfg["poids_indicateurs"])

    return PillarResult(
        name="Graphique",
        quanti=quanti,
        details=details,
        extra={
            "close": close,
            "rsi": rsi,
            "macd": m,
            "bands": bands,
            "mas": mas,
            "pivots_daily": daily,
            "pivots_weekly": weekly,
            "macd_cross": cross,
            "context": _context(prices),
        },
    )


def _pivot_zone(close: float, lv: dict) -> str:
    """Décrit la zone du cours entre les niveaux pivots."""
    if close > lv["R2"]:
        return f"au-dessus de R2 ({lv['R2']:.2f})"
    if close > lv["R1"]:
        return f"entre R1 ({lv['R1']:.2f}) et R2 ({lv['R2']:.2f})"
    if close >= lv["P"]:
        return f"entre P ({lv['P']:.2f}) et R1 ({lv['R1']:.2f})"
    if close >= lv["S1"]:
        return f"entre S1 ({lv['S1']:.2f}) et P ({lv['P']:.2f})"
    if close >= lv["S2"]:
        return f"entre S2 ({lv['S2']:.2f}) et S1 ({lv['S1']:.2f})"
    return f"sous S2 ({lv['S2']:.2f})"


def _recent_ma_cross(short: pd.Series, long: pd.Series, n_short: int, n_long: int,
                     window: int = 20) -> str | None:
    """Détecte un croisement MM courte / MM longue sur les `window` dernières séances.

    Leçon ABC : la MM courte qui passe au-dessus de la MM longue marque le début
    d'une tendance haussière (et inversement).
    """
    above = (short - long).dropna().iloc[-window - 1 :] > 0
    changes = above.astype(int).diff().dropna()
    if changes.empty or not changes.any():
        return None
    last_change = changes[changes != 0].iloc[-1]
    direction = "HAUSSIER" if last_change > 0 else "BAISSIER"
    return f"croisement {direction} MM{n_short}/MM{n_long} dans les {window} dernières séances"


def _context(prices: pd.DataFrame) -> dict:
    """Informations de contexte (non notées) : performances, plus hauts / bas."""
    close = prices["Close"]
    last = close.iloc[-1]

    def perf(days: int) -> float | None:
        return float(last / close.iloc[-1 - days] - 1) if len(close) > days else None

    year = close.iloc[-252:]
    ytd = close[close.index.year == close.index[-1].year]
    return {
        "dernier_cours": float(last),
        "date": close.index[-1],
        "perf_1s": perf(5),
        "perf_1m": perf(21),
        "perf_3m": perf(63),
        "perf_6m": perf(126),
        "perf_1a": perf(252),
        "perf_ytd": float(last / ytd.iloc[0] - 1) if len(ytd) else None,
        "plus_haut_52s": float(year.max()),
        "plus_bas_52s": float(year.min()),
        "ecart_plus_haut_52s": float(last / year.max() - 1),
        "volume_moyen_20j": float(prices["Volume"].iloc[-20:].mean()),
    }
