"""Graphiques PNG (matplotlib), insérés dans le rapport Excel et la synthèse Markdown."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")            # pas d'affichage à l'écran : on écrit des fichiers
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# Palette (ordre catégoriel fixe) et encres
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
STATUS = {"Faible": "#0ca30c", "Modéré": "#fab219", "Élevé": "#ec835a", "Critique": "#d03b3b"}
BAND_FILL = "#cde2fb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK, "axes.titleweight": "bold",
    "axes.titlesize": 11, "axes.titlelocation": "left", "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": MUTED, "ytick.color": MUTED, "font.size": 9, "legend.frameon": False,
    "lines.linewidth": 1.6, "legend.fontsize": 8,
})


def technical_chart(result, path: Path, sessions: int = 190) -> Path:
    """Cours + MM + Bollinger + pivots hebdo ; RSI ; MACD (3 panneaux, même axe des dates)."""
    e = result.technical.extra
    close = e["close"].iloc[-sessions:]
    idx = close.index
    fig, axes = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1, 1.2]})

    ax = axes[0]
    bands = e["bands"].loc[idx]
    ax.fill_between(idx, bands["lower"], bands["upper"], color=BAND_FILL, alpha=0.6, lw=0,
                    label="Bandes de Bollinger (20, 2)")
    ax.plot(idx, close, color=SERIES[0], lw=2, label="Cours de clôture")
    for (n, s), color in zip(e["mas"].items(), SERIES[1:4]):
        ax.plot(idx, s.loc[idx], color=color, lw=1.4, label=f"MM{n}")
    # Niveaux utilisés pour la décision (pivots hebdo de la semaine suivante, ou en vigueur)
    dl = result.decision.levels
    lv = {"S2": dl["stop_large"], "S1": dl["stop_indicatif"], "P": dl["pivot"], "R1": dl["objectif_1"],
          "R2": dl["objectif_2"]}
    for name in ["S2", "S1", "P", "R1", "R2"]:
        ax.axhline(lv[name], color=MUTED, lw=0.8, ls="--")
        ax.annotate(f"{name} {lv[name]:.2f}", (idx[-1], lv[name]), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7.5, color=INK2, annotation_clip=False)
    ax.set_title(f"{result.name} ({result.ticker}) — cours, moyennes mobiles, Bollinger, pivots hebdo "
                 f"({e.get('niveaux_decision', '')})")
    ax.legend(loc="upper left", ncol=3)

    ax = axes[1]
    rsi = e["rsi"].loc[idx]
    ax.plot(idx, rsi, color=SERIES[0])
    for level in (30, 70):
        ax.axhline(level, color=MUTED, lw=0.8, ls="--")
    ax.set_ylim(0, 100)
    ax.set_title(f"RSI 14 jours : {rsi.iloc[-1]:.1f}")

    ax = axes[2]
    m = e["macd"].loc[idx]
    colors = np.where(m["hist"] >= 0, SERIES[0], SERIES[7])
    ax.bar(idx, m["hist"], color=colors, width=1.0, alpha=0.45, label="Histogramme")
    ax.plot(idx, m["macd"], color=SERIES[0], label="MACD")
    ax.plot(idx, m["signal"], color=SERIES[1], label="Signal (9)")
    ax.axhline(0, color=AXIS, lw=0.8)
    ax.set_title("MACD (12, 26) et ligne de signal")
    ax.legend(loc="upper left", ncol=3)

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def montecarlo_chart(result, path: Path, n_paths: int = 150) -> Path:
    """Éventail des trajectoires simulées + histogramme du rendement à l'horizon."""
    x = result.montecarlo.extra
    paths, returns = x["paths"], x["returns"]
    days = np.arange(paths.shape[1])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    for p in paths[:n_paths]:
        ax1.plot(days, p, color=SERIES[0], alpha=0.06, lw=0.8)
    q = np.quantile(paths, [0.05, 0.25, 0.5, 0.75, 0.95], axis=0)
    ax1.fill_between(days, q[0], q[4], color=BAND_FILL, alpha=0.5, lw=0, label="5 % – 95 %")
    ax1.fill_between(days, q[1], q[3], color=SERIES[0], alpha=0.25, lw=0, label="25 % – 75 %")
    ax1.plot(days, q[2], color=SERIES[0], lw=2, label="Médiane")
    ax1.set_xlabel("Séances")
    ax1.set_title("Trajectoires simulées (mouvement brownien géométrique)")
    ax1.legend(loc="upper left")

    conf = x["confidence"]
    ax2.hist(returns * 100, bins=60, color=SERIES[0], alpha=0.8, edgecolor=SURFACE, linewidth=0.4)
    var_pct = -np.quantile(returns, 1 - conf) * 100
    ax2.axvline(-var_pct, color=STATUS["Critique"], lw=1.5)
    ax2.annotate(f"VaR {conf:.0%} : -{var_pct:.1f} %", (-var_pct, ax2.get_ylim()[1] * 0.9),
                 xytext=(-6, 0), textcoords="offset points", ha="right", color=INK, fontsize=8)
    ax2.axvline(0, color=AXIS, lw=0.8)
    ax2.set_xlabel(f"Rendement à {x['horizon']} séances (%)")
    ax2.set_title(f"Distribution ({len(returns):,} simulations)".replace(",", " "))
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def risk_matrix_chart(result, path: Path) -> Path:
    """Matrice 5 x 5 probabilité x impact, couleurs par zone, risques placés par ID."""
    zones = result.settings.params["risques"]["zones"]
    fig, ax = plt.subplots(figsize=(7.2, 6))
    for p in range(1, 6):
        for i in range(1, 6):
            c = p * i
            z = "Faible" if c <= zones["faible"] else "Modéré" if c <= zones["modere"] else \
                "Élevé" if c <= zones["eleve"] else "Critique"
            ax.add_patch(plt.Rectangle((i - 0.5, p - 0.5), 1, 1, color=STATUS[z], alpha=0.35, lw=2,
                                       ec=SURFACE))
    cells: dict = {}
    for _, r in result.risk_matrix.iterrows():
        cells.setdefault((r["Impact"], r["Probabilité"]), []).append(r["ID"])
    for (i, p), ids in cells.items():
        ax.text(i, p, "\n".join(", ".join(ids[k:k + 3]) for k in range(0, len(ids), 3)),
                ha="center", va="center", fontsize=8.5, color=INK, weight="bold")
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.set_xlabel("Impact (1 = très faible … 5 = très fort)")
    ax.set_ylabel("Probabilité (1 … 5)")
    ax.grid(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=STATUS[z], alpha=0.5) for z in STATUS]
    ax.legend(handles, [f"{z}" for z in STATUS], loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4)
    ax.set_title("Matrice de risque (criticité = probabilité × impact)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def ratios_chart(result, path: Path) -> Path:
    """Ratio société / médiane du secteur (1 = dans la moyenne du secteur)."""
    d = result.fundamental.details.dropna(subset=["Relatif (société / secteur)"])
    fig, ax = plt.subplots(figsize=(8, 3.8))
    y = np.arange(len(d))
    ax.barh(y, d["Relatif (société / secteur)"], color=SERIES[0], height=0.55)
    ax.axvline(1, color=INK2, lw=1)
    ax.set_yticks(y, d["Ratio"])
    ax.invert_yaxis()
    for yi, (v, n) in enumerate(zip(d["Relatif (société / secteur)"], d["Note"])):
        note = "—" if pd.isna(n) else f"{int(n):+d}"
        ax.annotate(f"{v:.2f}  (note {note})", (v, yi), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK)
    ax.set_xlabel("Société / médiane des pairs (1 = égal au secteur)")
    ax.set_title("Ratios financiers comparés au secteur")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(2.0, d["Relatif (société / secteur)"].max() * 1.35))
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def performance_chart(result, path: Path, sessions: int = 252) -> Path:
    """Performance base 100 sur 1 an : société, CAC 40 et pairs (devises locales)."""
    b = result.bundle
    series = {result.name: b["prices"]["Close"]}
    if b.get("benchmark") is not None:
        series["CAC 40"] = b["benchmark"]["Close"]
    if b.get("peer_prices") is not None:
        for col in b["peer_prices"].columns:
            series[col] = b["peer_prices"][col]
    frame = pd.DataFrame(series).ffill().iloc[-sessions:].dropna(axis=1, how="all")
    frame = frame / frame.bfill().iloc[0] * 100
    fig, ax = plt.subplots(figsize=(11, 4))
    for (name, s), color in zip(frame.items(), SERIES):
        ax.plot(s.index, s, color=color, lw=2.2 if name == result.name else 1.3, label=name)
        ax.annotate(f"{s.dropna().iloc[-1]:.0f}", (s.dropna().index[-1], s.dropna().iloc[-1]),
                    xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=INK2)
    ax.axhline(100, color=AXIS, lw=0.8)
    ax.set_title("Performance sur 1 an, base 100 (devises locales)")
    ax.legend(loc="upper left", ncol=len(frame.columns))
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def all_charts(result, folder: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    return {
        "technique": technical_chart(result, folder / "technique.png"),
        "montecarlo": montecarlo_chart(result, folder / "montecarlo.png"),
        "risques": risk_matrix_chart(result, folder / "matrice_risque.png"),
        "ratios": ratios_chart(result, folder / "ratios_secteur.png"),
        "performance": performance_chart(result, folder / "performance.png"),
    }
