# Bandes de Bollinger

**Leçon ABC Bourse :** [Les Bandes de Bollinger](https://www.abcbourse.com/apprendre/11_lecon4.html)
**Code :** `src/invest_model/indicators/bollinger.py`

## Réglage et calcul
La leçon indique que, traditionnellement, la moyenne mobile porte sur 20 séances et que les
bandes sont écartées de ±2 écarts-types.
- Milieu = MM20 (simple).
- Bandes = MM20 ± 2 × écart-type des 20 dernières clôtures. Nous prenons l'écart-type de
  **population** (division par 20), comme dans la définition de Bollinger.
- %B = (C − bande basse) / (bande haute − bande basse) ; largeur = (haute − basse) / milieu.

## Lecture (leçon) et note

| État de la dernière séance | Lecture ABC | Note |
|---|---|---|
| Retour dans les bandes par le bas (clôture sous la bande basse dans les 3 séances précédentes) | Retournement haussier | +2 |
| Clôture au-dessus de la bande haute | Continuation de tendance | +1 |
| À l'intérieur des bandes | — | 0 |
| Clôture sous la bande basse | Continuation baissière | −1 |
| Retour dans les bandes par le haut | Retournement baissier | −2 |

Le **resserrement** des bandes (largeur parmi les 10 % les plus faibles sur 6 mois) est signalé,
sans être noté : selon la leçon, un mouvement important suit souvent un resserrement.
