"""Tests des grilles, de Monte Carlo, de la combinaison des scores, de la décision et de la veille."""

import numpy as np
import pandas as pd
import pytest

from invest_model.config import _merge_client
from invest_model.decision import decide, signal_from_score
from invest_model.grids import level_1_to_5, note_from_bounds, weighted_mean
from invest_model.pillars.montecarlo import risk_stats, simulate_gbm
from invest_model.pillars.result import PillarResult
from invest_model.scoring import combine
from invest_model.watch import _dedup_key, build_queries, suggest_direction, suggest_reliability

# ---------------------------------------------------------------- grilles


def test_note_from_bounds_rsi_grid():
    bounds = [30, 40, 60, 70]                       # RSI : plus bas = mieux
    assert note_from_bounds(25, bounds, False) == 2
    assert note_from_bounds(30, bounds, False) == 1      # 30 inclus dans [30, 40[
    assert note_from_bounds(50, bounds, False) == 0
    assert note_from_bounds(65, bounds, False) == -1
    assert note_from_bounds(70, bounds, False) == -2
    assert note_from_bounds(None, bounds, False) is None


def test_note_from_bounds_rejects_bad_bounds():
    with pytest.raises(ValueError):
        note_from_bounds(1, [3, 2, 1, 0])


def test_level_and_weighted_mean():
    assert level_1_to_5(0.01, [0.02, 0.05, 0.1, 0.2]) == 1
    assert level_1_to_5(0.5, [0.02, 0.05, 0.1, 0.2]) == 5
    assert weighted_mean({"a": 2, "b": None, "c": -1}, {"a": 1, "b": 5, "c": 1}) == 0.5


# ---------------------------------------------------------------- Monte Carlo


def test_gbm_reproducible_and_terminal_equivalence():
    paths, z = simulate_gbm(100.0, 0.001, 0.02, n_days=5, n_sims=2000, seed=7)
    paths2, _ = simulate_gbm(100.0, 0.001, 0.02, n_days=5, n_sims=2000, seed=7)
    assert np.array_equal(paths, paths2)                         # même graine -> mêmes résultats
    z_eq = z.sum(axis=1) / np.sqrt(5)                            # formule recopiée dans Excel
    excel = 100.0 * np.exp(5 * 0.001 + 0.02 * np.sqrt(5) * z_eq)
    assert np.allclose(paths[:, -1], excel)


def test_gbm_zero_volatility_is_deterministic():
    paths, _ = simulate_gbm(100.0, 0.01, 0.0, n_days=5, n_sims=10, seed=1)
    assert np.allclose(paths[:, -1], 100 * np.exp(0.05))


def test_gbm_correlated_assets():
    corr = np.array([[1.0, 0.8], [0.8, 1.0]])
    paths, _ = simulate_gbm([100, 50], [0, 0], [0.02, 0.02], n_days=1, n_sims=50_000, seed=3, corr=corr)
    r = np.log(paths[:, 1, :] / paths[:, 0, :])
    assert np.corrcoef(r.T)[0, 1] == pytest.approx(0.8, abs=0.02)


def test_risk_stats_var():
    pnl = np.arange(-50, 50, dtype=float)                       # 100 valeurs de -50 à 49
    st = risk_stats(pnl, 0.95)
    assert st["var"] == pytest.approx(-np.quantile(pnl, 0.05))
    assert st["cvar"] >= st["var"]
    assert st["proba_perte"] == 0.5


# ---------------------------------------------------------------- scores et décision


def test_combine_weights_and_missing_quali():
    p1 = PillarResult("Graphique", quanti=1.0, quali=-1.0)
    p2 = PillarResult("Financier", quanti=2.0, quali=None)      # quali absent -> quanti seul
    p3 = PillarResult("Hasard", quanti=-2.0)
    final, table = combine([p1, p2, p3], {"graphique": 1, "financier": 1, "hasard": 2},
                           {"graphique": 0.75, "financier": 0.5})
    # Graphique = 0,75*1 + 0,25*(-1) = 0,5 ; Financier = 2 ; Hasard = -2
    assert final == pytest.approx((0.5 + 2 - 4) / 4)
    assert table["Contribution"].sum() == pytest.approx(final)


THRESHOLDS = {"achat_fort": 1.0, "achat": 0.4, "vente": -0.4, "vente_forte": -1.0,
              "risque_critique_bloque_achat": True}


def test_signal_thresholds():
    assert signal_from_score(1.2, THRESHOLDS) == "ACHAT FORT"
    assert signal_from_score(0.4, THRESHOLDS) == "ACHAT"
    assert signal_from_score(0.0, THRESHOLDS) == "NEUTRE"
    assert signal_from_score(-0.5, THRESHOLDS) == "VENTE"
    assert signal_from_score(-1.5, THRESHOLDS) == "VENTE FORTE"


def _decide(score, qty, zone="Faible"):
    risks = pd.DataFrame({"Risque": ["test"], "Zone": [zone]})
    table = pd.DataFrame({"Pilier": ["Graphique"], "Score du pilier": [score], "Contribution": [score],
                          "Combinaison": ["test"]})
    levels = {"S2": 90, "S1": 95, "P": 100, "R1": 105, "R2": 110}
    return decide(score, THRESHOLDS, qty, risks, 100.0, levels, table)


def test_decision_depends_on_position_and_risk():
    assert _decide(0.6, 0).action == "ACHETER"
    assert _decide(0.6, 10).action == "CONSERVER"
    assert _decide(-1.5, 10).action == "VENDRE"
    assert _decide(-1.5, 0).action == "ATTENDRE"
    assert _decide(1.5, 0, zone="Critique").action == "ATTENDRE"   # garde-fou risque critique
    assert _decide(0.6, 0).levels["ratio_gain_risque"] == pytest.approx(1.0)


# ---------------------------------------------------------------- configuration


def test_client_overrides_scenario():
    merged, origins = _merge_client({"a": 1, "b": 2, "c": None}, {"a": None, "b": 5})
    assert merged == {"a": 1, "b": 5, "c": None}
    assert origins == {"a": "scénario", "b": "client", "c": "non renseigné"}


# ---------------------------------------------------------------- veille


def test_watch_helpers():
    lex = {"positif": ["hausse", "relève"], "negatif": ["baisse", "amende"]}
    assert suggest_direction("Kepler RELEVE son objectif", lex) == 1        # accents et casse ignorés
    assert suggest_direction("Amende pour l'usine", lex) == -1
    assert suggest_direction("Hausse puis baisse", lex) == 0
    cfg = {"fiabilite_sources": {3: ["amf-france.org"], 2: ["boursier.com"]}}
    assert suggest_reliability("amf-france.org", cfg) == 3
    assert suggest_reliability("bourse.boursier.com", cfg) == 2
    assert suggest_reliability("blog.example", cfg) == 1
    assert _dedup_key("Air Liquide : record !") == _dedup_key("air liquide record")


def test_build_queries():
    q = build_queries({"nom": "Air Liquide", "secteur_requete": "Linde", "site_ir": "airliquide.com"},
                      {"fenetre": "when:7d", "modeles": {"officiel": '"{nom}" site:{site_ir}'}})
    assert q == {"officiel": '"Air Liquide" site:airliquide.com when:7d'}
