# Points pivots — supports et résistances

**Leçon ABC Bourse :** [Les Points pivots](https://www.abcbourse.com/apprendre/11_pivots.html)
**Outil ABC :** [Calcul des points pivots](https://www.abcbourse.com/analyses/pivots) (pivots quotidiens, 5 niveaux)
**Code :** `src/invest_model/indicators/pivots.py`

## Calcul (méthode standard)
H, B et C sont le plus haut, le plus bas et la clôture de la période **précédente** :

| Niveau | Formule |
|---|---|
| Pivot P | (H + B + C) / 3 |
| Support S1 | 2P − H |
| Support S2 | P − (H − B) |
| Résistance R1 | 2P − B |
| Résistance R2 | P + (H − B) |

La leçon présente aussi les variantes Camarilla, Fibonacci et Woodie. Elles ne sont pas utilisées
ici.

## Deux périodes
- **Quotidienne**, comme l'outil ABC : on compare la dernière clôture aux pivots de la veille, qui
  étaient en vigueur pendant la séance. Les comparer aux pivots calculés sur la même séance serait
  circulaire.
- **Hebdomadaire**, adaptée à l'horizon d'une semaine : pivots calculés sur la semaine précédente
  complète.

## Note quantitative
Règle de la leçon : on achète quand le cours franchit le pivot à la hausse, on vend quand il le
franchit à la baisse.

| Position du cours | > R1 | entre P et R1 | entre S1 et P | < S1 |
|---|---|---|---|---|
| Note | +2 | +1 | −1 | −2 |

La note retenue est la moyenne des notes quotidienne et hebdomadaire. Les poids se règlent dans
`technique.pivots`.

## Stop et objectifs
Ils se lisent sur les pivots **hebdomadaires** :
- stop indicatif = S1, stop large = S2 ;
- objectifs = R1 et R2 ;
- ratio gain / risque = (R1 − C) / (C − S1).

Si la semaine en cours n'est pas terminée, on utilise les niveaux **en vigueur** : une semaine de
2 séances donnerait des niveaux beaucoup trop serrés. Relancer l'analyse après la clôture du
vendredi donne les niveaux de la semaine suivante.
