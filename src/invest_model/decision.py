"""Du score final au signal : ACHETER / ATTENDRE / VENDRE (conception §9.3).

1. Le score final (-2..+2) est comparé aux seuils du scénario :
       score >= achat_fort  -> ACHAT FORT
       score >= achat       -> ACHAT
       score >  vente       -> NEUTRE
       score >  vente_forte -> VENTE
       sinon                -> VENTE FORTE
2. Le signal est traduit en action selon le portefeuille détenu :
   - sans position : ACHETER (achat fort / achat), ATTENDRE (neutre, vente, vente forte) ;
   - avec position : RENFORCER (achat fort), CONSERVER (achat, neutre),
     ALLÉGER (vente), VENDRE (vente forte).
3. Garde-fou risque : un risque CRITIQUE dans la matrice transforme un achat en
   ATTENDRE (paramètre risque_critique_bloque_achat).
4. Niveaux indicatifs à partir des pivots HEBDOMADAIRES de la semaine suivante :
   stop sous S1, objectifs R1 et R2, ratio gain / risque.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Decision:
    signal: str                    # ACHAT FORT, ACHAT, NEUTRE, VENTE, VENTE FORTE
    action: str                    # ACHETER, ATTENDRE, RENFORCER, CONSERVER, ALLÉGER, VENDRE
    score: float | None
    reasons: list[str] = field(default_factory=list)
    levels: dict = field(default_factory=dict)


def signal_from_score(score: float | None, th: dict) -> str:
    if score is None:
        return "INDÉTERMINÉ"
    if score >= th["achat_fort"]:
        return "ACHAT FORT"
    if score >= th["achat"]:
        return "ACHAT"
    if score > th["vente"]:
        return "NEUTRE"
    if score > th["vente_forte"]:
        return "VENTE"
    return "VENTE FORTE"


ACTION_WITHOUT_POSITION = {"ACHAT FORT": "ACHETER", "ACHAT": "ACHETER", "NEUTRE": "ATTENDRE",
                           "VENTE": "ATTENDRE", "VENTE FORTE": "ATTENDRE", "INDÉTERMINÉ": "ATTENDRE"}
ACTION_WITH_POSITION = {"ACHAT FORT": "RENFORCER", "ACHAT": "CONSERVER", "NEUTRE": "CONSERVER",
                        "VENTE": "ALLÉGER", "VENTE FORTE": "VENDRE", "INDÉTERMINÉ": "CONSERVER"}


def decide(score: float | None, thresholds: dict, position_qty: float, risk_matrix: pd.DataFrame,
           close: float, weekly_next: dict, pillar_table: pd.DataFrame) -> Decision:
    signal = signal_from_score(score, thresholds)
    holding = position_qty > 0
    action = (ACTION_WITH_POSITION if holding else ACTION_WITHOUT_POSITION)[signal]
    reasons = []

    # Piliers qui pèsent le plus dans le score (dans un sens ou dans l'autre)
    contrib = pillar_table.dropna(subset=["Contribution"]).sort_values("Contribution", key=abs, ascending=False)
    for _, r in contrib.iterrows():
        sens = "favorable" if r["Contribution"] > 0 else "défavorable" if r["Contribution"] < 0 else "neutre"
        reasons.append(f"{r['Pilier']} : score {r['Score du pilier']:+.2f} ({sens}, {r['Combinaison']})")

    # Garde-fou : risque critique
    critical = risk_matrix[risk_matrix["Zone"] == "Critique"]
    if not critical.empty:
        names = ", ".join(critical["Risque"])
        if thresholds.get("risque_critique_bloque_achat") and action in ("ACHETER", "RENFORCER"):
            action = "ATTENDRE" if not holding else "CONSERVER"
            reasons.insert(0, f"Achat BLOQUÉ par un risque critique : {names}")
        else:
            reasons.insert(0, f"Attention, risque critique : {names}")

    # Niveaux indicatifs (pivots hebdomadaires pour la semaine suivante)
    lv = weekly_next
    levels = {"cours": close, "stop_indicatif": lv["S1"], "stop_large": lv["S2"],
              "objectif_1": lv["R1"], "objectif_2": lv["R2"], "pivot": lv["P"]}
    risk_down = close - lv["S1"]
    gain_up = lv["R1"] - close
    levels["ratio_gain_risque"] = gain_up / risk_down if risk_down > 0 and gain_up > 0 else None
    return Decision(signal=signal, action=action, score=score, reasons=reasons, levels=levels)
