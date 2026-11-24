# Moyennes mobiles 20 / 50 / 100

**Leçon ABC Bourse :** [Les moyennes mobiles](https://www.abcbourse.com/apprendre/11_lecon2.html)
**Réglages :** ceux de la fiche *Analyse et conseil* (MM 20, 50 et 100 jours)
**Code :** `src/invest_model/indicators/moving_averages.py`

## Calcul
Moyenne mobile **simple** : MM(n) = somme des n dernières clôtures / n. La leçon conseille de
commencer par les moyennes simples.

## Lecture (leçon)
- Le cours au-dessus de ses moyennes mobiles indique une tendance haussière.
- Une MM courte qui croise une MM longue à la hausse marque le début d'une tendance haussière.
  La pente du croisement donne sa force.

## Note quantitative

| Moyennes mobiles sous le cours | 3 | 2 | 1 | 0 |
|---|---|---|---|---|
| Note | +2 | +1 | −1 | −2 |

Un croisement MM20/MM50 dans les 20 dernières séances est signalé dans la colonne *Lecture*,
sans être noté.
