# Cahier des charges — Modèle d'aide à l'investissement

> **Document de référence du projet.** Les spécifications (`specifications.md`) et la conception
> (`conception.md`) découlent de ce document. Toute exigence y est identifiée par un code
> (`ENO-xx`, `CLI-xx`, `GRP-xx`) que les autres documents citent.
>
> **Statut : version de travail.** Les besoins du client ne sont pas encore connus : les sections
> correspondantes sont **à compléter** et **aucune valeur n'y est fixée à la place du client**.

| Version | Date | Auteur(s) | Modifications |
|---|---|---|---|
| 0.1 | 2026-11-24 | Groupe | Création de la structure, questions à poser au client |
| | | | |

---

## 1. Contexte et objet

Projet de cours de finance (école d'ingénieur, groupe de 4). Il s'agit de concevoir, coder et
documenter un **modèle d'aide à la décision d'investissement** qui propose une répartition d'un
capital entre plusieurs actions et des signaux d'achat et de vente sur une période courte.

Le modèle est une **aide à la décision** : il calcule des scores et une allocation que le groupe
analyse et assume. Il ne passe pas d'ordres réels.

## 2. Parties prenantes

| Rôle | Qui | Attentes connues |
|---|---|---|
| Client / commanditaire | Professeur de finance | *À recueillir (voir §4 et §7)* |
| Maîtrise d'œuvre | Groupe de 4 étudiants | Livrer un modèle juste, explicable à l'oral et transmissible |
| Utilisateurs | Membres du groupe | Saisir les notes qualitatives, lancer le modèle, lire l'export Excel |

## 3. Données connues de l'énoncé

Ces éléments viennent de l'énoncé du projet. Ils sont considérés comme acquis, sauf
contre-indication du client.

| ID | Élément | Valeur | Remarque |
|---|---|---|---|
| ENO-01 | Capital à répartir | 500 000 € | Faut-il tout investir ? Voir CLI-05 |
| ENO-02 | Univers d'investissement | Hermès (RMS.PA), Air Liquide (AI.PA), Capgemini (CAP.PA), TotalEnergies (TTE.PA), Dassault Systèmes (DSY.PA) | 5 actions du CAC 40 cotées sur Euronext Paris |
| ENO-03 | Horizon | 1 semaine | Dates exactes à confirmer : voir CLI-03 |
| ENO-04 | Opérations | Achats et ventes possibles | Règles précises à confirmer : voir CLI-04 |

---

## 4. Besoins et contraintes du client — *à compléter*

> **Mode d'emploi.** Pour chaque section, reporter la réponse du professeur, la date et le support
> (oral, mail, sujet écrit). Chaque besoin renvoie aux **paramètres de configuration** qu'il
> alimente. Le code ne contient aucune de ces valeurs en dur : elles se règlent dans
> `config/client.yaml` (voir `conception.md`).
>
> Tant qu'une valeur n'est pas fournie par le client, elle reste vide (`null`). Le modèle ne peut
> alors tourner qu'avec un **scénario d'hypothèses du groupe**, explicitement signalé comme non
> validé sur tous les résultats.

### 4.1 CLI-01 — Objectifs de rendement

| Question | Réponse du client | Date / source | Paramètres impactés |
|---|---|---|---|
| Y a-t-il un objectif de rendement sur la semaine (absolu, en %, en €) ? | | | `client.objectif_rendement` |
| Est-ce un objectif à atteindre, ou un critère parmi d'autres ? | | | `client.objectif_type` |
| Faut-il battre un indice de référence (CAC 40, portefeuille équipondéré) ? | | | `client.benchmark` |

### 4.2 CLI-02 — Tolérance au risque

| Question | Réponse du client | Date / source | Paramètres impactés |
|---|---|---|---|
| Profil de risque attendu (prudent, équilibré, dynamique, ou autre) ? | | | `client.profil_risque` |
| Perte maximale acceptable sur la semaine (en € ou en %) ? | | | `client.perte_max` |
| Mesure de risque imposée ou préférée (volatilité, VaR, CVaR, drawdown) ? À quel niveau de confiance ? | | | `client.mesure_risque`, `client.niveau_confiance` |
| Faut-il des stop-loss ou des take-profit ? | | | `client.stop_loss`, `client.take_profit` |

### 4.3 CLI-03 — Horizon et calendrier

| Question | Réponse du client | Date / source | Paramètres impactés |
|---|---|---|---|
| Dates exactes de début et de fin de la semaine ? | | | `client.date_debut`, `client.date_fin` |
| À quel prix entre-t-on et sort-on (ouverture, clôture, cours à une heure donnée) ? | | | `client.prix_execution` |
| Combien de fois peut-on revoir le portefeuille dans la semaine (une fois à J0, chaque jour, sans limite) ? | | | `client.nb_reequilibrages`, `client.frequence` |
| Le portefeuille doit-il être soldé en cash à la fin de la semaine ? | | | `client.liquidation_finale` |

### 4.4 CLI-04 — Règles d'achat et de vente

| Question | Réponse du client | Date / source | Paramètres impactés |
|---|---|---|---|
| La vente à découvert est-elle autorisée ? | | | `client.vente_decouvert` |
| L'effet de levier ou l'emprunt sont-ils autorisés ? | | | `client.levier_max` |
| Faut-il acheter un nombre entier d'actions (Hermès dépasse 2 000 € l'action) ? | | | `client.actions_entieres` |
| Y a-t-il un nombre maximal d'ordres ou de transactions ? | | | `client.nb_ordres_max` |
| Les signaux doivent-ils suivre des règles imposées (par exemple « acheter uniquement si… ») ? | | | `client.regles_signaux` |

