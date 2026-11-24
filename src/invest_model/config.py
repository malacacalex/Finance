"""Chargement de la configuration.

Trois niveaux (conception §4) :
1. config/parametres.yaml : réglages techniques et grilles (choix du groupe) ;
2. config/scenarios/<nom>.yaml : hypothèses provisoires du groupe ;
3. config/client.yaml : réponses du client, qui l'emportent TOUJOURS sur le scénario.

Le résultat est un simple dictionnaire Python. On garde aussi la trace, pour
chaque valeur "client", de son origine (client ou scénario) afin de l'afficher
dans le rapport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Racine du projet : src/invest_model/config.py -> remonter de 3 niveaux
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


def load_yaml(path: Path) -> dict:
    """Lit un fichier YAML et renvoie un dictionnaire (vide si le fichier est vide)."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class Settings:
    """Configuration complète d'une exécution."""

    params: dict                      # parametres.yaml
    scenario_name: str                # nom lisible du scénario
    weights: dict                     # poids entre piliers
    quanti_share: dict                # part du quantitatif par pilier (lambda)
    decision: dict                    # seuils de décision
    client: dict                      # valeurs client fusionnées (client > scénario)
    origins: dict = field(default_factory=dict)  # clé client -> "client" ou "scénario"
    universe: dict = field(default_factory=dict)
    watch: dict = field(default_factory=dict)
    risks: dict = field(default_factory=dict)

    @property
    def uses_unvalidated_hypotheses(self) -> bool:
        """Vrai si au moins une valeur vient du scénario et non du client."""
        return any(origin == "scénario" for origin in self.origins.values())


def _merge_client(scenario_values: dict, client_values: dict) -> tuple[dict, dict]:
    """Fusionne : une valeur client non nulle remplace celle du scénario.

    Renvoie (valeurs fusionnées, origine de chaque valeur).
    """
    merged: dict[str, Any] = {}
    origins: dict[str, str] = {}
    keys = set(scenario_values) | set(client_values)
    for key in sorted(keys):
        client_value = client_values.get(key)
        if client_value is not None:
            merged[key] = client_value
            origins[key] = "client"
        elif scenario_values.get(key) is not None:
            merged[key] = scenario_values[key]
            origins[key] = "scénario"
        else:
            merged[key] = None
            origins[key] = "non renseigné"
    return merged, origins


def load_settings(scenario: str = "hypotheses_groupe", config_dir: Path = CONFIG_DIR) -> Settings:
    """Charge et fusionne toute la configuration."""
    params = load_yaml(config_dir / "parametres.yaml")
    scen = load_yaml(config_dir / "scenarios" / f"{scenario}.yaml")
    client_file = load_yaml(config_dir / "client.yaml")

    client, origins = _merge_client(scen.get("client", {}), client_file.get("client", {}) or {})

    # Poids : ceux du client s'il en impose, sinon ceux du scénario
    weights = client_file.get("poids_piliers") or scen["poids_piliers"]
    quanti_share = client_file.get("part_quanti") or scen["part_quanti"]
    origins["poids_piliers"] = "client" if client_file.get("poids_piliers") else "scénario"
    origins["part_quanti"] = "client" if client_file.get("part_quanti") else "scénario"

    settings = Settings(
        params=params,
        scenario_name=scen.get("nom", scenario),
        weights=weights,
        quanti_share=quanti_share,
        decision=scen["decision"],
        client=client,
        origins=origins,
        universe=load_yaml(config_dir / "univers.yaml").get("actions", {}),
        watch=load_yaml(config_dir / "veille.yaml"),
        risks=load_yaml(config_dir / "risques.yaml"),
    )
    _check_required(settings)
    return settings


# Valeurs indispensables à l'analyse d'une société : sans elles, on s'arrête
# avec un message clair plutôt que d'inventer une valeur (GRP-22).
REQUIRED_CLIENT_KEYS = [
    "horizon_jours",
    "montant_analyse",
    "niveau_confiance",
    "fenetre_historique_jours",
    "taux_sans_risque",
]


def _check_required(settings: Settings) -> None:
    missing = [k for k in REQUIRED_CLIENT_KEYS if settings.client.get(k) is None]
    if missing:
        raise ValueError(
            "Valeurs non renseignées : "
            + ", ".join(f"client.{k}" for k in missing)
            + ". Compléter config/client.yaml (réponse du professeur) ou le scénario."
        )


def project_path(relative: str) -> Path:
    """Chemin absolu à partir d'un chemin relatif à la racine du projet."""
    return PROJECT_ROOT / relative
