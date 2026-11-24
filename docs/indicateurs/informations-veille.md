# Pilier 3 — Informations et veille par dorking

**Code :** `src/invest_model/watch.py` (collecte), `src/invest_model/pillars/news.py` (notation)

## Collecte (`invest veille` ou automatiquement avec `invest analyse`)
- **Google News RSS**, gratuit et sans clé. Il accepte les opérateurs de dorking : `"expression"`,
  `OR`, `-exclure`, `site:`, `intitle:`, `when:7d`.
- Les **actualités Yahoo Finance** de l'instantané yfinance.
- Les requêtes se règlent dans `config/veille.yaml`, avec un modèle par catégorie :
  `resultats`, `communique`, `presse`, `secteur`, `macro`, `officiel` (`site:airliquide.com`).
- Pour les catégories qui concernent la société, on ne garde que les titres qui la citent, puis on
  dédoublonne et on conserve les 15 plus récentes par catégorie.
- En cas de limitation de débit (HTTP 429), le script attend puis réessaie.

Chaque nouvelle arrive dans l'onglet **Actualites** de `data/saisies.xlsx` avec :
- le statut « à classer » ;
- une **fiabilité suggérée** selon la source : 3 pour l'AMF, Euronext, le site de la société,
  Reuters ; 2 pour la presse financière ; 1 pour le reste ;
- un **sens suggéré** (+1, 0 ou −1), tiré d'un lexique de mots positifs et négatifs.

## Ce que fait le groupe
Pour chaque nouvelle : une **note** de −2 à +2 (le signe donne le sens, la valeur l'importance),
une **fiabilité** de 1 à 3 et une **justification**. Une nouvelle hors sujet passe au statut
« écartée ».

## Notation
- **Quantitatif, comptage et classement**. On calcule
  net = (poids des nouvelles positives − poids des négatives) / (poids total),
  où le poids d'une nouvelle est celui de sa catégorie : résultats 3, communiqué 2, autres 1.
  On prend le sens noté par le groupe, ou à défaut le sens suggéré. Le sens suggéré ne vaut que
  pour les catégories qui concernent la société : `secteur` et `macro` sont trop bruitées.
  La grille [−0,6 ; −0,2 ; 0,2 ; 0,6] donne la note de −2 à +2.
- **Qualitatif, importance et fiabilité** : moyenne des notes du groupe pondérée par la
  fiabilité.

Le Journal du rapport indique combien de nouvelles ont été comptées avec un sens seulement
*suggéré*. Le paramètre `informations.utiliser_suggestions: false` les ignore complètement.
