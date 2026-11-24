"""Analyse complète d'UNE société : enchaîne toutes les étapes du modèle.

    données (yfinance ou instantané) -> veille (dorking) -> 4 piliers
    -> matrice de risque -> score final -> décision -> rapport

C'est le point d'entrée appelé par la commande `invest analyse AI.PA`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from . import inputs
from .config import Settings, project_path
from .data import fetch_company, latest_snapshot_date, load_snapshot, save_snapshot, snapshot_dir
from .decision import Decision, decide
from .grids import is_missing
from .pillars.fundamental import analyse_fundamental, analyst_view, dividend_history, financial_history
from .pillars.montecarlo import analyse_montecarlo
from .pillars.news import analyse_news
from .pillars.result import PillarResult
from .pillars.technical import analyse_technical
from .risk import build_risk_matrix, quantitative_risks, risk_metrics, upcoming_events
from .scoring import combine
from .watch import collect_news


@dataclass
class AnalysisResult:
    ticker: str
    name: str
    as_of: pd.Timestamp
    snapshot_date: str
    settings: Settings
    bundle: dict
    technical: PillarResult
    fundamental: PillarResult
    news: PillarResult
    montecarlo: PillarResult
    metrics: dict
    risk_matrix: pd.DataFrame
    final_score: float | None
    pillar_table: pd.DataFrame
    decision: Decision
    position: tuple
    history: pd.DataFrame
    dividends: pd.DataFrame
    analysts: dict
    abc_comparison: pd.DataFrame
    quali_tables: dict
    warnings: list[str] = field(default_factory=list)


def run_analysis(ticker: str, settings: Settings, snapshot: str | None = None, offline: bool = False,
                 with_watch: bool = True, log=print) -> AnalysisResult:
    params = settings.params
    company = settings.universe.get(ticker)
    if company is None:
        raise ValueError(f"{ticker} absent de config/univers.yaml")
    snap_root = project_path(params["donnees"]["dossier_snapshots"])
    workbook = project_path(params["donnees"]["classeur_saisies"])
    warnings: list[str] = []

    # ------------------------------------------------------------------ 1. Données
    if offline or snapshot:
        snapshot = snapshot or latest_snapshot_date(snap_root, ticker)
        if snapshot is None:
            raise FileNotFoundError(f"Aucun instantané pour {ticker} : lancer sans --hors-ligne")
        log(f"[1/7] Lecture de l'instantané du {snapshot}")
        bundle = load_snapshot(snap_root, snapshot, ticker)
    else:
        snapshot = datetime.now().strftime("%Y-%m-%d")
        log(f"[1/7] Téléchargement yfinance : {ticker}, pairs {company['pairs']}, indice")
        bundle = fetch_company(ticker, company["pairs"], params["donnees"]["indice_reference"],
                               params["donnees"]["historique"])
        if bundle.get("prices") is None:
            raise RuntimeError("Cours indisponibles (yfinance) : relancer plus tard ou utiliser --hors-ligne")
        save_snapshot(bundle, snap_root, snapshot, ticker)
    warnings += bundle.get("meta", {}).get("avertissements", [])
    prices = bundle["prices"]
    as_of = prices.index[-1]

    # ------------------------------------------------------------------ 2. Saisies + veille
    inputs.ensure_workbook(workbook, [ticker], settings.risks)
    if with_watch and not offline:
        log("[2/7] Veille : requêtes Google News (dorking) + actualités Yahoo")
        watch_log: list[str] = []
        news_found = collect_news(ticker, company, settings.watch, bundle.get("news_yahoo"), watch_log)
        news_found.to_csv(snapshot_dir(snap_root, snapshot, ticker) / "veille_brute.csv", index=False)
        added = inputs.append_news(workbook, news_found)
        warnings += watch_log
        log(f"      {len(news_found)} actualités trouvées, {added} nouvelle(s) ajoutée(s) à {workbook.name}")
    else:
        log("[2/7] Veille ignorée (hors ligne ou --sans-veille)")

    # ------------------------------------------------------------------ 3. Pilier Graphique
    log("[3/7] Pilier Graphique : RSI, MACD, Bollinger, MM 20/50/100, pivots")
    technical = analyse_technical(prices, params["technique"])
    technical.quali, q_tech, w = inputs.read_quali(workbook, "Quali_Graphique", ticker)
    technical.warnings += w

    # ------------------------------------------------------------------ 4. Pilier Financier
    log("[4/7] Pilier Financier : ratios vs médiane des pairs")
    fundamental = analyse_fundamental(bundle["info"], bundle.get("peers_info") or {}, params["financier"],
                                      bundle.get("growth_estimates"), inputs.read_overrides(workbook, ticker))
    fundamental.quali, q_fin, w = inputs.read_quali(workbook, "Quali_Financier", ticker)
    fundamental.warnings += w

    # ------------------------------------------------------------------ 5. Pilier Informations
    log("[5/7] Pilier Informations : comptage et notes des actualités")
    news = analyse_news(inputs.read_news(workbook, ticker), as_of, params["informations"])

    # ------------------------------------------------------------------ 6. Pilier Hasard + risques
    c = settings.client
    log(f"[6/7] Pilier Hasard : Monte Carlo ({params['monte_carlo']['simulations']} simulations) et risques")
    adj = prices["Adj Close"] if "Adj Close" in prices else prices["Close"]
    mc = analyse_montecarlo(adj, params["monte_carlo"], c["horizon_jours"], c["fenetre_historique_jours"],
                            c["montant_analyse"], c["niveau_confiance"], params["risques"]["seuil_choc_hebdo"])
    metrics = risk_metrics(adj, prices, bundle.get("benchmark"), bundle.get("peer_prices"),
                           c["horizon_jours"], c["niveau_confiance"], c["montant_analyse"], c["taux_sans_risque"])
    metrics["var_montecarlo"] = mc.extra["stats"]["var"]
    metrics["cvar_montecarlo"] = mc.extra["stats"]["cvar"]

    # Niveaux hebdomadaires pour la décision : si la semaine est terminée (vendredi),
    # ceux de la semaine suivante ; sinon, ceux EN VIGUEUR cette semaine (calculés sur
    # la semaine précédente complète) : une semaine de 2 séances donnerait des niveaux trop serrés.
    pw = technical.extra["pivots_weekly"]
    weekly_next = pw["prochaine"] if pw["semaine_complete"] else pw["en_vigueur"]
    technical.extra["niveaux_decision"] = ("semaine suivante" if pw["semaine_complete"]
                                           else "semaine en cours (en vigueur)")
    fd = fundamental.details.set_index("cle")
    events = upcoming_events(bundle.get("calendar") or {}, as_of, c["horizon_jours"])
    quant_risks = quantitative_risks(
        params["risques"], mc.extra,
        {"per_relatif": fd.loc["per", "Relatif (société / secteur)"] if "per" in fd.index else None,
         "dette_ebitda": fd.loc["dette_ebitda", "Société"] if "dette_ebitda" in fd.index else None},
        {"close": float(prices["Close"].iloc[-1]), "s1_hebdo": weekly_next["S1"], "s2_hebdo": weekly_next["S2"],
         "sigma_hebdo": mc.extra["params"].sigma * np.sqrt(c["horizon_jours"])},
        news.extra.get("negative_share") if news.extra else None,
        events,
    )
    risk_matrix = build_risk_matrix(quant_risks, inputs.read_risks(workbook, ticker), params["risques"]["zones"])

    # ------------------------------------------------------------------ 7. Score et décision
    log("[7/7] Score final et décision")
    pillars = [technical, fundamental, news, mc]
    final, table = combine(pillars, settings.weights, settings.quanti_share)
    position = inputs.read_position(workbook, ticker)
    decision = decide(final, settings.decision, position[0], risk_matrix,
                      float(prices["Close"].iloc[-1]), weekly_next, table)
    if not pw["semaine_complete"]:
        warnings.append("Semaine en cours incomplète : stop et objectifs calculés sur les pivots hebdomadaires "
                        "EN VIGUEUR (semaine précédente complète) ; relancer après la clôture du vendredi "
                        "pour obtenir ceux de la semaine suivante")
    for p in pillars:
        warnings += p.warnings
    if settings.uses_unvalidated_hypotheses:
        warnings.insert(0, "Résultats fondés sur des HYPOTHÈSES DU GROUPE non validées par le client : "
                        + ", ".join(k for k, v in settings.origins.items() if v == "scénario"))

    return AnalysisResult(
        ticker=ticker, name=company["nom"], as_of=as_of, snapshot_date=snapshot, settings=settings,
        bundle=bundle, technical=technical, fundamental=fundamental, news=news, montecarlo=mc,
        metrics=metrics, risk_matrix=risk_matrix, final_score=final, pillar_table=table,
        decision=decision, position=position, history=financial_history(bundle),
        dividends=dividend_history(bundle.get("dividends")), analysts=analyst_view(bundle),
        abc_comparison=abc_comparison(workbook, ticker, technical, fundamental, bundle),
        quali_tables={"Graphique": q_tech, "Financier": q_fin}, warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Comparaison avec la fiche ABC Bourse « Analyse et conseil »
# ---------------------------------------------------------------------------

def our_abc_values(technical: PillarResult, fundamental: PillarResult, bundle: dict) -> dict:
    """Nos valeurs, exprimées comme sur la fiche ABC Bourse."""
    e = technical.extra
    close = float(e["close"].iloc[-1])
    out = {"RSI 14 jours": round(float(e["rsi"].iloc[-1]), 1)}
    for n, s in e["mas"].items():
        out[f"Cours / MM{n}"] = "au-dessus" if close > s.iloc[-1] else "en dessous"
    b = e["bands"].iloc[-1]
    out["Bollinger"] = "au-dessus" if close > b["upper"] else "en dessous" if close < b["lower"] else "intérieur"
    m = e["macd"].iloc[-1]
    out["MACD / signal"] = "au-dessus" if m["macd"] > m["signal"] else "sous"

    info = bundle.get("info") or {}
    fd = fundamental.details.set_index("cle")
    out["PER société"] = _round(fd.loc["per", "Société"]) if "per" in fd.index else None
    out["PER secteur"] = _round(fd.loc["per", "Secteur"]) if "per" in fd.index else None
    out["ROE"] = _round(info.get("returnOnEquity") * 100) if info.get("returnOnEquity") else None
    bs = bundle.get("balance_sheet")
    if bs is not None and "Net Debt" in bs.index and "Stockholders Equity" in bs.index:
        col = sorted(bs.columns)[-1]
        nd, eq = pd.to_numeric(bs.loc["Net Debt", col]), pd.to_numeric(bs.loc["Stockholders Equity", col])
        out["Ratio endettement net"] = _round(nd / eq * 100) if eq else None
    out["Valorisation / Ebitda"] = _round(info.get("enterpriseToEbitda"))
    return out


def _round(x, nd=2):
    return None if is_missing(x) else round(float(x), nd)


def abc_comparison(workbook, ticker, technical, fundamental, bundle) -> pd.DataFrame:
    ours = our_abc_values(technical, fundamental, bundle)
    theirs = inputs.read_abc_controls(workbook, ticker)
    theirs = dict(zip(theirs["Indicateur"], zip(theirs["Valeur ABC Bourse"], theirs["Date du relevé"])))
    rows = []
    for indicator, value in ours.items():
        abc, date = theirs.get(indicator, (None, None))
        status = "à relever sur la fiche ABC"
        gap = None
        if not is_missing(abc) and abc not in ("", None):
            num = pd.to_numeric(str(abc).replace(",", ".").replace("%", "").replace("x", ""), errors="coerce")
            if isinstance(value, (int, float)) and pd.notna(num) and value is not None:
                gap = value - float(num)
                status = "cohérent" if abs(gap) <= max(0.05 * abs(float(num)), 0.5) else "ÉCART à expliquer"
            else:
                same = str(value).lower()[:4] == str(abc).lower().strip()[:4]
                status = "cohérent" if same else "ÉCART à expliquer"
        rows.append({"Indicateur": indicator, "Notre valeur": value, "Valeur ABC Bourse": abc,
                     "Date du relevé ABC": date, "Écart": gap, "Statut": status})
    return pd.DataFrame(rows)
