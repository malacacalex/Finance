"""Veille d'actualités par dorking (GRP-12, conception §7.1).

Source principale : Google News RSS, gratuit et sans clé, qui accepte les
opérateurs de recherche avancée ("…", OR, -, site:, intitle:, when:7d).
On n'interroge PAS la page de recherche Google classique (bloquée pour les robots
et interdite par ses conditions d'utilisation).

Les nouvelles sont PRÉ-REMPLIES (catégorie, fiabilité suggérée, sens suggéré) ;
la note reste donnée par le groupe dans data/saisies.xlsx.
"""

from __future__ import annotations

import time
import unicodedata
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse

import pandas as pd
import requests

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
HEADERS = {"User-Agent": "Mozilla/5.0 (projet-etudiant-veille-boursiere)"}


def strip_accents(text: str) -> str:
    """'Relève' -> 'releve' : permet de comparer sans se soucier des accents."""
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def build_queries(company: dict, cfg: dict) -> dict[str, str]:
    """Construit les requêtes de dorking d'une société à partir des modèles."""
    queries = {}
    for category, template in cfg["modeles"].items():
        q = template.format(
            nom=company["nom"],
            secteur_requete=company.get("secteur_requete", ""),
            site_ir=company.get("site_ir", ""),
        )
        queries[category] = f"{q} {cfg.get('fenetre', '')}".strip()
    return queries


def google_news(query: str, lang: dict, timeout: int = 20, retries: int = 3) -> list[dict]:
    """Interroge le flux RSS Google News et renvoie une liste d'articles.

    En cas de limitation de débit (HTTP 429) ou d'indisponibilité (503), on attend
    puis on réessaie (5 s, 10 s, 20 s).
    """
    url = GOOGLE_NEWS_RSS.format(q=quote_plus(query), **lang)
    for attempt in range(retries + 1):
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        if response.status_code not in (429, 503) or attempt == retries:
            break
        time.sleep(5 * 2 ** attempt)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    for item in root.iter("item"):
        source = item.find("source")
        title = item.findtext("title") or ""
        source_name = source.text if source is not None else ""
        # Google ajoute " - Source" à la fin du titre : on le retire
        if source_name and title.endswith(" - " + source_name):
            title = title[: -len(" - " + source_name)]
        items.append({
            "date": _parse_date(item.findtext("pubDate")),
            "titre": title.strip(),
            "source": source_name,
            "domaine": _domain(source.get("url") if source is not None else ""),
            "url": item.findtext("link"),
        })
    return items


def _parse_date(text: str | None):
    try:
        return parsedate_to_datetime(text).replace(tzinfo=None) if text else None
    except (TypeError, ValueError):
        return None


def _domain(url: str) -> str:
    host = urlparse(url or "").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def suggest_reliability(domain: str, cfg: dict) -> int:
    """Fiabilité SUGGÉRÉE (1..3) selon le domaine de la source."""
    for level in (3, 2):
        for known in cfg.get("fiabilite_sources", {}).get(level, []):
            if domain == known or domain.endswith("." + known):
                return level
    return 1


def suggest_direction(title: str, lexicon: dict) -> int:
    """Sens SUGGÉRÉ d'un titre (+1, 0, -1) par recherche de mots du lexique.

    Ce n'est PAS une note du groupe : c'est une aide au tri, signalée comme telle.
    """
    text = strip_accents(title)
    pos = any(strip_accents(w) in text for w in lexicon.get("positif", []))
    neg = any(strip_accents(w) in text for w in lexicon.get("negatif", []))
    return int(pos) - int(neg)


def is_relevant(title: str, category: str, keywords: list[str]) -> bool:
    """Garde les titres qui citent la société (sauf actualités secteur et macro)."""
    if category in ("secteur", "macro"):
        return True
    text = strip_accents(title)
    return any(strip_accents(k) in text for k in keywords)


def collect_news(ticker: str, company: dict, cfg: dict, yahoo_news: list[dict] | None = None,
                 log: list[str] | None = None) -> pd.DataFrame:
    """Lance toutes les requêtes d'une société et renvoie un tableau dédoublonné."""
    log = log if log is not None else []
    rows = []
    for category, query in build_queries(company, cfg).items():
        try:
            articles = google_news(query, cfg["langue"])
        except Exception as exc:
            log.append(f"Veille « {category} » : échec de la requête ({exc.__class__.__name__})")
            continue
        relevant = [a for a in articles if is_relevant(a["titre"], category, company["mots_cles"])]
        relevant.sort(key=lambda a: a["date"] or pd.Timestamp.min, reverse=True)
        for a in relevant[: cfg.get("max_par_categorie", 20)]:      # les plus récentes d'abord
            rows.append({**a, "categorie": category, "requete": query, "origine": "Google News"})
        time.sleep(cfg.get("pause_secondes", 1.0))

    # Actualités Yahoo Finance (déjà dans l'instantané)
    for n in yahoo_news or []:
        if n.get("titre"):
            rows.append({
                "date": pd.to_datetime(n.get("date"), errors="coerce", utc=True).tz_localize(None)
                if n.get("date") else None,
                "titre": n["titre"], "source": n.get("source") or "Yahoo Finance",
                "domaine": _domain(n.get("url") or ""), "url": n.get("url"),
                "categorie": "presse", "requete": "yfinance Ticker.news", "origine": "Yahoo Finance",
            })

    if not rows:
        return pd.DataFrame(columns=["date", "titre", "source", "domaine", "url", "categorie",
                                     "requete", "origine", "ticker", "fiabilite_suggeree",
                                     "sens_suggere"])
    df = pd.DataFrame(rows)
    df["ticker"] = ticker
    df["fiabilite_suggeree"] = df["domaine"].map(lambda d: suggest_reliability(d, cfg))
    df["sens_suggere"] = df["titre"].map(lambda t: suggest_direction(t, cfg.get("lexique", {})))
    df["cle"] = df["titre"].map(_dedup_key)
    df = df.sort_values("date", ascending=False).drop_duplicates("cle").drop(columns="cle")
    log.append(f"Veille {ticker} : {len(df)} actualité(s) distincte(s) collectée(s)")
    return df.reset_index(drop=True)


def _dedup_key(title: str) -> str:
    """Clé de dédoublonnage : titre sans accents ni ponctuation."""
    return "".join(ch for ch in strip_accents(title) if ch.isalnum())
