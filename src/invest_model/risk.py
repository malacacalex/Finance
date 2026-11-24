"""Mesures de risque et matrice de risque (probabilité x impact).

1. Mesures quantitatives classiques : volatilités, bêta, corrélations, drawdown,
   VaR historique / paramétrique / Monte Carlo, Sharpe, Sortino, liquidité.
2. Matrice de risque 5 x 5 : chaque risque reçoit une probabilité (1..5) et un
   impact (1..5) ; criticité = probabilité x impact.
   - risques QUANTITATIFS : notés automatiquement par des règles explicites
     (bornes dans config/parametres.yaml, section risques) ;
   - risques QUALITATIFS : notés par le groupe (onglet Risques de saisies.xlsx).
"""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd

from .grids import is_missing, level_1_to_5

# ---------------------------------------------------------------------------
# 1. Mesures quantitatives
# ---------------------------------------------------------------------------


def max_drawdown(prices: pd.Series) -> float:
    """Plus forte baisse depuis un plus haut (valeur négative, ex. -0.18 = -18 %)."""
    running_max = prices.cummax()
    return float((prices / running_max - 1).min())


def risk_metrics(adj_close: pd.Series, prices: pd.DataFrame, benchmark: pd.DataFrame | None,
                 peer_prices: pd.DataFrame | None, horizon: int, confidence: float,
                 amount: float, rf: float) -> dict:
    """Calcule les mesures de risque usuelles sur ~1 an de séances."""
    r = np.log(adj_close / adj_close.shift(1)).dropna()
    r_1y = r.iloc[-252:]
    out: dict = {}

    out["vol_20j"] = float(r.iloc[-20:].std() * np.sqrt(252))
    out["vol_60j"] = float(r.iloc[-60:].std() * np.sqrt(252))
    out["vol_1a"] = float(r_1y.std() * np.sqrt(252))
    out["drawdown_max_1a"] = max_drawdown(adj_close.iloc[-252:])
    out["drawdown_actuel"] = float(adj_close.iloc[-1] / adj_close.iloc[-252:].max() - 1)

    # Rendement 1 an, Sharpe et Sortino (taux sans risque = hypothèse, voir scénario)
    ret_1a = float(adj_close.iloc[-1] / adj_close.iloc[-253] - 1) if len(adj_close) > 253 else None
    out["rendement_1a"] = ret_1a
    if ret_1a is not None:
        out["sharpe_1a"] = (ret_1a - rf) / out["vol_1a"]
        downside = r_1y[r_1y < 0].std() * np.sqrt(252)
        out["sortino_1a"] = (ret_1a - rf) / downside if downside else None

    # VaR sur l'horizon (en € pour `amount`) : historique et paramétrique
    h_returns = (np.exp(np.log(adj_close).diff(horizon)) - 1).dropna().iloc[-504:]
    out["var_historique"] = float(-np.quantile(h_returns, 1 - confidence) * amount)
    z = NormalDist().inv_cdf(confidence)
    mu_h, sig_h = r_1y.mean() * horizon, r_1y.std() * np.sqrt(horizon)
    out["var_parametrique"] = float(-(mu_h - z * sig_h) * amount)

    # Bêta et corrélation avec l'indice de référence
    if benchmark is not None and "Close" in benchmark:
        rm = np.log(benchmark["Close"] / benchmark["Close"].shift(1)).dropna()
        joined = pd.concat([r_1y, rm], axis=1, join="inner").dropna()
        joined.columns = ["action", "indice"]
        if len(joined) > 30:
            out["beta"] = float(joined.cov().iloc[0, 1] / joined["indice"].var())
            out["correlation_indice"] = float(joined.corr().iloc[0, 1])

    # Matrice de corrélation avec les pairs (rendements quotidiens, dates communes)
    if peer_prices is not None and not peer_prices.empty:
        frame = pd.concat([adj_close.rename("Société"), peer_prices], axis=1).iloc[-260:]
        rets = np.log(frame / frame.shift(1))
        out["correlations"] = rets.corr(min_periods=60)

    # Liquidité : montant échangé par jour (moyenne 20 séances)
    traded = (prices["Close"] * prices["Volume"]).iloc[-20:].mean()
    out["volume_euros_jour"] = float(traded)
    out["position_vs_volume"] = float(amount / traded) if traded else None
    return out


# ---------------------------------------------------------------------------
# 2. Matrice de risque
# ---------------------------------------------------------------------------


def zone(criticality: int, zones: dict) -> str:
    if criticality <= zones["faible"]:
        return "Faible"
    if criticality <= zones["modere"]:
        return "Modéré"
    if criticality <= zones["eleve"]:
        return "Élevé"
    return "Critique"


