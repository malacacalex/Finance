"""Pilier 4 — Hasard : simulation de Monte Carlo (mouvement brownien géométrique).

Modèle, au pas d'une séance :
    S(t+1) = S(t) * exp(m + sigma * eps(t)),  eps ~ N(0, 1)
où m et sigma sont la MOYENNE et l'ÉCART-TYPE des log-rendements quotidiens
historiques. Remarque : m correspond au terme (mu - sigma²/2) de la formule
usuelle S(t+dt) = S(t) exp((mu - sigma²/2) dt + sigma sqrt(dt) Z). Comme on
l'estime directement sur les log-rendements, on ne retranche PAS sigma²/2 une
seconde fois.

Plusieurs actions : eps = L @ Z avec L L' = matrice de corrélation (Cholesky).

Équivalence utilisée pour la vérification Excel : après h séances,
    S(h) = S0 * exp(h*m + sigma * somme(eps)) = S0 * exp(h*m + sigma*sqrt(h)*Z_eq)
avec Z_eq = somme(eps) / sqrt(h) ~ N(0, 1). La valeur finale peut donc être
recalculée en UNE formule dans Excel.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..grids import note_from_bounds
from .result import PillarResult


@dataclass
class GBMParams:
    s0: float          # dernier cours
    m: float           # moyenne des log-rendements quotidiens
    sigma: float       # écart-type des log-rendements quotidiens
    n_obs: int         # nombre de rendements utilisés

    @property
    def mu_annual(self) -> float:
        """Rendement arithmétique annualisé correspondant : (m + sigma²/2) * 252."""
        return (self.m + self.sigma ** 2 / 2) * 252

    @property
    def sigma_annual(self) -> float:
        return self.sigma * np.sqrt(252)


def estimate_params(prices: pd.Series, window: int) -> GBMParams:
    """Estime m et sigma sur les `window` derniers log-rendements."""
    log_returns = np.log(prices / prices.shift(1)).dropna().iloc[-window:]
    return GBMParams(
        s0=float(prices.iloc[-1]),
        m=float(log_returns.mean()),
        sigma=float(log_returns.std(ddof=1)),
        n_obs=len(log_returns),
    )


def simulate_gbm(s0, m, sigma, n_days: int, n_sims: int, seed: int, corr=None):
    """Simule des trajectoires de cours.

    Accepte une action (scalaires) ou plusieurs (vecteurs + matrice de corrélation).
    Renvoie (paths, z) :
    - paths : tableau (n_sims, n_days + 1[, n_assets]) des cours simulés ;
    - z     : tirages N(0,1) indépendants (n_sims, n_days[, n_assets]), avant corrélation.
    """
    rng = np.random.default_rng(seed)
    s0, m, sigma = np.atleast_1d(s0), np.atleast_1d(m), np.atleast_1d(sigma)
    n_assets = len(s0)
    z = rng.standard_normal((n_sims, n_days, n_assets))
    if corr is not None and n_assets > 1:
        chol = np.linalg.cholesky(np.asarray(corr))   # L tel que L @ L.T = corr
        eps = z @ chol.T                               # chaque ligne : L @ z
    else:
        eps = z
    log_steps = m + sigma * eps                         # (n_sims, n_days, n_assets)
    cum = np.concatenate([np.zeros((n_sims, 1, n_assets)), np.cumsum(log_steps, axis=1)], axis=1)
    paths = s0 * np.exp(cum)
    if n_assets == 1:
        return paths[:, :, 0], z[:, :, 0]
    return paths, z


def risk_stats(pnl: np.ndarray, confidence: float) -> dict:
    """Statistiques de risque d'une distribution de gains / pertes (en euros ou en %).

    - VaR(c) : perte qui n'est dépassée que dans (1 - c) des cas ;
    - CVaR(c) : perte moyenne dans ces (1 - c) pires cas (au-delà de la VaR).
    Les pertes sont exprimées en valeurs POSITIVES.
    """
    q = np.quantile(pnl, 1 - confidence)
    tail = pnl[pnl <= q]
    return {
        "esperance": float(pnl.mean()),
        "ecart_type": float(pnl.std(ddof=1)),
        "q05": float(np.quantile(pnl, 0.05)),
        "q25": float(np.quantile(pnl, 0.25)),
        "mediane": float(np.median(pnl)),
        "q75": float(np.quantile(pnl, 0.75)),
        "q95": float(np.quantile(pnl, 0.95)),
        "var": float(-q),
        "cvar": float(-tail.mean()) if len(tail) else float(-q),
        "proba_perte": float((pnl < 0).mean()),
        "proba_gain": float((pnl > 0).mean()),
    }


def analyse_montecarlo(adj_close: pd.Series, cfg: dict, horizon: int, window: int,
                       amount: float, confidence: float, shock: float) -> PillarResult:
    """Simule le cours à l'horizon et mesure le risque d'une position de `amount` euros."""
    params = estimate_params(adj_close, window)
    paths, z = simulate_gbm(params.s0, params.m, params.sigma, horizon, cfg["simulations"], cfg["graine"])
    final = paths[:, -1]
    returns = final / params.s0 - 1
    pnl = amount * returns
    stats = risk_stats(pnl, confidence)
    stats_pct = risk_stats(returns, confidence)

    grid = cfg["grille_proba_gain"]
    quanti = note_from_bounds(stats["proba_gain"], grid["bornes"], grid["plus_haut_mieux"])

    details = pd.DataFrame([
        ("Dernier cours ajusté S0", params.s0),
        ("m : moyenne des log-rendements quotidiens", params.m),
        ("sigma : écart-type des log-rendements quotidiens", params.sigma),
        ("Rendements utilisés", params.n_obs),
        ("Volatilité annualisée", params.sigma_annual),
        ("Rendement annualisé implicite", params.mu_annual),
        ("Horizon (séances)", horizon),
        ("Simulations", cfg["simulations"]),
        ("Graine", cfg["graine"]),
        ("Montant simulé (€)", amount),
        ("Gain espéré (€)", stats["esperance"]),
        ("Écart-type du P&L (€)", stats["ecart_type"]),
        (f"VaR {confidence:.0%} (€)", stats["var"]),
        (f"CVaR {confidence:.0%} (€)", stats["cvar"]),
        ("Quantile 5 % du rendement", stats_pct["q05"]),
        ("Médiane du rendement", stats_pct["mediane"]),
        ("Quantile 95 % du rendement", stats_pct["q95"]),
        ("Probabilité de perte", stats["proba_perte"]),
        ("Probabilité de gain", stats["proba_gain"]),
        (f"Probabilité de baisse > {shock:.0%}", float((returns < -shock).mean())),
    ], columns=["Mesure", "Valeur"])

    # Tirage équivalent à l'horizon (pour l'onglet de vérification exacte)
    z_eq = z.sum(axis=1) / np.sqrt(horizon)

    return PillarResult(
        name="Hasard",
        quanti=quanti,
        details=details,
        extra={"params": params, "paths": paths, "final": final, "returns": returns, "pnl": pnl,
               "stats": stats, "stats_pct": stats_pct, "z_eq": z_eq, "amount": amount,
               "horizon": horizon, "confidence": confidence,
               "proba_choc": float((returns < -shock).mean())},
    )
