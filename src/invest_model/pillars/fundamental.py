"""Pilier 2 — Financier.

Ratios de la société comparés à la MÉDIANE de ses pairs (GRP-04), notés -2..+2.
Définitions et leçons ABC Bourse : docs/indicateurs/ratios-financiers.md.
"""

from __future__ import annotations

import statistics

import pandas as pd

from ..grids import is_missing, note_from_bounds, weighted_mean
from .result import PillarResult

LABELS = {
    "per": "PER (cours / BPA)",
    "peg": "PEG (PER / croissance attendue)",
    "rendement": "Rendement du dividende",
    "roe": "ROE (résultat net / capitaux propres)",
    "dette_ebitda": "Dette nette / EBITDA",
    "marge_op": "Marge opérationnelle",
}

SOURCES = {
    "per": "ABC Leçon 9 : https://www.abcbourse.com/apprendre/12_lecon_af_9_partie2.html",
    "peg": "ABC Leçon 9 : https://www.abcbourse.com/apprendre/12_lecon_af_9_partie2.html",
    "rendement": "ABC Les dividendes : https://www.abcbourse.com/apprendre/1_les_dividendes1.html",
    "roe": "Définition standard (critère ROE > 10 % des fiches ABC)",
    "dette_ebitda": "Définition standard (absent des leçons ABC)",
    "marge_op": "Définition standard (marge opérationnelle des fiches ABC)",
}


def compute_ratios(info: dict, growth_estimates: pd.DataFrame | None = None) -> dict:
    """Calcule les ratios d'une société à partir des données yfinance.

    Renvoie {ratio: (valeur, provenance)}. La provenance indique si la valeur vient
    directement de yfinance ou si on l'a calculée (champ absent).
    """
    out: dict = {}
    price = info.get("currentPrice") or info.get("regularMarketPrice")

    # PER = cours / BPA des 12 derniers mois
    if info.get("trailingPE"):
        out["per"] = (info["trailingPE"], "yfinance")
    elif price and info.get("trailingEps"):
        out["per"] = (price / info["trailingEps"], "calculé : cours / BPA")
    else:
        out["per"] = (None, "indisponible")

    # PEG = PER / croissance attendue des bénéfices (en %)
    peg = info.get("trailingPegRatio") or info.get("pegRatio")
    if peg:
        out["peg"] = (peg, "yfinance")
    else:
        growth = _growth_next_year(growth_estimates)
        per = out["per"][0]
        if per and growth and growth > 0:
            out["peg"] = (per / (growth * 100), "calculé : PER / croissance BPA +1 an")
        else:
            out["peg"] = (None, "indisponible")

    # Rendement = dividendes versés sur 12 mois / cours
    if info.get("trailingAnnualDividendYield") is not None:
        out["rendement"] = (info["trailingAnnualDividendYield"], "yfinance (12 mois glissants)")
    elif price and info.get("dividendRate"):
        out["rendement"] = (info["dividendRate"] / price, "calculé : dividende / cours")
    else:
        out["rendement"] = (None, "indisponible")

    out["roe"] = (info.get("returnOnEquity"), "yfinance") if info.get("returnOnEquity") is not None \
        else (None, "indisponible")

    # Dette nette / EBITDA = (dettes financières - trésorerie) / EBITDA
    debt, cash, ebitda = info.get("totalDebt"), info.get("totalCash"), info.get("ebitda")
    if debt is not None and cash is not None and ebitda:
        out["dette_ebitda"] = ((debt - cash) / ebitda, "calculé : (dette - trésorerie) / EBITDA")
    else:
        out["dette_ebitda"] = (None, "indisponible")

    out["marge_op"] = (info.get("operatingMargins"), "yfinance") if info.get("operatingMargins") is not None \
        else (None, "indisponible")
    return out


def _growth_next_year(growth_estimates: pd.DataFrame | None) -> float | None:
    """Croissance attendue du BPA à +1 an (consensus), si disponible."""
    if growth_estimates is None or growth_estimates.empty:
        return None
    try:
        value = growth_estimates.loc["+1y", "stockTrend"]
        return None if is_missing(float(value)) else float(value)
    except (KeyError, ValueError, TypeError):
        return None


