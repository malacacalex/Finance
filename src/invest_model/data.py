"""Données de marché : téléchargement yfinance et instantanés datés.

Pourquoi des instantanés ? yfinance renvoie des données qui changent dans le temps
(et le service peut être indisponible). On fige donc chaque téléchargement dans
data/snapshots/AAAA-MM-JJ/<TICKER>/ : on peut relancer l'analyse à l'identique,
sans réseau, et le professeur peut vérifier les mêmes chiffres (GRP-24).
"""

from __future__ import annotations

import json
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

# Nature de chaque élément d'un instantané -> format de fichier
#   frame  : DataFrame -> CSV       series : Series -> CSV       json : dict/list -> JSON
SCHEMA = {
    "prices": "frame",
    "benchmark": "frame",
    "peer_prices": "frame",
    "financials": "frame",
    "balance_sheet": "frame",
    "cashflow": "frame",
    "dividends": "series",
    "recommendations": "frame",
    "earnings_estimate": "frame",
    "revenue_estimate": "frame",
    "growth_estimates": "frame",
    "eps_trend": "frame",
    "major_holders": "frame",
    "institutional_holders": "frame",
    "info": "json",
    "peers_info": "json",
    "analyst_targets": "json",
    "calendar": "json",
    "news_yahoo": "json",
    "meta": "json",
}


def _strip_tz(obj):
    """Retire le fuseau horaire de l'index (on travaille à la journée)."""
    if obj is not None and isinstance(obj.index, pd.DatetimeIndex) and obj.index.tz is not None:
        obj = obj.copy()
        obj.index = obj.index.tz_localize(None).normalize()
    return obj


def fetch_company(ticker: str, peers: list[str], benchmark: str, period: str = "2y") -> dict:
    """Télécharge tout ce qui est disponible sur une société via yfinance.

    Chaque appel est protégé : une donnée manquante n'arrête pas l'analyse, elle est
    notée dans meta["avertissements"] (puis dans l'onglet Journal du rapport).
    """
    import yfinance as yf

    warnings.filterwarnings("ignore")
    notes: list[str] = []
    t = yf.Ticker(ticker)

    def safe(label, func):
        try:
            value = func()
            if value is None or (hasattr(value, "empty") and value.empty):
                notes.append(f"{label} : aucune donnée renvoyée par yfinance")
                return None
            return value
        except Exception as exc:  # l'API non officielle peut échouer ponctuellement
            notes.append(f"{label} : erreur yfinance ({exc.__class__.__name__})")
            return None

    bundle: dict = {}
    # auto_adjust=False : on garde "Close" (ajusté des divisions/attributions) pour les
    # indicateurs, comme les graphiques boursiers, et "Adj Close" (dividendes réinvestis)
    # pour les rendements de Monte Carlo.
    bundle["prices"] = _strip_tz(safe("cours", lambda: t.history(period=period, auto_adjust=False)))
    bundle["info"] = safe("profil et ratios", lambda: t.info) or {}
    bundle["financials"] = safe("compte de résultat", lambda: t.financials)
    bundle["balance_sheet"] = safe("bilan", lambda: t.balance_sheet)
    bundle["cashflow"] = safe("flux de trésorerie", lambda: t.cashflow)
    bundle["dividends"] = _strip_tz(safe("dividendes", lambda: t.dividends))
    bundle["recommendations"] = safe("recommandations", lambda: t.recommendations_summary)
    bundle["earnings_estimate"] = safe("estimations BPA", lambda: t.earnings_estimate)
    bundle["revenue_estimate"] = safe("estimations CA", lambda: t.revenue_estimate)
    bundle["growth_estimates"] = safe("estimations croissance", lambda: t.growth_estimates)
    bundle["eps_trend"] = safe("tendance BPA", lambda: t.eps_trend)
    bundle["major_holders"] = safe("actionnariat", lambda: t.major_holders)
    bundle["institutional_holders"] = safe("institutionnels", lambda: t.institutional_holders)
    bundle["analyst_targets"] = safe("objectifs analystes", lambda: t.analyst_price_targets) or {}
    bundle["calendar"] = safe("calendrier", lambda: t.calendar) or {}
    bundle["news_yahoo"] = [_simplify_news(n) for n in (safe("actualités Yahoo", lambda: t.news) or [])]

    # Indice de référence et pairs (cours 1 an + ratios)
    bundle["benchmark"] = _strip_tz(safe(f"indice {benchmark}", lambda: yf.Ticker(benchmark).history(period=period)))
    bundle["peers_info"] = {}
    closes = {}
    for peer in peers:
        p = yf.Ticker(peer)
        bundle["peers_info"][peer] = safe(f"ratios du pair {peer}", lambda: p.info) or {}
        hist = _strip_tz(safe(f"cours du pair {peer}", lambda: p.history(period=period)))
        if hist is not None:
            closes[peer] = hist["Close"]
    bundle["peer_prices"] = pd.DataFrame(closes) if closes else None

    bundle["meta"] = {
        "ticker": ticker,
        "telecharge_le": datetime.now().isoformat(timespec="seconds"),
        "source": "yfinance " + getattr(yf, "__version__", "?"),
        "pairs": peers,
        "indice": benchmark,
        "avertissements": notes,
    }
    return bundle


def _simplify_news(item: dict) -> dict:
    """Garde l'essentiel d'une actualité Yahoo (le format brut est très verbeux)."""
    c = item.get("content", item)
    url = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url")
    return {
        "date": c.get("pubDate"),
        "titre": c.get("title"),
        "resume": c.get("summary"),
        "source": (c.get("provider") or {}).get("displayName"),
        "url": url,
    }


# ---------------------------------------------------------------------------
# Instantanés
# ---------------------------------------------------------------------------

def snapshot_dir(root: Path, date: str, ticker: str) -> Path:
    return root / date / ticker


def save_snapshot(bundle: dict, root: Path, date: str, ticker: str) -> Path:
    """Écrit chaque élément du bundle dans son fichier (CSV ou JSON)."""
    folder = snapshot_dir(root, date, ticker)
    folder.mkdir(parents=True, exist_ok=True)
    for name, kind in SCHEMA.items():
        value = bundle.get(name)
        if value is None:
            continue
        if kind in ("frame", "series"):
            value.to_csv(folder / f"{name}.csv")
        else:
            with open(folder / f"{name}.json", "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False, indent=1, default=str)
    return folder


def load_snapshot(root: Path, date: str, ticker: str) -> dict:
    """Relit un instantané écrit par save_snapshot."""
    folder = snapshot_dir(root, date, ticker)
    if not folder.exists():
        raise FileNotFoundError(f"Instantané introuvable : {folder}")
    bundle: dict = {}
    for name, kind in SCHEMA.items():
        path = folder / (f"{name}.json" if kind == "json" else f"{name}.csv")
        if not path.exists():
            bundle[name] = {} if kind == "json" else None
            continue
        if kind == "json":
            with open(path, encoding="utf-8") as f:
                bundle[name] = json.load(f)
        else:
            frame = pd.read_csv(path, index_col=0)
            if name in ("prices", "benchmark", "peer_prices", "dividends"):
                frame.index = pd.to_datetime(frame.index)
            bundle[name] = frame.iloc[:, 0] if kind == "series" else frame
    return bundle


def latest_snapshot_date(root: Path, ticker: str) -> str | None:
    """Date (AAAA-MM-JJ) du dernier instantané disponible pour ce ticker."""
    if not root.exists():
        return None
    dates = sorted(p.parent.name for p in root.glob(f"*/{ticker}") if p.is_dir())
    return dates[-1] if dates else None
