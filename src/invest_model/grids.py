"""Grilles de notation : transforment une valeur brute en note.

Une même fonction sert pour tous les indicateurs « continus » (RSI, ratios,
probabilités...). Les bornes viennent de config/parametres.yaml : changer une
grille ne demande pas de toucher au code.
"""

from __future__ import annotations

import math
from bisect import bisect_right


def is_missing(value) -> bool:
    """Vrai si la valeur est absente (None ou NaN)."""
    return value is None or (isinstance(value, float) and math.isnan(value))


def note_from_bounds(value: float | None, bounds: list[float], higher_is_better: bool = True) -> int | None:
    """Note -2..+2 à partir de 4 bornes croissantes [b1, b2, b3, b4].

    Intervalles : ]-inf, b1[  [b1, b2[  [b2, b3[  [b3, b4[  [b4, +inf[
    - plus_haut_mieux = True  : notes -2, -1, 0, +1, +2
    - plus_haut_mieux = False : notes +2, +1, 0, -1, -2
    Exemple RSI, bornes [30, 40, 60, 70], plus_haut_mieux False : RSI 25 -> +2, RSI 75 -> -2.
    Renvoie None si la valeur est absente.
    """
    if is_missing(value):
        return None
    if len(bounds) != 4 or sorted(bounds) != list(bounds):
        raise ValueError(f"Il faut 4 bornes croissantes, reçu : {bounds}")
    position = bisect_right(bounds, value)        # 0..4 : nb de bornes <= valeur
    notes = [-2, -1, 0, 1, 2] if higher_is_better else [2, 1, 0, -1, -2]
    return notes[position]


def level_1_to_5(value: float | None, bounds: list[float]) -> int | None:
    """Niveau 1..5 (matrice de risque) : plus la valeur est haute, plus le niveau est haut."""
    if is_missing(value):
        return None
    return bisect_right(bounds, value) + 1


def weighted_mean(values: dict[str, float | None], weights: dict[str, float]) -> float | None:
    """Moyenne pondérée en ignorant les valeurs absentes (poids renormalisés).

    Renvoie None si aucune valeur n'est disponible.
    """
    pairs = [(v, weights.get(k, 1.0)) for k, v in values.items() if not is_missing(v)]
    total = sum(w for _, w in pairs)
    if not pairs or total == 0:
        return None
    return sum(v * w for v, w in pairs) / total
