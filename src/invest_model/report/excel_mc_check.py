"""Onglets de vérification de Monte Carlo en FORMULES Excel (GRP-10, conception §8.4).

openpyxl écrit les noms ANGLAIS des fonctions ; Excel en français les affiche :
    RAND -> ALEA        NORMINV -> LOI.NORMALE.INVERSE      EXP -> EXP
    SQRT -> RACINE      AVERAGE -> MOYENNE                  STDEV -> ECARTYPE
    PERCENTILE -> CENTILE   COUNTIF -> NB.SI   AVERAGEIF -> MOYENNE.SI   SUMPRODUCT -> SOMMEPROD

Formule de la valeur finale (équivalente aux 5 pas quotidiens, voir pillars/montecarlo.py) :
    S_T = S0 * EXP(h * m + sigma * RACINE(h) * Z)
"""

from __future__ import annotations

import numpy as np
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.formula import DataTableFormula

BOLD = Font(bold=True)
TITLE = Font(bold=True, size=13)
INPUT_FILL = PatternFill("solid", fgColor="CDE2FB")


def _params_block(ws, result) -> None:
    """Paramètres en B3:B8, réutilisés par toutes les formules (références absolues)."""
    x = result.montecarlo.extra
    p = x["params"]
    rows = [
        ("S0 : dernier cours ajusté", p.s0),
        ("m : moyenne des log-rendements quotidiens", p.m),
        ("sigma : écart-type des log-rendements quotidiens", p.sigma),
        ("h : horizon (séances)", x["horizon"]),
        ("Montant investi (€)", x["amount"]),
        ("Nombre d'actions (= montant / S0)", "=B7/B3"),
        ("Niveau de confiance", x["confidence"]),
    ]
    for i, (label, value) in enumerate(rows, start=3):
        ws.cell(row=i, column=1, value=label)
        cell = ws.cell(row=i, column=2, value=value)
        cell.fill = INPUT_FILL
    ws.column_dimensions["A"].width = 48
    ws.column_dimensions["B"].width = 16


def write_exact_check(wb, result, n_rows: int) -> None:
    """Tirages Z de Python recopiés : Excel doit retrouver EXACTEMENT les mêmes S_T."""
    ws = wb.create_sheet("MC_Verif_Exacte")
    ws["A1"] = "Vérification EXACTE : mêmes tirages que Python, formules Excel"
    ws["A1"].font = TITLE
    _params_block(ws, result)
    x = result.montecarlo.extra
    z, final = x["z_eq"][:n_rows], x["final"][:n_rows]

    head = 12
    headers = ["Simulation", "Z (tirage Python, équivalent horizon)", "S_T formule Excel", "S_T Python",
               "Écart", "P&L formule (€)"]
    for j, h in enumerate(headers, start=1):
        ws.cell(row=head, column=j, value=h).font = BOLD
    for k in range(n_rows):
        r = head + 1 + k
        ws.cell(row=r, column=1, value=k + 1)
        ws.cell(row=r, column=2, value=float(z[k]))
        ws.cell(row=r, column=3, value=f"=$B$3*EXP($B$6*$B$4+$B$5*SQRT($B$6)*B{r})")
        ws.cell(row=r, column=4, value=float(final[k]))
        ws.cell(row=r, column=5, value=f"=C{r}-D{r}")
        ws.cell(row=r, column=6, value=f"=$B$8*(C{r}-$B$3)")
    first, last = head + 1, head + n_rows

    pnl_py = x["amount"] * (final / x["params"].s0 - 1)
    conf = x["confidence"]
    checks = [
        ("Somme des écarts absolus (doit valoir ~0)", f"=SUMPRODUCT(ABS(E{first}:E{last}))", 0.0),
        ("P&L moyen (€)", f"=AVERAGE(F{first}:F{last})", float(pnl_py.mean())),
        (f"VaR {conf:.0%} (€)", f"=-PERCENTILE(F{first}:F{last},1-B9)", float(-np.quantile(pnl_py, 1 - conf))),
    ]
    ws["H3"], ws["I3"], ws["J3"] = "Contrôle", "Excel", "Python (mêmes tirages)"
    for c in ("H3", "I3", "J3"):
        ws[c].font = BOLD
    for i, (label, formula, py) in enumerate(checks, start=4):
        ws.cell(row=i, column=8, value=label)
        ws.cell(row=i, column=9, value=formula)
        ws.cell(row=i, column=10, value=py)
    ws.column_dimensions["H"].width = 42
    for col in "CDEFIJ":
        ws.column_dimensions[col].width = 18