### 4.5 CLI-05 — Contraintes de répartition

| Question | Réponse du client | Date / source | Paramètres impactés |
|---|---|---|---|
| Faut-il investir la totalité des 500 000 € ? Peut-on garder du cash, et jusqu'à combien ? | | | `client.cash_min`, `client.cash_max` |
| Poids minimal et maximal par action ? | | | `client.poids_min`, `client.poids_max` |
| Faut-il détenir les 5 actions, ou peut-on en exclure ? | | | `client.nb_lignes_min` |
| Le cash est-il rémunéré ? À quel taux ? | | | `client.taux_sans_risque` |

### 4.6 CLI-06 — Frais et fiscalité

| Question | Réponse du client | Date / source | Paramètres impactés |
|---|---|---|---|
| Frais de courtage : pourcentage, montant fixe, minimum par ordre ? | | | `client.frais_pct`, `client.frais_fixe`, `client.frais_min` |
| Faut-il appliquer la taxe sur les transactions financières (TTF française) ? | | | `client.ttf` |
| Faut-il tenir compte d'un spread ou d'un glissement ? | | | `client.slippage` |
| Faut-il prendre en compte les dividendes détachés pendant la semaine ? | | | `client.dividendes` |

### 4.7 CLI-07 — Format de rendu et évaluation

| Question | Réponse du client | Date / source | Paramètres impactés |
|---|---|---|---|
| Quels livrables sont attendus (rapport écrit, fichier Excel, code, soutenance), et à quelles dates ? | | | — (organisation) |
| Quel format pour le fichier Excel (onglets imposés, gabarit fourni) ? | | | `rapport.*` |
| Combien de pages pour le rapport et combien de minutes pour la soutenance ? | | | — |
| Sur quels critères le projet est-il noté (performance réelle, rigueur de la méthode, qualité du rendu) ? | | | — |
| Faut-il justifier chaque décision d'achat ou de vente par écrit ? | | | `rapport.justifications` |

### 4.8 CLI-08 — Méthode et sources

| Question | Réponse du client | Date / source | Paramètres impactés |
|---|---|---|---|
| Les 4 piliers (graphique, financier, informations, hasard) conviennent-ils ? Faut-il en ajouter ou en retirer ? | | | `poids.piliers` |
| Le client impose-t-il des poids entre piliers, ou entre quantitatif et qualitatif ? | | | `poids.*` |
| ABC Bourse convient-il comme référence ? D'autres sources sont-elles imposées ou interdites ? | | | `sources.*` |
| Les données gratuites (yfinance) sont-elles acceptables ? | | | `donnees.fournisseur` |
| Sur quelle période historique calibrer le modèle (volatilité, rendement) ? | | | `monte_carlo.fenetre_historique` |

### 4.9 Autres besoins exprimés

*Section libre : y reporter tout besoin du client qui n'entre pas dans les rubriques ci-dessus,
et lui attribuer un identifiant `CLI-09`, `CLI-10`, etc.*

---

## 5. Exigences fixées par le groupe

Ces exigences viennent du groupe, pas du client. Elles peuvent être remises en cause par une
réponse du client : dans ce cas, c'est la réponse du client qui l'emporte, et on met ce document
à jour.

### 5.1 Exigences fonctionnelles

| ID | Exigence |
|---|---|
| GRP-01 | Le modèle combine **4 piliers** : Graphique, Financier, Informations, Hasard. |
| GRP-02 | Chacun des piliers Graphique, Financier et Informations produit un **score quantitatif** (calculé) et un **score qualitatif** (grille notée par le groupe de −2 à +2, avec une justification écrite obligatoire). Les deux scores sont pondérés entre eux. |
| GRP-03 | **Pilier Graphique**, 5 outils : RSI, supports et résistances par points pivots, bandes de Bollinger, MACD et sa ligne de signal, moyennes mobiles. Le quantitatif repose sur des signaux à seuils. Le qualitatif est la lecture du graphique par le groupe (tendance, figures). |
| GRP-04 | **Pilier Financier**, ratios comparés au secteur : PER, PEG, rendement du dividende, ROE, endettement net / EBITDA, marge. Le qualitatif porte sur la solidité du modèle économique et la position sectorielle. |
| GRP-05 | **Pilier Informations** : résultats, communiqués officiels, macroéconomie, secteur. Le quantitatif est le comptage et le classement des nouvelles positives et négatives. Le qualitatif est l'importance et la fiabilité de chaque information, notées par le groupe. |
| GRP-06 | **Pilier Hasard** : simulation Monte Carlo par mouvement brownien géométrique, calibrée sur le rendement et la volatilité historiques. Elle estime le risque et la fourchette de résultats du portefeuille sur l'horizon. |
| GRP-07 | **Tous les poids sont configurables** : entre piliers, et entre quantitatif et qualitatif. |
| GRP-08 | Le score final produit une **allocation des 500 000 €** et des **signaux d'achat et de vente**. |
| GRP-09 | **Export Excel** des résultats. |
| GRP-10 | La partie Monte Carlo doit pouvoir être **refaite dans Excel** (ALEA, LOI.NORMALE.INVERSE, table de données) pour vérification. |
| GRP-11 | Les indicateurs utilisent les **mêmes réglages qu'ABC Bourse** (RSI 14 jours, moyennes mobiles 20/50/100 jours, Bollinger, MACD et sa ligne de signal), pour pouvoir comparer nos résultats à leurs fiches « Analyse et conseil ». |