def analyse_fundamental(
    info: dict,
    peers_info: dict,
    cfg: dict,
    growth_estimates: pd.DataFrame | None = None,
    sector_overrides: dict | None = None,
) -> PillarResult:
    """Compare la société à la médiane de ses pairs et note chaque ratio.

    sector_overrides : {ratio: (valeur, source)} saisis par le groupe (onglet
    Secteur_Override) qui remplacent la médiane calculée.
    """
    warnings: list[str] = []
    company = compute_ratios(info, growth_estimates)
    peers = {t: compute_ratios(i) for t, i in peers_info.items() if i}
    sector_overrides = sector_overrides or {}

    rows, notes = [], {}
    for key, rcfg in cfg["ratios"].items():
        value, origin = company.get(key, (None, "indisponible"))
        peer_values = {t: r[key][0] for t, r in peers.items() if not is_missing(r[key][0])}
        median = statistics.median(peer_values.values()) if peer_values else None
        median_src = f"médiane de {len(peer_values)} pair(s)"
        if key in sector_overrides:
            median, median_src = sector_overrides[key]
            median_src = f"saisi : {median_src}"

        relative = None
        if not is_missing(value) and median not in (None, 0) and median > 0:
            relative = value / median

        # Cas particuliers documentés
        if key == "dette_ebitda" and not is_missing(value) and value < 0:
            note = 2                                    # trésorerie nette positive
        elif key == "per" and not is_missing(value) and value <= 0:
            note = None
            warnings.append("PER négatif (pertes) : ratio non noté")
        else:
            x = relative if rcfg["mode"] == "relatif" else value
            note = note_from_bounds(x, rcfg["bornes"], rcfg["plus_haut_mieux"])
        if note is None and is_missing(value):
            warnings.append(f"{LABELS[key]} : indisponible, exclu de la note")
        notes[key] = note

        rows.append({
            "cle": key,
            "Ratio": LABELS[key],
            "Société": value,
            "Provenance": origin,
            "Secteur": median,
            "Référence secteur": median_src,
            "Relatif (société / secteur)": relative,
            **{f"Pair {t}": v for t, v in peer_values.items()},
            "Note": note,
            "Poids": rcfg["poids"],
            "Source définition": SOURCES[key],
        })

    details = pd.DataFrame(rows)
    quanti = weighted_mean(notes, {k: v["poids"] for k, v in cfg["ratios"].items()})

    # Contrôles absolus cités par ABC Bourse (affichés, non notés)
    checks = cfg.get("controles_abc", {})
    abc_checks = []
    if not is_missing(company["peg"][0]):
        abc_checks.append(("PEG < 1 (Leçon 9)", company["peg"][0] < checks.get("peg_max", 1.0)))
    if not is_missing(company["roe"][0]):
        abc_checks.append(("ROE > 10 % (fiche Analyse et conseil)", company["roe"][0] > checks.get("roe_min", 0.10)))

    return PillarResult(
        name="Financier",
        quanti=quanti,
        details=details,
        warnings=warnings,
        extra={"company": company, "peers": peers, "abc_checks": abc_checks},
    )


# ---------------------------------------------------------------------------
# Informations complémentaires (non notées) : historique, dividendes, analystes
# ---------------------------------------------------------------------------

STATEMENT_ROWS = {
    "Chiffre d'affaires": ("financials", "Total Revenue"),
    "EBITDA": ("financials", "EBITDA"),
    "Résultat opérationnel": ("financials", "Operating Income"),
    "Résultat net": ("financials", "Net Income"),
    "BPA dilué": ("financials", "Diluted EPS"),
    "Flux de trésorerie opérationnel": ("cashflow", "Operating Cash Flow"),
    "Investissements (capex)": ("cashflow", "Capital Expenditure"),
    "Flux de trésorerie disponible": ("cashflow", "Free Cash Flow"),
    "Dividendes versés": ("cashflow", "Cash Dividends Paid"),
    "Dette totale": ("balance_sheet", "Total Debt"),
    "Dette nette": ("balance_sheet", "Net Debt"),
    "Capitaux propres": ("balance_sheet", "Stockholders Equity"),
}


def financial_history(bundle: dict) -> pd.DataFrame:
    """Tableau des grands postes financiers sur les derniers exercices + ratios dérivés."""
    data = {}
    for label, (source, row) in STATEMENT_ROWS.items():
        frame = bundle.get(source)
        if frame is not None and row in frame.index:
            data[label] = frame.loc[row]
    if not data:
        return pd.DataFrame()
    table = pd.DataFrame(data).T
    table.columns = [str(c)[:4] for c in table.columns]          # années
    table = table[sorted(table.columns)]                         # ordre chronologique

    def ratio(num, den):
        if num in table.index and den in table.index:
            return table.loc[num] / table.loc[den]
        return None

    derived = {
        "Marge opérationnelle": ratio("Résultat opérationnel", "Chiffre d'affaires"),
        "Marge nette": ratio("Résultat net", "Chiffre d'affaires"),
        "ROE": ratio("Résultat net", "Capitaux propres"),
        "Dette nette / EBITDA": ratio("Dette nette", "EBITDA"),
        "Gearing (dette nette / capitaux propres)": ratio("Dette nette", "Capitaux propres"),
    }
    for label, series in derived.items():
        if series is not None:
            table.loc[label] = series
    if "Chiffre d'affaires" in table.index:
        table.loc["Croissance du CA"] = table.loc["Chiffre d'affaires"].pct_change()
    return table


def dividend_history(dividends: pd.Series | None) -> pd.DataFrame:
    """Dividende par action et par année civile, avec la croissance annuelle."""
    if dividends is None or len(dividends) == 0:
        return pd.DataFrame()
    yearly = dividends.groupby(dividends.index.year).sum()
    table = pd.DataFrame({"Dividende par action": yearly, "Croissance": yearly.pct_change()})
    table.index.name = "Année"
    return table


def analyst_view(bundle: dict) -> dict:
    """Consensus des analystes : objectifs de cours et recommandations."""
    targets = bundle.get("analyst_targets") or {}
    out = {
        "objectif_moyen": targets.get("mean"),
        "objectif_median": targets.get("median"),
        "objectif_haut": targets.get("high"),
        "objectif_bas": targets.get("low"),
        "cours": targets.get("current"),
        "nb_analystes": (bundle.get("info") or {}).get("numberOfAnalystOpinions"),
        "recommandation": (bundle.get("info") or {}).get("recommendationKey"),
    }
    if out["objectif_moyen"] and out["cours"]:
        out["potentiel"] = out["objectif_moyen"] / out["cours"] - 1
    rec = bundle.get("recommendations")
    if rec is not None and not rec.empty:
        current = rec.iloc[0]
        out["repartition"] = {k: int(current[k]) for k in ["strongBuy", "buy", "hold", "sell", "strongSell"]
                              if k in current}
    return out
