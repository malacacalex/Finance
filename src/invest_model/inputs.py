"""Classeur de saisie du groupe : data/saisies.xlsx.

Le groupe y saisit tout ce qui n'est pas calculé :
- notes QUALITATIVES (-2..+2, justification obligatoire) des piliers Graphique et Financier ;
- ACTUALITÉS (pré-remplies par la veille, notées et classées par le groupe) ;
- références SECTEUR saisies à la main (remplacent la médiane des pairs) ;
- RISQUES qualitatifs de la matrice de risque ;
- valeurs relevées sur les fiches ABC Bourse (onglet de CONTRÔLE) ;
- PORTEFEUILLE détenu (pour savoir s'il faut acheter, conserver ou vendre).

Le script n'écrase jamais une saisie du groupe : il ajoute seulement les lignes manquantes.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from .watch import _dedup_key

QUALI_COLUMNS = ["Ticker", "Critère", "Note (-2..+2)", "Justification", "Date", "Auteur"]
SHEETS = {
    "Quali_Graphique": QUALI_COLUMNS,
    "Quali_Financier": QUALI_COLUMNS,
    "Actualites": ["ID", "Ticker", "Date", "Titre", "Source", "Domaine", "URL", "Catégorie", "Origine",
                   "Requête", "Statut", "Sens suggéré", "Fiabilité suggérée", "Note (-2..+2)",
                   "Fiabilité (1..3)", "Justification", "Ajoutée le"],
    "Secteur_Override": ["Ticker", "Ratio", "Valeur", "Source", "Date"],
    "Risques": ["Ticker", "Risque", "Catégorie", "Probabilité (1..5)", "Impact (1..5)", "Justification"],
    "Controle_ABC": ["Ticker", "Indicateur", "Valeur ABC Bourse", "Date du relevé", "Commentaire"],
    "Portefeuille": ["Ticker", "Quantité", "Prix de revient"],
}

CRITERIA = {
    "Quali_Graphique": ["Tendance", "Figures chartistes", "Supports et résistances visuels"],
    "Quali_Financier": ["Solidité du modèle économique", "Position sectorielle"],
}

# Indicateurs à relever sur la fiche « Analyse et conseil » d'ABC Bourse
ABC_INDICATORS = [
    "RSI 14 jours", "Cours / MM20", "Cours / MM50", "Cours / MM100", "Bollinger", "MACD / signal",
    "PER société", "PER secteur", "ROE", "Ratio endettement net", "Valorisation / Ebitda",
]

README = [
    "Classeur de saisie du groupe — modèle d'aide à l'investissement",
    "",
    "Quali_Graphique / Quali_Financier : une note de -2 à +2 par critère, JUSTIFICATION OBLIGATOIRE",
    "   (une note sans justification est ignorée par le modèle).",
    "Actualites : lignes ajoutées par `invest veille` avec le statut « à classer ».",
    "   Remplir Note (-2..+2 : signe = sens, valeur = importance), Fiabilité (1..3), Justification,",
    "   puis passer le statut à « classée ». Les colonnes « suggérées » ne sont qu'une aide.",
    "Secteur_Override : ratio (per, peg, rendement, roe, dette_ebitda, marge_op), valeur, source, date.",
    "   Remplace la médiane des pairs calculée avec yfinance.",
    "Risques : probabilité et impact de 1 à 5 (propositions à revoir en groupe).",
    "Controle_ABC : valeurs lues sur la fiche ABC Bourse le JOUR de l'instantané.",
    "   Pour les positions, écrire « au-dessus », « en dessous », « intérieur »...",
    "Portefeuille : quantité détenue (0 si aucune) et prix de revient.",
]

HEADER_FILL = PatternFill("solid", fgColor="1C5CAB")
HEADER_FONT = Font(bold=True, color="FFFFFF")


# ---------------------------------------------------------------------------
# Création / complétion du classeur
# ---------------------------------------------------------------------------

def ensure_workbook(path: Path, tickers: list[str], risks_cfg: dict) -> Path:
    """Crée le classeur s'il n'existe pas, puis ajoute les lignes manquantes par ticker."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        wb = load_workbook(path)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Lisez-moi"
        for i, line in enumerate(README, start=1):
            ws.cell(row=i, column=1, value=line)
        ws["A1"].font = Font(bold=True, size=14)
        ws.column_dimensions["A"].width = 110

    for name, columns in SHEETS.items():
        if name not in wb.sheetnames:
            _create_sheet(wb, name, columns)

    for ticker in tickers:
        for sheet, criteria in CRITERIA.items():
            existing = _existing(wb[sheet], ticker, column=2)
            for crit in criteria:
                if crit not in existing:
                    wb[sheet].append([ticker, crit, None, None, None, None])
        if not _existing(wb["Risques"], ticker, column=2):
            for r in risks_cfg.get(ticker, []):
                wb["Risques"].append([ticker, r["risque"], r["categorie"], r["probabilite"],
                                      r["impact"], r["justification"]])
        existing = _existing(wb["Controle_ABC"], ticker, column=2)
        for ind in ABC_INDICATORS:
            if ind not in existing:
                wb["Controle_ABC"].append([ticker, ind, None, None, None])
        if not _existing(wb["Portefeuille"], ticker, column=1):
            wb["Portefeuille"].append([ticker, 0, None])
    wb.save(path)
    return path


