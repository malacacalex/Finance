# MACD et ligne de signal

**Leçon ABC Bourse :** [La MACD](https://www.abcbourse.com/apprendre/11_lecon3.html)
**Code :** `src/invest_model/indicators/macd.py`

## Réglage et calcul
- MACD = EMA(12) − EMA(26), sur les clôtures ; la leçon précise qu'on emploie couramment les
  périodes de 12 et 26 jours.
- Ligne de signal = EMA(9) de la MACD.
- Histogramme = MACD − signal.
- EMA(n) : EMA(t) = a·C(t) + (1 − a)·EMA(t−1), avec a = 2 / (n + 1).

## Lecture (leçon)
- La MACD croise sa ligne de signal à la hausse : signal d'achat. À la baisse : signal de vente.
- **Règle de validation** : un croisement n'est valable que si la MACD et le signal étaient du même
  côté depuis au moins 14 séances. Ce nombre est paramétrable (`seances_validation`).

## Note quantitative

| Situation | Note |
|---|---|
| Croisement haussier **validé** il y a 5 séances ou moins (`croisement_recent`) | +2 |
| MACD au-dessus du signal | +1 |
| MACD sous le signal | −1 |
| Croisement baissier validé il y a 5 séances ou moins | −2 |

Le rapport affiche la date du dernier croisement, sa durée de validation et son statut.
