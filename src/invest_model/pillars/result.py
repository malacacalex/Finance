"""Structure commune aux résultats des piliers."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class PillarResult:
    """Résultat d'un pilier pour une société.

    - quanti : note quantitative -2..+2 (None si non calculable) ;
    - quali  : note qualitative -2..+2 saisie par le groupe (None si absente) ;
    - details : tableau « indicateur -> valeur -> note », affiché dans le rapport ;
    - extra : informations complémentaires (niveaux, séries pour les graphiques...) ;
    - warnings : messages pour l'onglet Journal.
    """

    name: str
    quanti: float | None
    quali: float | None = None
    details: pd.DataFrame = field(default_factory=pd.DataFrame)
    extra: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
