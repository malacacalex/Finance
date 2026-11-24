"""Ligne de commande.

    invest analyse AI.PA                 # télécharge, veille, analyse, rapport
    invest analyse AI.PA --hors-ligne    # rejoue le dernier instantané (sans réseau)
    invest analyse AI.PA --snapshot 2026-11-24
    invest veille AI.PA                  # seulement la veille d'actualités
    invest saisies AI.PA RMS.PA          # crée / complète data/saisies.xlsx

Sans installation : python -m invest_model analyse AI.PA
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from . import inputs
from .config import load_settings, project_path


def cmd_analyse(args) -> int:
    from .analyse import run_analysis
    from .report.charts import all_charts
    from .report.excel import write_report
    from .report.markdown import build_markdown

    settings = load_settings(args.scenario)
    result = run_analysis(args.ticker, settings, snapshot=args.snapshot, offline=args.hors_ligne,
                          with_watch=not args.sans_veille)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out = project_path(settings.params["donnees"]["dossier_sorties"]) / f"{args.ticker}_{stamp}"
    charts = all_charts(result, out / "graphiques")
    xlsx = write_report(result, out / "resultats.xlsx", charts)
    md = build_markdown(result, charts)
    (out / "rapport.md").write_text(md, encoding="utf-8")

    print()
    print(md.split("\n## 1. Graphique")[0])   # décision + scores dans le terminal
    print(f"Rapport Excel : {xlsx}")
    print(f"Synthèse     : {out / 'rapport.md'}")
    print(f"Saisies      : {project_path(settings.params['donnees']['classeur_saisies'])} "
          "(notes qualitatives, actualités à classer, risques, contrôle ABC)")
    return 0


def cmd_veille(args) -> int:
    from .watch import collect_news

    settings = load_settings(args.scenario)
    workbook = project_path(settings.params["donnees"]["classeur_saisies"])
    inputs.ensure_workbook(workbook, args.tickers, settings.risks)
    for ticker in args.tickers:
        log: list[str] = []
        news = collect_news(ticker, settings.universe[ticker], settings.watch, None, log)
        added = inputs.append_news(workbook, news)
        print(f"{ticker} : {len(news)} actualités trouvées, {added} ajoutée(s) à classer dans {workbook}")
        for line in log:
            print("  -", line)
    return 0


def cmd_saisies(args) -> int:
    settings = load_settings(args.scenario)
    workbook = project_path(settings.params["donnees"]["classeur_saisies"])
    inputs.ensure_workbook(workbook, args.tickers or list(settings.universe), settings.risks)
    print(f"Classeur prêt : {workbook}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="invest", description="Modèle d'aide à l'investissement (4 piliers)")
    parser.add_argument("--scenario", default="hypotheses_groupe", help="fichier de config/scenarios/ (sans .yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("analyse", help="analyse complète d'une société")
    p.add_argument("ticker", help="ex. AI.PA")
    p.add_argument("--snapshot", help="date AAAA-MM-JJ d'un instantané à rejouer")
    p.add_argument("--hors-ligne", action="store_true", help="utiliser le dernier instantané, sans réseau")
    p.add_argument("--sans-veille", action="store_true", help="ne pas lancer la veille d'actualités")
    p.set_defaults(func=cmd_analyse)

    p = sub.add_parser("veille", help="veille d'actualités (dorking Google News) -> saisies.xlsx")
    p.add_argument("tickers", nargs="+")
    p.set_defaults(func=cmd_veille)

    p = sub.add_parser("saisies", help="crée / complète le classeur de saisie")
    p.add_argument("tickers", nargs="*")
    p.set_defaults(func=cmd_saisies)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except PermissionError as exc:
        print(f"Fichier verrouillé (ouvert dans Excel ?) : {exc.filename}. Fermez-le puis relancez.", file=sys.stderr)
        return 1
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
