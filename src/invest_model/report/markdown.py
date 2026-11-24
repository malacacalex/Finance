"""Synthèse lisible (Markdown) : affichée dans le terminal et enregistrée en rapport.md."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..grids import is_missing


def _f(x, fmt="{:.2f}", none="—"):
    return none if is_missing(x) else fmt.format(x)


def _eur(x):
    """1234567.8 -> '1 234 568' (séparateur de milliers français)."""
    return "—" if is_missing(x) else f"{x:,.0f}".replace(",", "\u202f")


def _pct(x):
    return _f(x, "{:+.1%}") if not is_missing(x) else "—"


def build_markdown(result, charts: dict | None = None) -> str:
    d, a, m = result.decision, result.analysts, result.metrics
    ctx = result.technical.extra["context"]
    mc = result.montecarlo.extra
    conf = mc["confidence"]
    L = []
    L.append(f"# {result.name} ({result.ticker}) — analyse du {result.as_of.date()}")
    if result.settings.uses_unvalidated_hypotheses:
        L.append("\n> ⚠ Résultats fondés sur des **hypothèses du groupe non validées par le client** "
                 "(config/scenarios/hypotheses_groupe.yaml).")
    L.append(f"\n## Décision : **{d.action}**  (signal {d.signal}, score {_f(d.score, '{:+.2f}')} sur [-2 ; +2])\n")
    for r in d.reasons:
        L.append(f"- {r}")
    lv = d.levels
    L.append(f"\nNiveaux = pivots hebdomadaires ({result.technical.extra.get('niveaux_decision', '')}).")
    L.append(f"\n| Cours | Stop indicatif (S1 hebdo) | Stop large (S2) | Objectif 1 (R1) | Objectif 2 (R2) | Gain / risque |")
    L.append("|---|---|---|---|---|---|")
    L.append(f"| {_f(lv['cours'])} | {_f(lv['stop_indicatif'])} | {_f(lv['stop_large'])} | {_f(lv['objectif_1'])} "
             f"| {_f(lv['objectif_2'])} | {_f(lv['ratio_gain_risque'])} |")

    L.append("\n## Score par pilier\n")
    L.append("| Pilier | Quanti | Quali | Score | Poids | Combinaison |")
    L.append("|---|---|---|---|---|---|")
    for _, r in result.pillar_table.iterrows():
        L.append(f"| {r['Pilier']} | {_f(r['Quantitatif'], '{:+.2f}')} | {_f(r['Qualitatif'], '{:+.2f}')} | "
                 f"{_f(r['Score du pilier'], '{:+.2f}')} | {r['Poids']:g} | {r['Combinaison']} |")

    L.append("\n## 1. Graphique\n")
    L.append("| Indicateur | Valeur | Note | Lecture |")
    L.append("|---|---|---|---|")
    for _, r in result.technical.details.iterrows():
        L.append(f"| {r['Indicateur']} | {r['Valeur']} | {_f(r['Note'], '{:+g}')} | {r['Lecture']} |")
    L.append(f"\nPerformances : 1 sem. {_pct(ctx['perf_1s'])}, 1 mois {_pct(ctx['perf_1m'])}, "
             f"3 mois {_pct(ctx['perf_3m'])}, 1 an {_pct(ctx['perf_1a'])}, depuis janvier {_pct(ctx['perf_ytd'])}. "
             f"Plus haut 52 sem. {_f(ctx['plus_haut_52s'])} ({_pct(ctx['ecart_plus_haut_52s'])}), "
             f"plus bas {_f(ctx['plus_bas_52s'])}.")

    L.append("\n## 2. Financier (vs médiane des pairs)\n")
    L.append("| Ratio | Société | Secteur | Relatif | Note | Provenance |")
    L.append("|---|---|---|---|---|---|")
    pct_keys = {"rendement", "roe", "marge_op"}
    for _, r in result.fundamental.details.iterrows():
        fmt = "{:.2%}" if r["cle"] in pct_keys else "{:.2f}"
        L.append(f"| {r['Ratio']} | {_f(r['Société'], fmt)} | {_f(r['Secteur'], fmt)} | "
                 f"{_f(r['Relatif (société / secteur)'])} | {_f(r['Note'], '{:+g}')} | {r['Provenance']} |")
    for label, ok in result.fundamental.extra["abc_checks"]:
        L.append(f"- Contrôle {label} : {'oui' if ok else 'non'}")
    L.append(f"\nConsensus ({a.get('nb_analystes') or '?'} analystes, non noté) : objectif moyen "
             f"{_f(a.get('objectif_moyen'))} (potentiel {_pct(a.get('potentiel'))}), fourchette "
             f"{_f(a.get('objectif_bas'))} – {_f(a.get('objectif_haut'))} ; recommandation « {a.get('recommandation')} » ; "
             f"répartition {a.get('repartition')}.")

    n = result.news
    L.append("\n## 3. Informations\n")
    if n.extra:
        L.append(f"Solde net {n.extra['net']:+.2f} -> quanti {_f(n.quanti, '{:+g}')} ; quali {_f(n.quali, '{:+.2f}')}.\n")
        top = n.extra["news"].head(12)
        L.append("| Date | Catégorie | Sens | Origine du sens | Titre | Source |")
        L.append("|---|---|---|---|---|---|")
        for _, r in top.iterrows():
            date = r["date"].date() if pd.notna(r["date"]) else ""
            title = str(r["titre"]).replace("|", "/")[:110]
            L.append(f"| {date} | {r['categorie']} | {int(r['sens']):+d} | {r['sens_origine']} | {title} | {r['source']} |")
    else:
        L.append("Aucune actualité.")

    n_sims = _eur(len(mc["final"]))
    L.append(f"\n## 4. Hasard — Monte Carlo ({n_sims} simulations, {mc['horizon']} séances)\n")
    st, sp = mc["stats"], mc["stats_pct"]
    L.append(f"Sur {_eur(mc['amount'])} € investis : gain espéré {st['esperance']:+.0f} €, "
             f"VaR {conf:.0%} {_eur(st['var'])} €, CVaR {_eur(st['cvar'])} €, "
             f"probabilité de perte {st['proba_perte']:.0%}. Rendement à l'horizon : 5 % des cas < {sp['q05']:+.1%}, "
             f"médiane {sp['mediane']:+.1%}, 5 % des cas > {sp['q95']:+.1%}.")
    p = mc["params"]
    L.append(f"\nCalibrage sur {p.n_obs} séances : volatilité annualisée {p.sigma_annual:.1%}, "
             f"rendement annualisé implicite {p.mu_annual:+.1%}. Attention : la dérive est tirée de "
             f"l'historique récent ; la probabilité de gain reflète donc en partie la tendance passée.")

    L.append("\n## Risques\n")
    L.append(f"Volatilité 1 an {_f(m.get('vol_1a'), '{:.1%}')}, bêta CAC 40 {_f(m.get('beta'))}, "
             f"drawdown max 1 an {_f(m.get('drawdown_max_1a'), '{:.1%}')}, Sharpe 1 an {_f(m.get('sharpe_1a'))}, "
             f"VaR historique {_eur(m.get('var_historique'))} € / paramétrique "
             f"{_eur(m.get('var_parametrique'))} € / Monte Carlo {_eur(m.get('var_montecarlo'))} €.")
    L.append("\n| ID | Risque | Type | P | I | Criticité | Zone |")
    L.append("|---|---|---|---|---|---|---|")
    for _, r in result.risk_matrix.iterrows():
        L.append(f"| {r['ID']} | {r['Risque']} | {r['Type']} | {r['Probabilité']} | {r['Impact']} | "
                 f"{r['Criticité']} | {r['Zone']} |")

    if charts:
        L.append("\n## Graphiques\n")
        for key, p in charts.items():
            L.append(f"![{key}](graphiques/{Path(p).name})")

    if result.warnings:
        L.append("\n## Journal\n")
        for w in result.warnings:
            L.append(f"- {w}")
    return "\n".join(L) + "\n"