def write_alea_check(wb, result, n_rows: int) -> None:
    """Simulation refaite avec ALEA : accord STATISTIQUE avec Python (tirages différents).

    Deux méthodes côte à côte :
    1. colonnes B:D : une ligne par simulation (une formule ALEA par ligne) ;
    2. colonnes K:L : TABLE DE DONNÉES (Données > Analyse de scénarios > Table de données)
       qui recalcule n fois la cellule G21 (un tirage).
    Appuyer sur F9 relance tous les tirages.
    """
    ws = wb.create_sheet("MC_Verif_ALEA")
    ws["A1"] = "Vérification STATISTIQUE avec ALEA() et LOI.NORMALE.INVERSE() — F9 pour relancer"
    ws["A1"].font = TITLE
    _params_block(ws, result)
    x = result.montecarlo.extra

    head = 12
    for j, h in enumerate(["Simulation", "Z = LOI.NORMALE.INVERSE(ALEA();0;1)", "S_T", "P&L (€)"], start=1):
        ws.cell(row=head, column=j, value=h).font = BOLD
    for k in range(n_rows):
        r = head + 1 + k
        ws.cell(row=r, column=1, value=k + 1)
        ws.cell(row=r, column=2, value="=NORMINV(RAND(),0,1)")
        ws.cell(row=r, column=3, value=f"=$B$3*EXP($B$6*$B$4+$B$5*SQRT($B$6)*B{r})")
        ws.cell(row=r, column=4, value=f"=$B$8*(C{r}-$B$3)")
    first, last = head + 1, head + n_rows
    rng = f"D{first}:D{last}"

    st = x["stats"]
    rows = [
        ("P&L moyen (€)", f"=AVERAGE({rng})", st["esperance"]),
        ("Écart-type du P&L (€)", f"=STDEV({rng})", st["ecart_type"]),
        ("VaR (€)", f"=-PERCENTILE({rng},1-B9)", st["var"]),
        ("CVaR (€)", f'=-AVERAGEIF({rng},"<="&-G6)', st["cvar"]),
        ("Probabilité de perte", f'=COUNTIF({rng},"<0")/COUNT({rng})', st["proba_perte"]),
    ]
    ws["F3"], ws["G3"], ws["H3"], ws["I3"] = "Statistique", "Excel (ALEA)", "Python", "Écart relatif"
    for c in ("F3", "G3", "H3", "I3"):
        ws[c].font = BOLD
    for i, (label, formula, py) in enumerate(rows, start=4):
        ws.cell(row=i, column=6, value=label)
        ws.cell(row=i, column=7, value=formula)
        ws.cell(row=i, column=8, value=py)
        ws.cell(row=i, column=9, value=f"=IF(H{i}=0,\"\",G{i}/H{i}-1)")
    ws["F10"] = (f"Écarts attendus de quelques % : {n_rows} tirages Excel contre "
                 f"{len(x['final'])} en Python, tirages différents.")

    # --- Méthode 2 : table de données -----------------------------------
    ws["F19"] = "Méthode « table de données »"
    ws["F19"].font = BOLD
    ws["F20"] = "Un tirage de P&L (€) :"
    ws["G21"] = "=$B$8*($B$3*EXP($B$6*$B$4+$B$5*SQRT($B$6)*NORMINV(RAND(),0,1))-$B$3)"
    ws["F21"] = "Cellule recalculée par la table ->"
    top = 23
    ws.cell(row=top - 1, column=11, value="n").font = BOLD
    ws.cell(row=top - 1, column=12, value="=G21")         # en-tête de la table : la formule à répéter
    for k in range(n_rows):
        ws.cell(row=top + k, column=11, value=k + 1)
    # TABLE(;M1) : table à une variable en colonne, cellule d'entrée M1 (vide, sans effet).
    ref = f"L{top}:L{top + n_rows - 1}"
    ws.cell(row=top, column=12).value = DataTableFormula(ref=ref, dt2D=False, dtr=False, r1="M1")
    trng = f"L{top}:L{top + n_rows - 1}"
    ws["F23"], ws["G23"] = "P&L moyen (table)", f"=AVERAGE({trng})"
    ws["F24"], ws["G24"] = "VaR (table)", f"=-PERCENTILE({trng},1-B9)"
    ws["F26"] = ("Si la table n'est pas calculée : sélectionner K22:L" + str(top + n_rows - 1)
                 + ", Données > Analyse de scénarios > Table de données, cellule d'entrée en colonne : M1.")
    ws.column_dimensions["F"].width = 34
    for col in "BCDGHIL":
        ws.column_dimensions[col].width = 16
