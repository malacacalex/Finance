"""Classeur de résultats `resultats.xlsx` : un onglet par étape du modèle (conception §10)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .excel_mc_check import write_alea_check, write_exact_check

TITLE = Font(bold=True, size=14)
H2 = Font(bold=True, size=11, color="1C5CAB")
HEADER_FILL = PatternFill("solid", fgColor="1C5CAB")
HEADER_FONT = Font(bold=True, color="FFFFFF")
WARN_FILL = PatternFill("solid", fgColor="FFE3A3")
ZONE_FILL = {"Faible": "B7E4B7", "Modéré": "FDE7A6", "Élevé": "F7C3AD", "Critique": "EE9D9D"}
ACTION_FILL = {"ACHETER": "B7E4B7", "RENFORCER": "B7E4B7", "CONSERVER": "DDE7F3", "ATTENDRE": "FDE7A6",
               "ALLÉGER": "F7C3AD", "VENDRE": "EE9D9D"}

# Libellés à afficher en pourcentage
PCT_HINTS = ("probabilit", "volatilit", "rendement", "quantile", "marge", "roe", "perf", "écart au plus haut",
             "drawdown", "croissance", "potentiel", "gearing", "médiane du rendement")


def _clean(v):
    """Convertit une valeur pour openpyxl (pas de NaN, pas de types numpy, dates naïves)."""
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime().replace(tzinfo=None)
    if hasattr(v, "item"):
        try:
            return v.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(v, (list, dict, tuple)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return v


def write_df(ws, df: pd.DataFrame, row: int, col: int = 1, index: bool = False, title: str | None = None,
             pct_cols: tuple = ()) -> int:
    """Écrit un DataFrame à partir de (row, col). Renvoie la première ligne libre après."""
    if title:
        ws.cell(row=row, column=col, value=title).font = H2
        row += 1
    if df is None or df.empty:
        ws.cell(row=row, column=col, value="(aucune donnée)")
        return row + 2
    frame = df.reset_index() if index else df
    for j, name in enumerate(frame.columns):
        c = ws.cell(row=row, column=col + j, value=str(name))
        c.fill, c.font = HEADER_FILL, HEADER_FONT
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, values in enumerate(frame.itertuples(index=False), start=1):
        label = str(values[0]).lower() if len(values) else ""
        for j, v in enumerate(values):
            cell = ws.cell(row=row + i, column=col + j, value=_clean(v))
            name = str(frame.columns[j])
            if isinstance(cell.value, float):
                if name in pct_cols or (j > 0 and any(h in label for h in PCT_HINTS) and abs(cell.value) < 5):
                    cell.number_format = "0.00%"
                else:
                    cell.number_format = "#,##0.00" if abs(cell.value) >= 1 else "0.0000"
    return row + len(frame) + 2


def _autowidth(ws, minimum: int = 10, maximum: int = 70) -> None:
    widths: dict = {}
    for row in ws.iter_rows():
        for c in row:
            if c.value is not None:
                widths[c.column] = max(widths.get(c.column, 0), len(str(c.value)))
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = max(minimum, min(maximum, w + 2))


def _image(ws, path: Path, anchor: str, width: int | None = None) -> None:
    img = Image(str(path))
    if width:
        ratio = width / img.width
        img.width, img.height = width, int(img.height * ratio)
    ws.add_image(img, anchor)


def _kv(d: dict, labels: dict) -> pd.DataFrame:
    return pd.DataFrame([(labels.get(k, k), v) for k, v in d.items() if k in labels], columns=["Mesure", "Valeur"])


METRIC_LABELS = {
    "vol_20j": "Volatilité annualisée 20 séances", "vol_60j": "Volatilité annualisée 60 séances",
    "vol_1a": "Volatilité annualisée 1 an", "beta": "Bêta vs CAC 40 (1 an)",
    "correlation_indice": "Corrélation avec le CAC 40", "drawdown_max_1a": "Drawdown maximal 1 an",
    "drawdown_actuel": "Drawdown actuel (vs plus haut 1 an)", "rendement_1a": "Rendement 1 an (dividendes inclus)",
    "sharpe_1a": "Ratio de Sharpe 1 an", "sortino_1a": "Ratio de Sortino 1 an",
    "var_historique": "VaR historique horizon (€)", "var_parametrique": "VaR paramétrique normale (€)",
    "var_montecarlo": "VaR Monte Carlo (€)", "cvar_montecarlo": "CVaR Monte Carlo (€)",
    "volume_euros_jour": "Montant échangé par jour, moy. 20 séances (€)",
    "position_vs_volume": "Position / montant échangé par jour",
}
CONTEXT_LABELS = {
    "dernier_cours": "Dernier cours", "perf_1s": "Performance 1 semaine", "perf_1m": "Performance 1 mois",
    "perf_3m": "Performance 3 mois", "perf_6m": "Performance 6 mois", "perf_1a": "Performance 1 an",
    "perf_ytd": "Performance depuis le 1er janvier", "plus_haut_52s": "Plus haut 52 semaines",
    "plus_bas_52s": "Plus bas 52 semaines", "ecart_plus_haut_52s": "Écart au plus haut 52 semaines",
    "volume_moyen_20j": "Volume moyen 20 séances (titres)",
}
PROFILE_KEYS = {
    "longName": "Nom", "sector": "Secteur (Yahoo)", "industry": "Industrie (Yahoo)", "country": "Pays",
    "website": "Site", "fullTimeEmployees": "Effectif", "marketCap": "Capitalisation",
    "enterpriseValue": "Valeur d'entreprise", "sharesOutstanding": "Nombre d'actions", "currency": "Devise",
    "beta": "Bêta (Yahoo, 5 ans)", "forwardPE": "PER prévisionnel", "priceToBook": "Cours / actif net",
    "enterpriseToEbitda": "VE / EBITDA", "enterpriseToRevenue": "VE / CA", "payoutRatio": "Taux de distribution",
    "dividendRate": "Dividende annuel", "exDividendDate": "Dernier détachement (timestamp)",
    "profitMargins": "Marge nette", "grossMargins": "Marge brute", "revenueGrowth": "Croissance du CA (trim.)",
    "earningsGrowth": "Croissance des bénéfices (trim.)", "trailingEps": "BPA 12 mois", "forwardEps": "BPA prévisionnel",
    "longBusinessSummary": "Activité",
}


def write_report(result, path: Path, charts: dict) -> Path:
    wb = Workbook()
    d = result.decision
    s = result.settings

    # ------------------------------------------------------------ Synthèse
    ws = wb.active
    ws.title = "Synthèse"
    ws["A1"] = f"{result.name} ({result.ticker}) — analyse du {result.as_of.date()}"
    ws["A1"].font = TITLE
    row = 2
    if s.uses_unvalidated_hypotheses:
        ws.cell(row=row, column=1, value="⚠ Résultats fondés sur des hypothèses du groupe NON VALIDÉES par le "
                "client (voir onglet Paramètres)").fill = WARN_FILL
        row += 1
    row += 1
    summary = [
        ("Action recommandée", d.action),
        ("Signal", d.signal),
        ("Score final (-2..+2)", d.score),
        ("Dernier cours", d.levels["cours"]),
        ("Quantité détenue (onglet Portefeuille)", result.position[0]),
        (f"Stop indicatif (S1 hebdo, {result.technical.extra.get('niveaux_decision', '')})", d.levels["stop_indicatif"]),
        ("Stop large (S2 hebdo)", d.levels["stop_large"]),
        ("Objectif 1 (R1 hebdo)", d.levels["objectif_1"]),
        ("Objectif 2 (R2 hebdo)", d.levels["objectif_2"]),
        ("Ratio gain / risque (R1 vs S1)", d.levels["ratio_gain_risque"]),
        ("Instantané de données", result.snapshot_date),
    ]
    row = write_df(ws, pd.DataFrame(summary, columns=["Élément", "Valeur"]), row, title="Décision")
    ws.cell(row=row - len(summary) - 1, column=2).fill = PatternFill("solid", fgColor=ACTION_FILL.get(d.action, "FFFFFF"))
    ws.cell(row=row, column=1, value="Pourquoi ?").font = H2
    for r in d.reasons:
        row += 1
        ws.cell(row=row, column=1, value="• " + r)
    row += 2
    row = write_df(ws, result.pillar_table, row, title="Score par pilier")
    a = result.analysts
    cons = [("Objectif moyen", a.get("objectif_moyen")), ("Objectif médian", a.get("objectif_median")),
            ("Objectif haut", a.get("objectif_haut")), ("Objectif bas", a.get("objectif_bas")),
            ("Potentiel vs cours", a.get("potentiel")), ("Nombre d'analystes", a.get("nb_analystes")),
            ("Recommandation moyenne", a.get("recommandation")), ("Répartition", a.get("repartition"))]
    row = write_df(ws, pd.DataFrame(cons, columns=["Consensus des analystes (non noté)", "Valeur"]), row)
    row = write_df(ws, result.risk_matrix.head(6)[["ID", "Risque", "Criticité", "Zone"]], row,
                   title="Principaux risques")
    _autowidth(ws, maximum=90)
    _image(ws, charts["technique"], "E4", width=900)

    # ------------------------------------------------------------ Graphique
    ws = wb.create_sheet("Graphique")
    row = write_df(ws, result.technical.details.drop(columns="cle"), 1, title="Pilier 1 — indicateurs techniques")
    row = write_df(ws, result.quali_tables["Graphique"].drop(columns=["note"], errors="ignore"), row,
                   title=f"Qualitatif (classeur de saisie) — note retenue : {result.technical.quali}")
    pv = result.technical.extra
    piv = pd.DataFrame({"Quotidien en vigueur": pv["pivots_daily"]["en_vigueur"],
                        "Quotidien séance suivante": pv["pivots_daily"]["prochaine"],
                        "Hebdo en vigueur": pv["pivots_weekly"]["en_vigueur"],
                        "Hebdo semaine suivante": pv["pivots_weekly"]["prochaine"]})
    row = write_df(ws, piv, row, index=True, title="Points pivots (méthode standard ABC Bourse)")
    row = write_df(ws, _kv(pv["context"], CONTEXT_LABELS), row, title="Contexte de marché")
    _autowidth(ws, maximum=80)
    _image(ws, charts["performance"], f"A{row + 1}", width=900)

    # ------------------------------------------------------------ Financier
    ws = wb.create_sheet("Financier")
    row = write_df(ws, result.fundamental.details.drop(columns="cle"), 1, title="Pilier 2 — ratios vs secteur",
                   pct_cols=())
    checks = pd.DataFrame(result.fundamental.extra["abc_checks"], columns=["Contrôle ABC Bourse", "Respecté"])
    row = write_df(ws, checks, row)
    row = write_df(ws, result.quali_tables["Financier"].drop(columns=["note"], errors="ignore"), row,
                   title=f"Qualitatif (classeur de saisie) — note retenue : {result.fundamental.quali}")
    row = write_df(ws, result.history, row, index=True, title="Historique financier (exercices annuels)")
    row = write_df(ws, result.dividends, row, index=True, title="Dividende par action (ajusté des attributions)")
    _autowidth(ws, maximum=45)
    _image(ws, charts["ratios"], f"A{row + 1}", width=700)

    # ------------------------------------------------------------ Analystes
    ws = wb.create_sheet("Analystes")
    row = 1
    for key, title in [("recommendations", "Recommandations (nombre d'analystes par mois)"),
                       ("earnings_estimate", "Estimations de BPA"), ("revenue_estimate", "Estimations de CA"),
                       ("eps_trend", "Évolution des estimations de BPA"), ("growth_estimates", "Croissance attendue"),
                       ("major_holders", "Actionnariat"), ("institutional_holders", "Principaux institutionnels")]:
        row = write_df(ws, result.bundle.get(key), row, index=key not in ("recommendations",), title=title)
    _autowidth(ws, maximum=40)

    # ------------------------------------------------------------ Informations
    ws = wb.create_sheet("Informations")
    n = result.news
    row = write_df(ws, n.details, 1, title=f"Pilier 3 — quanti {n.quanti} / quali {n.quali}")
    if n.extra:
        row = write_df(ws, n.extra["by_category"], row, title="Par catégorie")
        cols = ["date", "titre", "source", "categorie", "sens", "sens_origine", "note", "fiabilite", "url"]
        row = write_df(ws, n.extra["news"][[c for c in cols if c in n.extra["news"]]], row,
                       title="Actualités prises en compte (à noter dans data/saisies.xlsx)")
    _autowidth(ws, maximum=90)

    # ------------------------------------------------------------ Monte Carlo + vérifications
    ws = wb.create_sheet("Monte_Carlo")
    row = write_df(ws, result.montecarlo.details, 1, title="Pilier 4 — Monte Carlo (mouvement brownien géométrique)")
    ws.cell(row=row, column=1, value="Vérification : onglets MC_Verif_Exacte (mêmes tirages) et MC_Verif_ALEA (ALEA)")
    _autowidth(ws, maximum=60)
    _image(ws, charts["montecarlo"], "D2", width=900)
    mc_cfg = s.params["monte_carlo"]
    write_exact_check(wb, result, mc_cfg["lignes_verif_exacte"])
    write_alea_check(wb, result, mc_cfg["lignes_verif_alea"])

    # ------------------------------------------------------------ Risques
    ws = wb.create_sheet("Risques")
    row = write_df(ws, _kv(result.metrics, METRIC_LABELS), 1, title="Mesures de risque")
    corr = result.metrics.get("correlations")
    if corr is not None:
        row = write_df(ws, corr.round(2), row, index=True, title="Corrélations des rendements quotidiens (1 an)")
    start = row
    row = write_df(ws, result.risk_matrix, row, title="Matrice de risque (criticité = probabilité × impact)")
    for i in range(len(result.risk_matrix)):
        cell = ws.cell(row=start + 2 + i, column=8)
        cell.fill = PatternFill("solid", fgColor=ZONE_FILL.get(cell.value, "FFFFFF"))
    _autowidth(ws, maximum=70)
    _image(ws, charts["risques"], f"K{start}", width=520)

    # ------------------------------------------------------------ Contrôle ABC, profil, paramètres, journal
    ws = wb.create_sheet("Controle_ABC")
    write_df(ws, result.abc_comparison, 1,
             title="Comparaison avec la fiche ABC Bourse « Analyse et conseil » (valeurs relevées dans saisies.xlsx)")
    _autowidth(ws)

    ws = wb.create_sheet("Profil")
    info = result.bundle.get("info") or {}
    write_df(ws, pd.DataFrame([(lbl, info.get(k)) for k, lbl in PROFILE_KEYS.items()], columns=["Champ", "Valeur"]),
             1, title="Profil de la société (yfinance)")
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 120
    for c in ws["B"]:
        c.alignment = Alignment(wrap_text=True, vertical="top")

    ws = wb.create_sheet("Paramètres")
    rows = [("Scénario", s.scenario_name)]
    rows += [(f"client.{k}", v, s.origins.get(k)) for k, v in s.client.items()]
    rows += [(f"poids.{k}", v, s.origins.get("poids_piliers")) for k, v in s.weights.items()]
    rows += [(f"part_quanti.{k}", v, s.origins.get("part_quanti")) for k, v in s.quanti_share.items()]
    rows += [(f"decision.{k}", v, "scénario") for k, v in s.decision.items()]
    rows += [("parametres.yaml", json.dumps(s.params, ensure_ascii=False), "groupe")]
    rows += [("meta instantané", json.dumps(result.bundle.get("meta"), ensure_ascii=False), "")]
    write_df(ws, pd.DataFrame(rows, columns=["Paramètre", "Valeur", "Origine"]), 1, title="Configuration utilisée")
    _autowidth(ws, maximum=100)

    ws = wb.create_sheet("Journal")
    write_df(ws, pd.DataFrame({"Avertissement": result.warnings}), 1, title="Journal (données manquantes, hypothèses)")
    ws.column_dimensions["A"].width = 150

    ws = wb.create_sheet("Cours")
    e = result.technical.extra
    frame = result.bundle["prices"][["Open", "High", "Low", "Close", "Volume"]].copy()
    for n_, s_ in e["mas"].items():
        frame[f"MM{n_}"] = s_
    frame["RSI14"] = e["rsi"]
    frame = frame.join(e["macd"]).join(e["bands"][["upper", "lower"]])
    frame.index = frame.index.date
    write_df(ws, frame.iloc[-260:].round(4), 1, index=True, title="Cours et indicateurs (260 dernières séances)")

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
