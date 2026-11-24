"""Tests des indicateurs techniques avec des valeurs calculées À LA MAIN."""

import numpy as np
import pandas as pd
import pytest

from invest_model.indicators import (bollinger, bollinger_state, classic_pivots, ema, last_cross, macd,
                                     rsi_wilder, sma, weekly_pivots)
from invest_model.indicators.pivots import pivot_position_score


def s(values):
    return pd.Series(values, dtype=float, index=pd.bdate_range("2026-01-05", periods=len(values)))


def test_sma():
    assert list(sma(s([1, 2, 3, 4]), 2).dropna()) == [1.5, 2.5, 3.5]


def test_ema_recurrence():
    # a = 2 / (3 + 1) = 0.5 : 1 ; 0.5*2 + 0.5*1 = 1.5 ; 0.5*3 + 0.5*1.5 = 2.25
    assert list(ema(s([1, 2, 3]), 3)) == [1.0, 1.5, 2.25]


def test_rsi_wilder_hand_computed():
    # Clôtures 10 ; 11 ; 10,5 ; 11,5 ; 11 et RSI sur 2 séances
    # Variations +1 ; -0,5 ; +1 ; -0,5
    # t=2 : moy. hausses (1+0)/2 = 0,5 ; moy. baisses (0+0,5)/2 = 0,25 ; RS = 2 -> RSI = 66,67
    # t=3 : hausses (0,5*1 + 1)/2 = 0,75 ; baisses (0,25*1 + 0)/2 = 0,125 ; RS = 6 -> 85,71
    # t=4 : hausses (0,75 + 0)/2 = 0,375 ; baisses (0,125 + 0,5)/2 = 0,3125 ; RS = 1,2 -> 54,55
    rsi = rsi_wilder(s([10, 11, 10.5, 11.5, 11]), 2)
    assert np.isnan(rsi.iloc[1])
    assert rsi.iloc[2] == pytest.approx(66.6667, abs=1e-3)
    assert rsi.iloc[3] == pytest.approx(85.7143, abs=1e-3)
    assert rsi.iloc[4] == pytest.approx(54.5455, abs=1e-3)


def test_rsi_limits():
    assert rsi_wilder(s(range(1, 30)), 14).iloc[-1] == 100.0          # uniquement des hausses
    assert rsi_wilder(s(range(30, 1, -1)), 14).iloc[-1] == 0.0        # uniquement des baisses


def test_macd_constant_series_is_zero():
    m = macd(s([50.0] * 60))
    assert m.abs().max().max() == pytest.approx(0.0)


def test_last_cross_validation_rule():
    # 20 séances MACD sous le signal puis passage au-dessus : croisement haussier validé (>= 14)
    hist = [-1.0] * 20 + [1.0] * 3
    df = pd.DataFrame({"hist": hist}, index=pd.bdate_range("2026-01-05", periods=len(hist)))
    c = last_cross(df, min_sessions=14)
    assert c["direction"] == "haussier"
    assert c["age"] == 2
    assert c["sessions_before"] == 20
    assert c["validated"]
    # seulement 5 séances avant : non validé
    hist = [1.0] * 10 + [-1.0] * 5 + [1.0] * 2
    df = pd.DataFrame({"hist": hist}, index=pd.bdate_range("2026-01-05", periods=len(hist)))
    assert not last_cross(df, 14)["validated"]


def test_bollinger_population_std():
    b = bollinger(s([1, 2, 3]), n=3, k=2)
    std = np.sqrt(2 / 3)                     # écart-type de population de 1, 2, 3
    assert b["mid"].iloc[-1] == 2
    assert b["upper"].iloc[-1] == pytest.approx(2 + 2 * std)
    assert b["lower"].iloc[-1] == pytest.approx(2 - 2 * std)


def test_bollinger_state_reintegration():
    close = s([10] * 25 + [5, 10])           # passage sous la bande basse puis retour
    bands = bollinger(close, 20, 2)
    assert bollinger_state(close.iloc[:-1], bands.iloc[:-1]) == "sortie_basse"
    assert bollinger_state(close, bands) == "reintegration_basse"


def test_classic_pivots():
    # H = 110, B = 90, C = 100 -> P = 100 ; S1 = 90 ; R1 = 110 ; S2 = 80 ; R2 = 120
    p = classic_pivots(110, 90, 100)
    assert p == {"S2": 80, "S1": 90, "P": 100, "R1": 110, "R2": 120}


def test_pivot_position_score():
    lv = classic_pivots(110, 90, 100)
    assert pivot_position_score(115, lv) == 2
    assert pivot_position_score(105, lv) == 1
    assert pivot_position_score(95, lv) == -1
    assert pivot_position_score(85, lv) == -2


def test_weekly_pivots_use_previous_complete_week():
    idx = pd.bdate_range("2026-11-02", "2026-11-17")          # 2 semaines complètes + lundi/mardi
    n = len(idx)
    df = pd.DataFrame({"High": np.arange(n) + 101.0, "Low": np.arange(n) + 99.0,
                       "Close": np.arange(n) + 100.0}, index=idx)
    w = weekly_pivots(df)
    prev = df.loc["2026-11-09":"2026-11-13"]                   # semaine précédente complète
    expected = classic_pivots(prev["High"].max(), prev["Low"].min(), prev["Close"].iloc[-1])
    assert w["en_vigueur"] == pytest.approx(expected)
    assert not w["semaine_complete"]                           # dernière séance = mardi
