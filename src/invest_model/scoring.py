"""Combinaison des notes : quantitatif / qualitatif, puis entre piliers (conception §9.1).

Pour les piliers Graphique, Financier, Informations :
    S_p = lambda_p * Quanti_p + (1 - lambda_p) * Quali_p
Pilier Hasard : S_H = Quanti_H (pas de qualitatif).
Score final :
    S = somme(W_p * S_p) / somme(W_p)      -> reste dans [-2, +2]

Si une composante manque (ex. pas encore de note qualitative), on utilise l'autre
seule et on le signale : le score reste calculable, mais le rapport l'indique.
"""

from __future__ import annotations

import pandas as pd

from .grids import is_missing
from .pillars.result import PillarResult

PILLAR_KEYS = {"Graphique": "graphique", "Financier": "financier", "Informations": "informations",
               "Hasard": "hasard"}


def pillar_score(p: PillarResult, quanti_share: float | None) -> tuple[float | None, str]:
    """Score d'un pilier et explication de la combinaison utilisée."""
    q, l = p.quanti, p.quali
    if quanti_share is None:                       # pilier sans qualitatif (Hasard)
        return q, "quantitatif seul (pas de qualitatif pour ce pilier)"
    if not is_missing(q) and not is_missing(l):
        return quanti_share * q + (1 - quanti_share) * l, f"{quanti_share:.0%} quanti + {1 - quanti_share:.0%} quali"
    if not is_missing(q):
        return q, "quantitatif seul (qualitatif non saisi)"
    if not is_missing(l):
        return l, "qualitatif seul (quantitatif indisponible)"
    return None, "aucune note disponible"


def combine(pillars: list[PillarResult], weights: dict, quanti_share: dict) -> tuple[float | None, pd.DataFrame]:
    """Renvoie (score final, tableau de détail par pilier)."""
    rows = []
    total_w, total = 0.0, 0.0
    for p in pillars:
        key = PILLAR_KEYS[p.name]
        score, how = pillar_score(p, quanti_share.get(key))
        w = float(weights.get(key, 0))
        if not is_missing(score) and w > 0:
            total_w += w
            total += w * score
        rows.append({"Pilier": p.name, "Quantitatif": p.quanti, "Qualitatif": p.quali,
                     "Part quanti": quanti_share.get(key), "Score du pilier": score,
                     "Combinaison": how, "Poids": w})
    table = pd.DataFrame(rows)
    final = total / total_w if total_w else None
    table["Contribution"] = table.apply(
        lambda r: (r["Poids"] * r["Score du pilier"] / total_w) if total_w and not is_missing(r["Score du pilier"])
        else None, axis=1)
    return final, table
