# Pilier 4 — Hasard : Monte Carlo

**Code :** `src/invest_model/pillars/montecarlo.py`, vérification Excel dans `report/excel_mc_check.py`

## Modèle : mouvement brownien géométrique
Calibrage sur les cours ajustés des dividendes : sur les 252 dernières séances (paramètre
`fenetre_historique_jours`), on calcule les log-rendements quotidiens r(t) = ln(S(t) / S(t−1)),
leur moyenne **m** et leur écart-type **σ**.

Simulation, au pas d'une séance :

  S(t+1) = S(t) × exp(m + σ × ε(t)), avec ε ~ N(0, 1)

Attention : m est déjà la moyenne des **log**-rendements, c'est-à-dire le terme (μ − σ²/2) de la
formule usuelle. On ne retranche donc pas σ²/2 une deuxième fois. Le rendement arithmétique
annualisé implicite vaut (m + σ²/2) × 252.

Pour plusieurs actions, ε = L × Z, où L est la décomposition de Cholesky de la matrice de
corrélation (L × Lᵀ = ρ). Elle est prête pour le portefeuille des 5 actions.

## Sorties
Pour un montant investi `montant_analyse` (hypothèse : 100 000 € = 500 000 € / 5), on obtient la
distribution du gain ou de la perte à l'horizon (5 séances) :
- espérance, écart-type, quantiles ;
- **VaR** : perte dépassée dans seulement 5 % des cas ;
- **CVaR** : perte moyenne dans ces 5 % pires cas ;
- probabilité de perte, probabilité de baisse de plus de 5 %.

**Note quantitative** : probabilité de gain, grille [0,40 ; 0,47 ; 0,53 ; 0,60] → −2..+2.
**Limite** : la dérive m vient de l'historique récent, donc la probabilité de gain prolonge en
partie la tendance passée. On peut réduire le poids du pilier dans le scénario.

## Vérification dans Excel
Après h séances, S(h) = S0 × exp(h·m + σ·Σε) = S0 × exp(h·m + σ·√h·Z), avec Z = Σε / √h ~ N(0, 1).
La valeur finale tient donc en une seule formule :

  `= S0 * EXP(h*m + sigma*RACINE(h)*Z)`

| Onglet | Méthode | Résultat attendu |
|---|---|---|
| `MC_Verif_Exacte` | Z = tirages de Python recopiés ; S_T et P&L recalculés par formules | Écart **nul** avec Python : la formule est juste |
| `MC_Verif_ALEA` | Z = `LOI.NORMALE.INVERSE(ALEA();0;1)` sur 1 000 lignes, et la même chose avec une **table de données** | Accord statistique, à quelques % près (F9 relance les tirages) |

Résultat vérifié le 24/11/2026 sur Air Liquide après recalcul par LibreOffice :
- l'onglet exact donne un écart total de 0 ;
- l'onglet ALEA s'écarte de Python de moins de 3,5 % sur la moyenne, l'écart-type, la VaR, la
  CVaR et la probabilité de perte.

Pour la table de données : LibreOffice ne retire pas ALEA à chaque ligne. Elle doit donc être
contrôlée dans Excel. Si elle ne se calcule pas, il suffit de la recréer : *Données → Analyse de
scénarios → Table de données*, cellule d'entrée en colonne M1. La procédure est écrite dans
l'onglet.
