# Modèle d'aide à l'investissement — 4 piliers

Projet de cours de finance (école d'ingénieur). Le modèle analyse une action selon quatre piliers :
**Graphique** (analyse technique), **Financier** (ratios comparés au secteur), **Informations**
(actualités) et **Hasard** (Monte Carlo). Il en déduit un score de −2 à +2, une décision
(ACHETER, ATTENDRE, CONSERVER, ALLÉGER, VENDRE…) et une matrice de risque.

Documents de référence :
- [Cahier des charges](docs/cahier-des-charges.md) (besoins du client, questions au professeur) ;
- [Conception](docs/conception.md) (architecture et choix justifiés) ;
- [Fiches des indicateurs](docs/indicateurs/), chacune avec la leçon ABC Bourse correspondante.

## Installation

```bash
python -m pip install -e ".[dev]"     # Python 3.10 ou plus
```

## Utilisation

```bash
invest analyse AI.PA                  # télécharge les données, lance la veille, analyse, produit le rapport
invest analyse AI.PA --hors-ligne     # rejoue le dernier instantané, sans réseau
invest analyse AI.PA --snapshot 2026-11-24
invest analyse AI.PA --sans-veille    # sans la recherche d'actualités
invest veille AI.PA                   # veille d'actualités seule (dorking Google News)
invest saisies                        # crée ou complète data/saisies.xlsx pour les 5 actions
```

Sans installer le paquet, on peut aussi lancer `python -m invest_model analyse AI.PA`.

Chaque analyse produit un dossier `outputs/<TICKER>_<date>_<heure>/` qui contient :
- `resultats.xlsx` : décision, scores, détail de chaque pilier, consensus des analystes, Monte Carlo
  et sa vérification en formules Excel, risques, contrôle ABC Bourse, paramètres, journal ;
- `rapport.md` : synthèse lisible, également affichée dans le terminal ;
- `graphiques/` : cours et indicateurs, Monte Carlo, matrice de risque, ratios, performance.

## Déroulé d'une analyse

1. `invest analyse AI.PA` : les données sont figées dans `data/snapshots/<date>/AI.PA/` et les
   actualités trouvées s'ajoutent à `data/saisies.xlsx` avec le statut « à classer ».
2. Le groupe complète `data/saisies.xlsx` :
   - **Quali_Graphique** et **Quali_Financier** : une note de −2 à +2 par critère, avec une
     justification obligatoire ;
   - **Actualites** : une note de −2 à +2 (le signe donne le sens, la valeur l'importance), une
     fiabilité de 1 à 3 et une justification. Le statut passe à « classée », ou à « écartée » si
     la nouvelle est hors sujet ;
   - **Risques** : revoir les probabilités et impacts proposés ;
   - **Controle_ABC** : recopier les valeurs de la fiche ABC Bourse *Analyse et conseil* du jour ;
   - **Portefeuille** : la quantité détenue (elle change la décision : ACHETER ou CONSERVER).
3. `invest analyse AI.PA --hors-ligne` recalcule avec les saisies, sur les mêmes données.

## Configuration (rien n'est codé en dur)

| Fichier | Contenu | Qui le modifie |
|---|---|---|
| `config/parametres.yaml` | Réglages ABC Bourse, grilles de notation, Monte Carlo, règles de la matrice de risque | Le groupe |
| `config/scenarios/hypotheses_groupe.yaml` | Poids, seuils de décision, hypothèses provisoires (horizon, montant…) | Le groupe, en attendant le client |
| `config/client.yaml` | Réponses du professeur (toutes `null` au départ). Elles l'emportent sur le scénario | Le groupe, sur réponse du client |
| `config/univers.yaml` | Actions, pairs sectoriels, mots-clés de veille | Le groupe |
| `config/veille.yaml` | Requêtes de dorking, fiabilité des sources, lexique | Le groupe |
| `config/risques.yaml` | Risques qualitatifs proposés (copiés une fois dans le classeur) | Le groupe |

## Tests

```bash
python -m pytest
```

Les tests vérifient les indicateurs sur des valeurs calculées à la main (RSI, EMA, Bollinger,
pivots, règle des 14 séances de la MACD), les grilles, Monte Carlo (reproductibilité, formule
utilisée dans Excel, corrélations), la combinaison des scores, la décision et la veille.

## Limites à connaître

- **yfinance** est une API non officielle et gratuite : certains champs peuvent manquer. Chaque
  manque est signalé dans l'onglet *Journal*, et chaque ratio indique sa provenance.
- Le **sens suggéré** d'une actualité vient d'un simple lexique : c'est une aide au tri, pas une
  note. Seules les catégories qui concernent directement la société comptent tant que le groupe
  n'a pas noté.
- Dans **Monte Carlo**, la dérive est estimée sur l'historique récent : après une forte hausse,
  la probabilité de gain reflète en partie la tendance passée.
- Le modèle est une **aide à la décision** pour un projet de cours, pas un conseil en
  investissement.