def quantitative_risks(cfg: dict, mc: dict, fundamental: dict, technical: dict,
                       news_negative_share: float | None, events: list[str]) -> list[dict]:
    """Risques notés automatiquement. Chaque ligne explique sa règle de notation."""
    risks = []

    # R1 — Marché : probabilité d'une forte baisse et ampleur des pires cas (Monte Carlo)
    c = cfg["marche"]
    cvar_pct = mc["stats_pct"]["cvar"]
    risks.append({
        "Risque": f"Baisse de plus de {cfg['seuil_choc_hebdo']:.0%} sur l'horizon (marché)",
        "Catégorie": "Marché",
        "Probabilité": level_1_to_5(mc["proba_choc"], c["proba_bornes"]),
        "Impact": level_1_to_5(cvar_pct, c["impact_bornes"]),
        "Justification": f"Monte Carlo : P(baisse > {cfg['seuil_choc_hebdo']:.0%}) = {mc['proba_choc']:.1%} ; "
                         f"CVaR = {cvar_pct:.1%} de la position",
    })

    # R2 — Valorisation : PER par rapport au secteur
    per_rel = fundamental.get("per_relatif")
    if not is_missing(per_rel):
        risks.append({
            "Risque": "Valorisation élevée (correction si déception)",
            "Catégorie": "Valorisation",
            "Probabilité": level_1_to_5(per_rel, cfg["valorisation"]["proba_bornes"]),
            "Impact": cfg["valorisation"]["impact"],
            "Justification": f"PER = {per_rel:.2f} x la médiane du secteur",
        })

    # R3 — Endettement
    dn = fundamental.get("dette_ebitda")
    if not is_missing(dn):
        risks.append({
            "Risque": "Endettement (charge de la dette, flexibilité financière)",
            "Catégorie": "Financier",
            "Probabilité": level_1_to_5(dn, cfg["endettement"]["proba_bornes"]),
            "Impact": cfg["endettement"]["impact"],
            "Justification": f"Dette nette / EBITDA = {dn:.2f}",
        })

    # R4 — Cassure du support hebdomadaire S1 : plus il est proche, plus c'est probable
    s = cfg["support"]
    close, s1, s2 = technical["close"], technical["s1_hebdo"], technical["s2_hebdo"]
    sigma_week = technical["sigma_hebdo"]
    distance_sigma = (close - s1) / (close * sigma_week) if sigma_week else None
    if not is_missing(distance_sigma):
        proba = 5 if distance_sigma <= 0 else 6 - level_1_to_5(distance_sigma, s["proba_bornes"])
        gap = (s1 - s2) / close
        risks.append({
            "Risque": "Cassure du support hebdomadaire S1",
            "Catégorie": "Technique",
            "Probabilité": int(proba),
            "Impact": level_1_to_5(gap, s["impact_bornes"]),
            "Justification": f"Cours à {distance_sigma:.2f} écart-type(s) hebdo de S1 ({s1:.2f}) ; "
                             f"S1 -> S2 = {gap:.1%}",
        })

    # R5 — Flux d'informations négatives
    if news_negative_share is not None:
        risks.append({
            "Risque": "Flux d'actualités négatives",
            "Catégorie": "Information",
            "Probabilité": level_1_to_5(news_negative_share, cfg["information"]["proba_bornes"]),
            "Impact": cfg["information"]["impact"],
            "Justification": f"{news_negative_share:.0%} des nouvelles récentes sont négatives",
        })

    # R6 — Événement pendant l'horizon (publication, détachement du dividende)
    risks.append({
        "Risque": "Événement de la société pendant l'horizon",
        "Catégorie": "Événement",
        "Probabilité": 5 if events else 1,
        "Impact": cfg["evenement"]["impact"],
        "Justification": "; ".join(events) if events else "Aucun événement connu dans l'horizon (calendrier yfinance)",
    })

    for r in risks:
        r["Type"] = "Quantitatif (automatique)"
    return risks


def build_risk_matrix(quant: list[dict], qualitative: pd.DataFrame | None, zones: dict) -> pd.DataFrame:
    """Assemble tous les risques, calcule criticité et zone, trie du plus critique au moins."""
    rows = list(quant)
    if qualitative is not None and not qualitative.empty:
        for _, q in qualitative.iterrows():
            if is_missing(q.get("probabilite")) or is_missing(q.get("impact")):
                continue
            rows.append({
                "Risque": q["risque"], "Catégorie": q.get("categorie", ""),
                "Probabilité": int(q["probabilite"]), "Impact": int(q["impact"]),
                "Justification": q.get("justification", ""), "Type": "Qualitatif (groupe)",
            })
    df = pd.DataFrame(rows)
    df["Criticité"] = df["Probabilité"] * df["Impact"]
    df["Zone"] = df["Criticité"].map(lambda c: zone(c, zones))
    df = df.sort_values("Criticité", ascending=False).reset_index(drop=True)
    df.insert(0, "ID", [f"R{i + 1}" for i in range(len(df))])
    return df[["ID", "Risque", "Catégorie", "Type", "Probabilité", "Impact", "Criticité", "Zone", "Justification"]]


def upcoming_events(calendar: dict, as_of: pd.Timestamp, horizon: int) -> list[str]:
    """Événements du calendrier yfinance qui tombent dans l'horizon (jours ouvrés)."""
    end = as_of + pd.offsets.BDay(horizon)
    found = []
    for label, key in [("Publication de résultats", "Earnings Date"), ("Détachement du dividende", "Ex-Dividend Date"),
                       ("Paiement du dividende", "Dividend Date")]:
        values = calendar.get(key)
        values = values if isinstance(values, list) else [values]
        for v in values:
            if not v:
                continue
            d = pd.to_datetime(v, errors="coerce")
            if pd.notna(d) and as_of < d <= end:
                found.append(f"{label} le {d.date()}")
    return found
