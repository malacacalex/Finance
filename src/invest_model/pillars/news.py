"""Pilier 3 — Informations.

Entrée : les actualités de l'onglet `Actualites` de data/saisies.xlsx (pré-remplies par
la veille, classées par le groupe).

- QUANTITATIF (comptage et classement) :
    net = (somme des poids des nouvelles positives - somme des poids des négatives)
          / (somme des poids des nouvelles positives et négatives)
  où le poids d'une nouvelle est celui de sa catégorie (résultats > communiqué > ...).
  net est dans [-1, 1] puis converti en note -2..+2 par une grille.
- QUALITATIF (importance et fiabilité, notées par le groupe) :
    moyenne des notes du groupe (-2..+2) pondérée par la fiabilité (1..3).
"""

from __future__ import annotations

import pandas as pd

from ..grids import is_missing, note_from_bounds
from .result import PillarResult


def analyse_news(news: pd.DataFrame, as_of: pd.Timestamp, cfg: dict) -> PillarResult:
    warnings: list[str] = []
    if news is None or news.empty:
        return PillarResult("Informations", quanti=None, quali=None,
                            warnings=["Aucune actualité disponible pour le pilier Informations"])

    df = news.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    start = as_of - pd.Timedelta(days=cfg["fenetre_jours"])
    df = df[(df["date"].isna()) | ((df["date"] >= start) & (df["date"] <= as_of + pd.Timedelta(days=1)))]

    # Sens utilisé pour le comptage : signe de la note du groupe, sinon suggestion
    def direction(row):
        if not is_missing(row.get("note")):
            return (float(row["note"]) > 0) - (float(row["note"]) < 0), "groupe"
        allowed = cfg.get("categories_suggestions")
        if (cfg.get("utiliser_suggestions") and not is_missing(row.get("sens_suggere"))
                and (allowed is None or row.get("categorie") in allowed)):
            return int(row["sens_suggere"]), "suggestion"
        return 0, "non classée"

    res = df.apply(direction, axis=1, result_type="expand")
    df["sens"], df["sens_origine"] = res[0], res[1]
    df["poids_categorie"] = df["categorie"].map(cfg["poids_categories"]).fillna(1)

    pos = df.loc[df["sens"] > 0, "poids_categorie"].sum()
    neg = df.loc[df["sens"] < 0, "poids_categorie"].sum()
    net = (pos - neg) / (pos + neg) if (pos + neg) > 0 else 0.0
    grid = cfg["grille_net"]
    quanti = note_from_bounds(net, grid["bornes"], grid["plus_haut_mieux"])

    n_suggest = int((df["sens_origine"] == "suggestion").sum())
    n_unclassified = int((df["sens_origine"] == "non classée").sum())
    if n_suggest:
        warnings.append(f"Informations : {n_suggest} nouvelle(s) comptée(s) avec le sens SUGGÉRÉ "
                        "automatiquement (à confirmer par le groupe dans saisies.xlsx)")
    if n_unclassified:
        warnings.append(f"Informations : {n_unclassified} nouvelle(s) neutre(s) ou non classée(s)")

    # Qualitatif : uniquement les nouvelles notées par le groupe
    graded = df[df["note"].notna()] if "note" in df else df.iloc[0:0]
    quali = None
    if not graded.empty:
        fiab = pd.to_numeric(graded["fiabilite"], errors="coerce").fillna(1)
        quali = float((pd.to_numeric(graded["note"]) * fiab).sum() / fiab.sum())
    else:
        warnings.append("Informations : aucune nouvelle notée par le groupe -> pas de qualitatif")

    summary = pd.DataFrame([
        ("Nouvelles dans la fenêtre", len(df)),
        ("Positives (nombre)", int((df["sens"] > 0).sum())),
        ("Négatives (nombre)", int((df["sens"] < 0).sum())),
        ("Neutres / non classées", int((df["sens"] == 0).sum())),
        ("Poids positif (catégories)", pos),
        ("Poids négatif (catégories)", neg),
        ("Solde net (-1..+1)", round(net, 3)),
        ("Nouvelles notées par le groupe", len(graded)),
    ], columns=["Mesure", "Valeur"])

    by_category = (df.groupby("categorie")["sens"]
                   .agg(total="count", positives=lambda s: (s > 0).sum(), negatives=lambda s: (s < 0).sum())
                   .reset_index())

    return PillarResult(
        name="Informations",
        quanti=quanti,
        quali=quali,
        details=summary,
        warnings=warnings,
        extra={"news": df.sort_values("date", ascending=False), "net": net,
               "by_category": by_category, "negative_share": (df["sens"] < 0).mean() if len(df) else 0.0},
    )
