import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def find_latest_json(results_dir: Path) -> Path:
    candidates = sorted(results_dir.glob("sl_benchmark_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"V mapi {results_dir} ni benchmark JSON datotek.")
    return candidates[0]


def load_results(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def summarize_model(model_name: str, model_payload: Dict, min_average_score: float) -> Dict:
    cases: List[Dict] = model_payload.get("cases", [])
    if not cases:
        return {
            "model": model_name,
            "avg": 0.0,
            "hard_fail": 0,
            "critical": 0,
            "latency": 0.0,
            "status": "FAIL",
            "case_count": 0,
            "category_scores": {},
        }

    avg_score = statistics.mean(c["scores"]["overall"] for c in cases)
    avg_latency = statistics.mean(c.get("latency_sec", 0.0) for c in cases)
    hard_fail = sum(1 for c in cases if c.get("hard_fail", False))
    critical = sum(1 for c in cases if c["scores"]["overall"] < 2.5)

    category_values: Dict[str, List[float]] = {}
    for case in cases:
        category_values.setdefault(case.get("category", "Ostalo"), []).append(case["scores"]["overall"])

    category_scores = {k: round(statistics.mean(v), 2) for k, v in sorted(category_values.items())}
    status = "PASS" if (hard_fail == 0 and avg_score >= min_average_score) else "FAIL"

    return {
        "model": model_name,
        "avg": round(avg_score, 3),
        "hard_fail": hard_fail,
        "critical": critical,
        "latency": round(avg_latency, 3),
        "status": status,
        "case_count": len(cases),
        "category_scores": category_scores,
        "cases": cases,
    }


def choose_recommendation(summaries: List[Dict]) -> Tuple[str, str]:
    passing = [s for s in summaries if s["status"] == "PASS"]
    if passing:
        passing.sort(key=lambda s: (-s["avg"], s["latency"]))
        best = passing[0]
        reason = (
            f"Model dosega PASS brez hard-fail primerov, ima najvišjo povprečno oceno ({best['avg']:.2f}) "
            f"ob povprečni latenci {best['latency']:.2f}s."
        )
        return best["model"], reason

    fallback = sorted(summaries, key=lambda s: (s["hard_fail"], -s["avg"], s["latency"]))[0]
    reason = (
        f"Noben model ni dosegel PASS. Kot začasni kandidat je izbran model z najmanj hard-fail primeri "
        f"({fallback['hard_fail']}) in najboljšo oceno med preostalimi ({fallback['avg']:.2f})."
    )
    return fallback["model"], reason


def pick_examples(cases: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    ordered = sorted(cases, key=lambda c: c["scores"]["overall"])
    worst = ordered[:3]
    best = ordered[-3:] if len(ordered) >= 3 else ordered
    return best, worst


def build_markdown(input_file: Path, summaries: List[Dict], recommended_model: str, recommendation_reason: str) -> str:
    lines: List[str] = []
    lines.append("# Končno poročilo benchmarka modelov (AKOS / slovenščina)")
    lines.append("")
    lines.append(f"- Datum generiranja: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- Vir rezultatov: {input_file.name}")
    lines.append("")

    lines.append("## Povzetek")
    lines.append("")
    lines.append("| Model | Status | Povpr. ocena | Povpr. latenca (s) | Hard-fail | Kritične (<2.5) | Testi |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for s in summaries:
        lines.append(
            f"| {s['model']} | {s['status']} | {s['avg']:.2f} | {s['latency']:.2f} | {s['hard_fail']} | {s['critical']} | {s['case_count']} |"
        )

    lines.append("")
    lines.append("## Priporočilo")
    lines.append("")
    lines.append(f"- Predlagani model: **{recommended_model}**")
    lines.append(f"- Utemeljitev: {recommendation_reason}")

    lines.append("")
    lines.append("## Kategorije")
    lines.append("")
    for s in summaries:
        lines.append(f"### {s['model']}")
        for cat, score in s["category_scores"].items():
            lines.append(f"- {cat}: {score:.2f}")
        lines.append("")

    lines.append("## Primeri (najboljši / najslabši)")
    lines.append("")
    for s in summaries:
        lines.append(f"### {s['model']}")
        best, worst = pick_examples(s.get("cases", []))
        lines.append("- Najboljši primeri:")
        for case in best:
            lines.append(f"  - {case['id']} ({case.get('category', 'Ostalo')}), ocena {case['scores']['overall']:.2f}")
        lines.append("- Najslabši primeri:")
        for case in worst:
            hf = " [HARD-FAIL]" if case.get("hard_fail") else ""
            lines.append(f"  - {case['id']} ({case.get('category', 'Ostalo')}), ocena {case['scores']['overall']:.2f}{hf}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate final benchmark report from sl_benchmark_*.json")
    parser.add_argument("--input", default="", help="Pot do benchmark JSON. Če ni podana, uporabi zadnjo datoteko iz --results-dir.")
    parser.add_argument("--results-dir", default="results", help="Mapa z benchmark JSON rezultati.")
    parser.add_argument("--output", default="", help="Izhodna .md datoteka. Privzeto final_report_YYYYMMDD_HHMMSS.md")
    parser.add_argument("--min-average-score", type=float, default=3.8)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    input_file = Path(args.input) if args.input else find_latest_json(results_dir)

    if not input_file.exists():
        raise FileNotFoundError(f"Vhodna datoteka ne obstaja: {input_file}")

    payload = load_results(input_file)
    summaries = [summarize_model(name, model_data, args.min_average_score) for name, model_data in payload.items()]
    summaries = sorted(summaries, key=lambda s: (s["status"] != "PASS", -s["avg"], s["latency"]))

    recommended_model, recommendation_reason = choose_recommendation(summaries)
    markdown = build_markdown(input_file, summaries, recommended_model, recommendation_reason)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path(args.output) if args.output else results_dir / f"final_report_{timestamp}.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(markdown, encoding="utf-8")

    print(f"Generated final report: {output_file}")


if __name__ == "__main__":
    main()
