# RSI — Relative Strength Index

**Leçon ABC Bourse :** [Le RSI](https://www.abcbourse.com/apprendre/11_lecon7_1.html)
**Code :** `src/invest_model/indicators/rsi.py`, notation dans `pillars/technical.py`

## Réglage
14 séances : c'est la période d'origine de Wilder et celle des fiches *Analyse et conseil*
(« RSI 14 jours »). La leçon signale que certains analystes utilisent 9 ou 25.

## Calcul (lissage de Wilder)
1. Variation quotidienne : d(t) = C(t) − C(t−1).
2. Hausse(t) = max(d, 0) ; Baisse(t) = max(−d, 0).
3. Première moyenne : moyenne simple des 14 premières hausses (respectivement baisses).
4. Ensuite : moy(t) = (moy(t−1) × 13 + valeur(t)) / 14.
5. RS = moyenne des hausses / moyenne des baisses ; **RSI = 100 − 100 / (1 + RS)**.

La leçon ABC donne la formule sous forme d'image. Nous utilisons la définition de Wilder, qui est
la référence, et nous comparons notre valeur à celle de la fiche (onglet *Controle_ABC*).

## Lecture (leçon)
- RSI au-dessus de 70 : surachat, risque de sommet.
- RSI en dessous de 30 : survente.
- Signaux complémentaires, non automatisés ici (lecture qualitative) : divergences avec le cours,
  figures sur le RSI.

## Note quantitative (−2..+2) — `parametres.yaml > technique.rsi.grille`

| RSI | < 30 | 30–40 | 40–60 | 60–70 | ≥ 70 |
|---|---|---|---|---|---|
| Note | +2 | +1 | 0 | −1 | −2 |

Les seuils 30 et 70 viennent de la leçon. Les bornes intermédiaires 40 et 60 sont un choix du
groupe.
