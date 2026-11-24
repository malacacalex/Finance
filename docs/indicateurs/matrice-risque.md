# Mesures de risque et matrice de risque

**Code :** `src/invest_model/risk.py` ; règles dans `config/parametres.yaml > risques`

## Mesures quantitatives (onglet *Risques*)
| Mesure | Définition |
|---|---|
| Volatilité 20 j / 60 j / 1 an | Écart-type des log-rendements quotidiens × √252 |
| Bêta | Covariance(action, CAC 40) / variance(CAC 40), sur 1 an de rendements quotidiens |
| Corrélations | Matrice des corrélations des rendements quotidiens avec les pairs (1 an) |
| Drawdown | Plus forte baisse depuis un plus haut (sur 1 an) et écart au plus haut actuel |
| Sharpe / Sortino | (rendement 1 an − taux sans risque) / volatilité (Sortino : volatilité des seules baisses) |
| VaR historique | Quantile 5 % des rendements observés sur 5 séances (2 ans) × montant |
| VaR paramétrique | Hypothèse normale : −(μ·h − 1,645·σ·√h) × montant |
| VaR / CVaR Monte Carlo | Voir [monte-carlo.md](monte-carlo.md) |
| Liquidité | Montant échangé par jour (moyenne sur 20 séances), comparé à la position |

## Matrice de risque (probabilité × impact)
Chaque risque reçoit une **probabilité** et un **impact**, chacun de 1 à 5. On calcule
**criticité = P × I**, qui donne une zone :

| Criticité | 1–4 | 5–9 | 10–15 | 16–25 |
|---|---|---|---|---|
| Zone | Faible | Modéré | Élevé | Critique |

### Risques quantitatifs, notés automatiquement par une règle explicite
| Risque | Probabilité | Impact |
|---|---|---|
| Baisse de plus de 5 % sur l'horizon | P(baisse > 5 %) selon Monte Carlo | CVaR en % |
| Valorisation élevée | PER / médiane du secteur | 3 (fixe) |
| Endettement | Dette nette / EBITDA | 3 (fixe) |
| Cassure du support S1 hebdo | Plus le cours est proche de S1 (en écarts-types hebdo), plus elle est probable | Distance de S1 à S2 |
| Flux d'actualités négatives | Part des nouvelles négatives | 3 (fixe) |
| Événement pendant l'horizon | 5 si publication ou détachement de dividende prévu, sinon 1 | 4 (fixe) |

### Risques qualitatifs, notés par le groupe
Le fichier `config/risques.yaml` contient des propositions pour Air Liquide (énergie, cycle
industriel, change, hydrogène, concurrence, réglementation…). Elles sont recopiées **une fois**
dans l'onglet *Risques* de `data/saisies.xlsx`, où le groupe les ajuste et les justifie.

## Effet sur la décision
Si un risque est **critique**, un signal d'achat devient ATTENDRE. On peut désactiver ce
garde-fou avec `decision.risque_critique_bloque_achat` dans le scénario.