def _create_sheet(wb: Workbook, name: str, columns: list[str]) -> None:
    ws = wb.create_sheet(name)
    ws.append(columns)
    for cell in ws[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "A2"
    for i, col in enumerate(columns, start=1):
        width = 60 if col in ("Justification", "Titre", "Risque", "Requête") else 18
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width

    # Listes déroulantes : notes -2..+2, fiabilité 1..3, probabilité / impact 1..5
    def add_list(header: str, values: str):
        if header in columns:
            letter = ws.cell(row=1, column=columns.index(header) + 1).column_letter
            dv = DataValidation(type="list", formula1=f'"{values}"', allow_blank=True)
            dv.add(f"{letter}2:{letter}5000")
            ws.add_data_validation(dv)

    add_list("Note (-2..+2)", "-2,-1,0,1,2")
    add_list("Fiabilité (1..3)", "1,2,3")
    add_list("Probabilité (1..5)", "1,2,3,4,5")
    add_list("Impact (1..5)", "1,2,3,4,5")
    add_list("Statut", "à classer,classée,écartée")


def _existing(ws, ticker: str, column: int) -> set:
    """Valeurs déjà présentes dans une colonne pour un ticker donné."""
    return {row[column - 1] for row in ws.iter_rows(min_row=2, values_only=True) if row[0] == ticker}


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------

def read_sheet(path: Path, sheet: str) -> pd.DataFrame:
    """Lit un onglet sous forme de DataFrame (en-têtes en première ligne)."""
    if not path.exists():
        return pd.DataFrame(columns=SHEETS.get(sheet, []))
    df = pd.read_excel(path, sheet_name=sheet, dtype=object)
    return df.dropna(how="all")


def read_quali(path: Path, sheet: str, ticker: str) -> tuple[float | None, pd.DataFrame, list[str]]:
    """Note qualitative d'un pilier = moyenne des critères notés ET justifiés."""
    df = read_sheet(path, sheet)
    df = df[df["Ticker"] == ticker].copy()
    warnings = []
    df["note"] = pd.to_numeric(df["Note (-2..+2)"], errors="coerce")
    justified = df["Justification"].astype(str).str.strip().replace({"nan": "", "None": ""}) != ""
    no_justif = df[df["note"].notna() & ~justified]
    for crit in no_justif["Critère"]:
        warnings.append(f"{sheet} : « {crit} » noté SANS justification -> ignoré (GRP-02)")
    valid = df[df["note"].notna() & justified]
    if valid.empty:
        warnings.append(f"{sheet} : aucune note qualitative saisie pour {ticker}")
        return None, df, warnings
    return float(valid["note"].clip(-2, 2).mean()), df, warnings


def read_news(path: Path, ticker: str) -> pd.DataFrame:
    """Actualités d'un ticker, avec des noms de colonnes internes."""
    df = read_sheet(path, "Actualites")
    df = df[df["Ticker"] == ticker]
    if df.get("Statut") is not None:
        df = df[df["Statut"].astype(str) != "écartée"]           # le groupe peut écarter une nouvelle
    return pd.DataFrame({
        "date": pd.to_datetime(df["Date"], errors="coerce"),
        "titre": df["Titre"],
        "source": df["Source"],
        "url": df["URL"],
        "categorie": df["Catégorie"],
        "statut": df["Statut"],
        "sens_suggere": pd.to_numeric(df["Sens suggéré"], errors="coerce"),
        "fiabilite_suggeree": pd.to_numeric(df["Fiabilité suggérée"], errors="coerce"),
        "note": pd.to_numeric(df["Note (-2..+2)"], errors="coerce"),
        "fiabilite": pd.to_numeric(df["Fiabilité (1..3)"], errors="coerce"),
        "justification": df["Justification"],
    }).reset_index(drop=True)


def append_news(path: Path, news: pd.DataFrame) -> int:
    """Ajoute à l'onglet Actualites les nouvelles absentes (dédoublonnage par titre).

    Les lignes existantes (et donc les notes du groupe) ne sont jamais modifiées.
    """
    wb = load_workbook(path)
    ws = wb["Actualites"]
    headers = [c.value for c in ws[1]]
    i_title, i_ticker, i_id = headers.index("Titre"), headers.index("Ticker"), headers.index("ID")
    existing = {(r[i_ticker], _dedup_key(str(r[i_title]))) for r in ws.iter_rows(min_row=2, values_only=True)
                if r[i_title]}
    ids = [r[i_id] for r in ws.iter_rows(min_row=2, values_only=True) if isinstance(r[i_id], int)]
    next_id = max(ids, default=0) + 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    added = 0
    for _, n in news.iterrows():
        key = (n["ticker"], _dedup_key(str(n["titre"])))
        if key in existing:
            continue
        existing.add(key)
        date = n["date"].to_pydatetime() if pd.notna(n["date"]) else None
        ws.append([next_id, n["ticker"], date, n["titre"], n["source"], n["domaine"], n["url"],
                   n["categorie"], n["origine"], n["requete"], "à classer", int(n["sens_suggere"]),
                   int(n["fiabilite_suggeree"]), None, None, None, now])
        next_id += 1
        added += 1
    wb.save(path)
    return added


def read_overrides(path: Path, ticker: str) -> dict:
    """Références secteur saisies : {ratio: (valeur, 'source, date')}."""
    df = read_sheet(path, "Secteur_Override")
    df = df[df["Ticker"] == ticker]
    out = {}
    for _, r in df.iterrows():
        value = pd.to_numeric(r["Valeur"], errors="coerce")
        if pd.notna(value) and isinstance(r["Ratio"], str):
            out[r["Ratio"].strip().lower()] = (float(value), f"{r['Source']} ({r['Date']})")
    return out


def read_risks(path: Path, ticker: str) -> pd.DataFrame:
    df = read_sheet(path, "Risques")
    df = df[df["Ticker"] == ticker]
    return pd.DataFrame({
        "risque": df["Risque"], "categorie": df["Catégorie"],
        "probabilite": pd.to_numeric(df["Probabilité (1..5)"], errors="coerce"),
        "impact": pd.to_numeric(df["Impact (1..5)"], errors="coerce"),
        "justification": df["Justification"],
    })


def read_abc_controls(path: Path, ticker: str) -> pd.DataFrame:
    df = read_sheet(path, "Controle_ABC")
    return df[df["Ticker"] == ticker]


def read_position(path: Path, ticker: str) -> tuple[float, float | None]:
    """Quantité détenue et prix de revient (0, None si rien)."""
    df = read_sheet(path, "Portefeuille")
    df = df[df["Ticker"] == ticker]
    if df.empty:
        return 0.0, None
    qty = pd.to_numeric(df["Quantité"], errors="coerce").fillna(0).iloc[0]
    pru = pd.to_numeric(df["Prix de revient"], errors="coerce").iloc[0]
    return float(qty), (None if pd.isna(pru) else float(pru))
