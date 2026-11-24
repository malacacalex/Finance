# Ratios financiers (pilier 2)

**Code :** `src/invest_model/pillars/fundamental.py`

| Ratio | Définition | Source |
|---|---|---|
| PER | Cours / BPA des 12 derniers mois | ABC [Leçon 9 — PER et PEG](https://www.abcbourse.com/apprendre/12_lecon_af_9_partie2.html) |
| PEG | PER / taux de croissance attendu des bénéfices (en %) | Même leçon : PEG < 1, valeur sous-évaluée |
| Rendement du dividende | Dividendes versés sur 12 mois / cours | ABC [Les dividendes](https://www.abcbourse.com/apprendre/1_les_dividendes1.html), [Leçon 9 partie 3](https://www.abcbourse.com/apprendre/12_lecon_af_9_partie3.html) |
| ROE | Résultat net / capitaux propres | **Absent des leçons ABC** : définition standard. Les fiches ABC affichent le critère « ROE > 10 % » |
| Dette nette / EBITDA | (Dettes financières − trésorerie) / EBITDA | **Absent des leçons ABC** : définition standard |
| Marge opérationnelle | Résultat opérationnel / chiffre d'affaires | **Absent des leçons ABC** : définition standard. Les fiches affichent la « marge opérationnelle courante » |

Les fiches ABC affichent aussi le **ratio d'endettement net** (dette nette / capitaux propres) et
la **valorisation / EBITDA**. Nous les calculons, pour pouvoir comparer, dans l'onglet
*Controle_ABC*.

## Référence secteur
La référence est la **médiane** des pairs définis dans `config/univers.yaml`. Pour Air Liquide :
Linde, Air Products et Nippon Sanso. La médiane résiste mieux aux valeurs extrêmes, comme le PER
d'Air Products gonflé par des charges exceptionnelles. Un ratio est sans unité : les écarts de
devise ne posent pas de problème. Le groupe peut remplacer la médiane par une valeur sourcée
(onglet *Secteur_Override*, par exemple le « PER secteur » de la fiche ABC).

## Note quantitative
Relatif = valeur de la société / médiane du secteur. Bornes [0,80 ; 0,95 ; 1,05 ; 1,20] :

| Relatif | < 0,80 | 0,80–0,95 | 0,95–1,05 | 1,05–1,20 | ≥ 1,20 |
|---|---|---|---|---|---|
| PER, PEG, dette / EBITDA (plus bas = mieux) | +2 | +1 | 0 | −1 | −2 |
| Rendement, ROE, marge (plus haut = mieux) | −2 | −1 | 0 | +1 | +2 |

Cas particuliers : une dette nette négative (trésorerie nette) vaut +2 ; un PER négatif (pertes)
n'est pas noté.

## Provenance
yfinance ne fournit pas toujours le PEG des valeurs européennes. Dans ce cas, il est calculé à
partir de la croissance du BPA attendue à +1 an par le consensus. La colonne *Provenance* indique
pour chaque ratio : `yfinance`, `calculé` ou `saisi`.

## Informations complémentaires (non notées)
- Historique sur 4 exercices : CA, EBITDA, résultat, flux de trésorerie disponible, dette nette,
  marges, ROE, gearing.
- Dividende par action.
- Consensus des analystes : objectifs de cours et répartition des recommandations.
- Estimations de BPA et de CA, actionnariat.