### 5.2 Exigences non fonctionnelles

| ID | Exigence |
|---|---|
| GRP-20 | Application en **Python**, données de marché tirées d'une **API gratuite** (yfinance). |
| GRP-21 | Code **lisible et commenté**, que chaque membre du groupe peut expliquer à l'oral et reprendre. |
| GRP-22 | **Rien de ce qui dépend du client n'est codé en dur** : profil de risque, règles et poids par défaut sont des paramètres. |
| GRP-23 | **Traçabilité** : la documentation de chaque indicateur cite la leçon ABC Bourse utilisée. |
| GRP-24 | **Reproductibilité** : on peut relancer une exécution sur les mêmes données et obtenir les mêmes résultats (instantané de données daté, graine aléatoire fixée). |
| GRP-25 | **Évolutivité** : ce cahier des charges peut évoluer. Une évolution se traduit par un changement de configuration plutôt que par une réécriture du code. |
| GRP-26 | Le projet doit pouvoir devenir ensuite un projet personnel : architecture modulaire, univers d'actions et horizon paramétrables. |

## 6. Hors périmètre

- Passage d'ordres réels chez un courtier.
- Données temps réel ou intrajournalières, sauf si le client les demande.
- Analyse de sentiment automatique des actualités : le classement est fait par le groupe.
- Conseil en investissement au sens réglementaire.

---

## 7. Questions à poser au professeur

Les questions sont classées par priorité. Les questions **bloquantes** conditionnent des choix de
conception. Les autres peuvent attendre.

### 7.1 Bloquantes (à poser en premier)

1. **Dates** : quelles sont les dates exactes de la semaine, et à quel prix entre-t-on et sort-on (ouverture ou clôture) ? *(CLI-03)*
2. **Fréquence** : peut-on modifier le portefeuille pendant la semaine ? Combien de fois ? *(CLI-03)*
3. **Investissement total** : faut-il investir les 500 000 € en totalité, ou peut-on garder du cash ? *(CLI-05)*
4. **Vente à découvert et levier** : sont-ils autorisés ? Que signifie précisément « ventes possibles » ? *(CLI-04)*
5. **Frais** : faut-il simuler des frais de transaction ? Lesquels ? *(CLI-06)*
6. **Évaluation** : est-on noté sur la performance réelle de la semaine, sur la méthode, ou sur les deux ? *(CLI-07)*

### 7.2 Importantes

7. Y a-t-il un profil de risque ou une perte maximale à respecter ? *(CLI-02)*
8. Y a-t-il un poids minimal ou maximal par action, ou une obligation de détenir les 5 ? *(CLI-05)*
9. Faut-il acheter un nombre entier d'actions ? *(CLI-04)*
10. Y a-t-il un objectif de rendement ou un indice à battre ? *(CLI-01)*
11. Les 4 piliers et leurs poids sont-ils libres, ou y a-t-il des attentes ? *(CLI-08)*
12. Quel format de rendu est attendu (rapport, Excel, soutenance), avec quel gabarit et quelles échéances ? *(CLI-07)*

### 7.3 Pour affiner

13. Les données yfinance sont-elles acceptables ? D'autres sources sont-elles imposées ou interdites ? *(CLI-08)*
14. Faut-il tenir compte des dividendes détachés pendant la semaine ? *(CLI-06)*
15. Faut-il des stop-loss ou des take-profit ? *(CLI-02)*
16. Sur quelle période historique calibrer la volatilité ? *(CLI-08)*
17. Le cash est-il rémunéré ? *(CLI-05)*
18. Faut-il justifier chaque décision par écrit dans le rendu ? *(CLI-07)*

---

## 8. Gestion des évolutions

1. Toute réponse du client est reportée au §4, avec sa date et sa source.
2. On incrémente la version et on complète le tableau d'historique en tête de document.
3. On répercute la réponse dans `config/client.yaml`, puis on vérifie si `specifications.md` est
   impacté. Chaque spécification cite les identifiants qui la justifient, ce qui permet de
   retrouver les impacts.
4. Si une réponse contredit une exigence du groupe (§5), on modifie l'exigence du groupe et on
   note la raison dans l'historique.
