import argparse
import csv
import json
import os
import random
import re
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests


def load_cases(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        return payload["cases"]

    raise ValueError("Neveljaven format dataset datoteke. Pričakovan je seznam primerov ali objekt s poljem 'cases'.")


def sample_cases(cases: List[Dict], max_cases: int, strategy: str, seed: int) -> List[Dict]:
    if max_cases <= 0 or max_cases >= len(cases):
        return cases

    rng = random.Random(seed)

    if strategy == "random":
        picked = list(cases)
        rng.shuffle(picked)
        return picked[:max_cases]

    by_category: Dict[str, List[Dict]] = {}
    for case in cases:
        category = case.get("category", "Ostalo")
        by_category.setdefault(category, []).append(case)

    categories = sorted(by_category.keys())
    if not categories:
        return cases[:max_cases]

    per_category = max(1, max_cases // len(categories))
    sampled = []
    leftovers = []

    for category in categories:
        items = list(by_category[category])
        rng.shuffle(items)
        sampled.extend(items[:per_category])
        leftovers.extend(items[per_category:])

    if len(sampled) < max_cases:
        rng.shuffle(leftovers)
        sampled.extend(leftovers[: max_cases - len(sampled)])

    if len(sampled) > max_cases:
        rng.shuffle(sampled)
        sampled = sampled[:max_cases]

    return sampled


def call_vllm_openai(
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    temperature: float,
    timeout: int,
    max_retries: int,
    retry_backoff_sec: float,
):
    url = f"{base_url.rstrip('/')}/completions"
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "prompt": f"Uporabnik: {prompt}\nAsistent: ",
        "temperature": temperature,
        "max_tokens": 1024,
    }

    attempt = 0
    while True:
        started = time.perf_counter()
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.exceptions.Timeout:
            if attempt >= max_retries:
                raise
            time.sleep(max(0.2, retry_backoff_sec * (2 ** attempt)))
            attempt += 1
            continue
        except requests.exceptions.RequestException:
            if attempt >= max_retries:
                raise
            time.sleep(max(0.2, retry_backoff_sec * (2 ** attempt)))
            attempt += 1
            continue

        elapsed = time.perf_counter() - started

        if response.status_code < 400:
            data = response.json()
            text = (
                data.get("choices", [{}])[0]
                .get("text", "")
                .strip()
            )
            usage = data.get("usage", {})
            tokens = usage.get("completion_tokens")
            return text, elapsed, tokens

        retriable = response.status_code in {408, 409, 429, 500, 502, 503, 504}
        if not retriable or attempt >= max_retries:
            raise RuntimeError(f"Error {response.status_code}: {response.text}")

        time.sleep(max(0.2, retry_backoff_sec * (2 ** attempt)))
        attempt += 1


def normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def render_case_prompt(case: Dict) -> str:
    if isinstance(case.get("conversation"), list) and case["conversation"]:
        lines = []
        for turn in case["conversation"]:
            role = (turn.get("role") or "user").strip().lower()
            content = (turn.get("content") or "").strip()
            if not content:
                continue
            if role == "assistant":
                lines.append(f"Asistent: {content}")
            else:
                lines.append(f"Uporabnik: {content}")

        transcript = "\n".join(lines)
        return (
            "Spodaj je del pogovora. Odgovori na zadnje uporabnikovo vprašanje jedrnato, pravilno in brez ugibanja.\n\n"
            f"{transcript}\n\n"
            "Odgovor asistent:"
        )

    return case["prompt"]


def repetition_penalty(text: str):
    words = re.findall(r"\w+", text.lower())
    if len(words) < 8:
        return 0.0
    trigrams = [tuple(words[i : i + 3]) for i in range(len(words) - 2)]
    unique = len(set(trigrams))
    total = len(trigrams)
    ratio = unique / total if total else 1.0
    return max(0.0, 1.0 - ratio)


def slovene_signal_score(text: str):
    if not text.strip():
        return 0.0

    lower = text.lower()
    diacritics = len(re.findall(r"[čšž]", lower))
    common_sl_words = [
        "in", "je", "da", "se", "za", "na", "ali", "lahko", "uporabnik", "storitev", "podatki", "račun"
    ]
    hits = sum(1 for word in common_sl_words if re.search(rf"\b{re.escape(word)}\b", lower))

    score = 0.0
    if diacritics >= 2:
        score += 2.0
    elif diacritics == 1:
        score += 1.0

    score += min(3.0, hits / 2.0)
    return min(5.0, score)


def keyword_score(text: str, required_keywords: List[str]):
    if not required_keywords:
        return 5.0

    lower = normalize(text)
    matched = 0
    for keyword in required_keywords:
        if normalize(keyword) in lower:
            matched += 1

    ratio = matched / len(required_keywords)
    return round(ratio * 5.0, 2)


def forbidden_score(text: str, forbidden_keywords: List[str]):
    if not forbidden_keywords:
        return 5.0

    lower = normalize(text)
    hits = 0
    for keyword in forbidden_keywords:
        if normalize(keyword) in lower:
            hits += 1

    if hits == 0:
        return 5.0

    penalty_ratio = hits / len(forbidden_keywords)
    return round(max(0.0, 5.0 * (1.0 - penalty_ratio)), 2)


def abstention_score(text: str, expected_abstain: bool):
    if not expected_abstain:
        return 5.0

    lower = normalize(text)
    abstain_patterns = [
        "ni v bazi",
        "nimam podatka",
        "tega podatka nimam",
        "ne morem potrditi",
        "prosim preverite",
        "uradni kanali",
        "www.akos.si"
    ]
    hits = sum(1 for pattern in abstain_patterns if pattern in lower)
    return round(min(5.0, hits * 1.2), 2)


def fluency_score(text: str):
    content = text.strip()
    if not content:
        return 0.0

    sentence_like = len(re.findall(r"[.!?]", content))
    length_ok = 30 <= len(content) <= 1800
    rep_pen = repetition_penalty(content)

    score = 2.0
    if sentence_like >= 1:
        score += 1.5
    if length_ok:
        score += 1.0
    score += max(0.0, 0.5 - rep_pen)
    return round(min(5.0, score), 2)


def evaluate_answer(case: Dict, text: str):
    required_keywords = case.get("required_keywords") or case.get("expected_keywords") or []
    forbidden_keywords = case.get("forbidden_keywords", [])
    expected_abstain = bool(case.get("expected_abstain", False))

    s_score = slovene_signal_score(text)
    r_score = keyword_score(text, required_keywords)
    fbd_score = forbidden_score(text, forbidden_keywords)
    abs_score = abstention_score(text, expected_abstain)
    f_score = fluency_score(text)

    final = round(
        (0.25 * s_score)
        + (0.30 * r_score)
        + (0.20 * f_score)
        + (0.15 * abs_score)
        + (0.10 * fbd_score),
        2,
    )

    return {
        "slovene_signal": round(s_score, 2),
        "required_coverage": round(r_score, 2),
        "fluency": round(f_score, 2),
        "abstention": round(abs_score, 2),
        "forbidden_control": round(fbd_score, 2),
        "overall": final
    }


def detect_hard_fail(
    case: Dict,
    text: str,
    scores: Dict,
    hard_fail_enabled: bool,
    abstention_threshold: float,
) -> Tuple[bool, List[str]]:
    if not hard_fail_enabled:
        return False, []

    reasons: List[str] = []
    lower = normalize(text)

    forbidden_keywords = case.get("forbidden_keywords", [])
    if case.get("hard_fail_on_forbidden", True) and forbidden_keywords:
        found = [keyword for keyword in forbidden_keywords if normalize(keyword) in lower]
        if found:
            reasons.append(f"Prepovedana trditev: {', '.join(found[:3])}")

    if bool(case.get("expected_abstain", False)) and scores.get("abstention", 0.0) < abstention_threshold:
        reasons.append("Nezadostna abstinenca pri primeru, kjer je zahtevana.")

    return len(reasons) > 0, reasons


def write_markdown_report(results, output_md: Path, min_average_score: float):
    lines = []
    lines.append("# Poročilo benchmarka GaMS modela za slovenščino (Sling HPC / vLLM)")
    lines.append("")
    lines.append(f"- Datum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("## Povzetek modelov")
    lines.append("")
    lines.append("| Model | Status | Povpr. ocena | Povpr. čas (s) | Testi | Kritične napake | Hard-fail |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")

    for model_name, model_result in results.items():
        avg_score = statistics.mean(item["scores"]["overall"] for item in model_result["cases"])
        avg_time = statistics.mean(item["latency_sec"] for item in model_result["cases"])
        critical_failures = sum(1 for item in model_result["cases"] if item["scores"]["overall"] < 2.5)
        hard_fail_count = sum(1 for item in model_result["cases"] if item.get("hard_fail", False))
        status = "PASS" if (avg_score >= min_average_score and hard_fail_count == 0) else "FAIL"
        lines.append(
            f"| {model_name} | {status} | {avg_score:.2f} | {avg_time:.2f} | {len(model_result['cases'])} | {critical_failures} | {hard_fail_count} |"
        )

    lines.append("")
    lines.append("## Povzetek po kategorijah")
    lines.append("")

    for model_name, model_result in results.items():
        lines.append(f"### {model_name}")
        category_map: Dict[str, List[float]] = {}
        for case in model_result["cases"]:
            category = case.get("category", "Ostalo")
            category_map.setdefault(category, []).append(case["scores"]["overall"])

        for category, values in sorted(category_map.items()):
            lines.append(f"- {category}: {statistics.mean(values):.2f}")
        lines.append("")

    lines.append("## Primeri")
    lines.append("")

    for model_name, model_result in results.items():
        lines.append(f"### {model_name}")
        lines.append("")

        sorted_cases = sorted(model_result["cases"], key=lambda case: case["scores"]["overall"])
        picked = sorted_cases[:2] + sorted_cases[-1:]

        for case in picked:
            lines.append(f"- **{case['id']}** ({case['category']}), ocena: {case['scores']['overall']:.2f}")
            lines.append(f"  - Prompt: {case['prompt']}")
            snippet = case["answer"].replace("\n", " ").strip()
            if len(snippet) > 280:
                snippet = snippet[:280] + " ..."
            lines.append(f"  - Odgovor: {snippet}")
            if case.get("hard_fail"):
                lines.append(f"  - Hard-fail razlog: {'; '.join(case.get('hard_fail_reasons', []))}")
        lines.append("")

    output_md.write_text("\n".join(lines), encoding="utf-8")


def write_csv_outputs(
    results: Dict,
    cases_csv_path: Path,
    summary_csv_path: Path,
    min_average_score: float,
):
    with cases_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "model",
                "id",
                "category",
                "score_overall",
                "score_slovene_signal",
                "score_required_coverage",
                "score_fluency",
                "score_abstention",
                "score_forbidden_control",
                "hard_fail",
                "hard_fail_reasons",
                "latency_sec",
                "tokens",
                "expected_abstain",
                "source_topic",
                "source_url",
                "prompt",
                "answer",
            ],
        )
        writer.writeheader()

        for model_name, model_result in results.items():
            for case in model_result["cases"]:
                writer.writerow(
                    {
                        "model": model_name,
                        "id": case.get("id", ""),
                        "category": case.get("category", ""),
                        "score_overall": case.get("scores", {}).get("overall", ""),
                        "score_slovene_signal": case.get("scores", {}).get("slovene_signal", ""),
                        "score_required_coverage": case.get("scores", {}).get("required_coverage", ""),
                        "score_fluency": case.get("scores", {}).get("fluency", ""),
                        "score_abstention": case.get("scores", {}).get("abstention", ""),
                        "score_forbidden_control": case.get("scores", {}).get("forbidden_control", ""),
                        "hard_fail": case.get("hard_fail", False),
                        "hard_fail_reasons": "; ".join(case.get("hard_fail_reasons", [])),
                        "latency_sec": case.get("latency_sec", ""),
                        "tokens": case.get("tokens", ""),
                        "expected_abstain": case.get("expected_abstain", False),
                        "source_topic": case.get("source_topic", ""),
                        "source_url": case.get("source_url", ""),
                        "prompt": case.get("prompt", ""),
                        "answer": case.get("answer", ""),
                    }
                )

    with summary_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "model",
                "status",
                "avg_score",
                "avg_latency_sec",
                "tests",
                "critical_failures",
                "hard_fail_count",
            ],
        )
        writer.writeheader()

        for model_name, model_result in results.items():
            avg_score = statistics.mean(item["scores"]["overall"] for item in model_result["cases"])
            avg_time = statistics.mean(item["latency_sec"] for item in model_result["cases"])
            critical_failures = sum(1 for item in model_result["cases"] if item["scores"]["overall"] < 2.5)
            hard_fail_count = sum(1 for item in model_result["cases"] if item.get("hard_fail", False))
            status = "PASS" if (avg_score >= min_average_score and hard_fail_count == 0) else "FAIL"
            writer.writerow(
                {
                    "model": model_name,
                    "status": status,
                    "avg_score": round(avg_score, 4),
                    "avg_latency_sec": round(avg_time, 4),
                    "tests": len(model_result["cases"]),
                    "critical_failures": critical_failures,
                    "hard_fail_count": hard_fail_count,
                }
            )


def build_instruction(case_prompt: str, strict_domain_mode: bool):
    if strict_domain_mode:
        return (
            "Odgovarjaj kot slovensko govoreči asistent za AKOS. "
            "Bodi kratek, natančen in ne ugibaj. "
            "Če podatka nimaš, to jasno povej in usmeri uporabnika na uradne kanale AKOS.\n\n"
            f"Vprašanje: {case_prompt}\nOdgovor:"
        )
    return case_prompt


def format_seconds(total_seconds: float) -> str:
    seconds = max(0, int(total_seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes:02d}m {secs:02d}s"


def main():
    parser = argparse.ArgumentParser(description="Benchmark GaMS (OpenAI-compatible) LLM modelov za slovenščino (Sling HPC / vLLM).")
    parser.add_argument("--base-url", required=True, help="OpenAI-kompatibilen URL (npr. http://<hpc_ip>:8000/v1)")
    parser.add_argument("--api-key", default="", help="API ključ če ga server zahteva (prek vLLM pogosto ni obvezen)")
    parser.add_argument("--models", nargs="+", required=True, help="Seznam imen modelov, natanko tako, kot se razkrivajo na /v1/models")
    parser.add_argument("--cases", default="backend/data/akos_gold_eval_set_v2_2000.json", help="Pot do JSON testnih primerov")
    parser.add_argument("--temperature", type=float, default=0.2, help="Temperatura generiranja")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout na zahtevek v sekundah")
    parser.add_argument("--max-retries", type=int, default=3, help="Maksimalno število ponovitev pri prehodnih HTTP napakah.")
    parser.add_argument("--retry-backoff-sec", type=float, default=1.5, help="Začetni backoff (sekunde), eksponentno naraščanje pri ponovitvah.")
    parser.add_argument("--out-dir", default="results", help="Izhodna mapa")
    parser.add_argument("--max-cases", type=int, default=0, help="Maksimalno število primerov (0 = vsi).")
    parser.add_argument(
        "--sample-strategy",
        choices=["stratified", "random"],
        default="stratified",
        help="Strategija vzorčenja, kadar je --max-cases manjši od velikosti dataseta.",
    )
    parser.add_argument("--sample-seed", type=int, default=42, help="Seed za ponovljivo vzorčenje primerov.")
    parser.add_argument(
        "--csv-prefix",
        default="",
        help="Prefix CSV izhoda (brez končnice). Če ni podan, se uporabi timestamp.",
    )
    parser.add_argument("--min-average-score", type=float, default=3.8, help="Minimalna povprečna ocena za status PASS.")
    parser.add_argument("--disable-hard-fail", action="store_true", help="Izklopi hard-fail pravilo.")
    parser.add_argument(
        "--hard-fail-abstention-threshold",
        type=float,
        default=2.5,
        help="Prag abstinence za hard-fail pri primerih z expected_abstain=true.",
    )
    parser.add_argument(
        "--strict-domain-mode",
        action="store_true",
        help="Doda navodilo za AKOS-slog, ne-ugibanje in varno abstinenco.",
    )
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.exists():
        fallback_data = Path("backend/data") / Path(args.cases).name
        if fallback_data.exists():
            cases_path = fallback_data
        else:
            raise FileNotFoundError(f"Datoteka primerov ne obstaja: {cases_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = load_cases(cases_path)
    original_count = len(cases)
    cases = sample_cases(
        cases,
        max_cases=args.max_cases,
        strategy=args.sample_strategy,
        seed=args.sample_seed,
    )

    if len(cases) != original_count:
        print(
            f"[INFO] Uporabljam vzorec {len(cases)}/{original_count} primerov "
            f"(strategy={args.sample_strategy}, seed={args.sample_seed})"
        )

    all_results = {}

    benchmark_start = time.perf_counter()

    for model in args.models:
        model_cases = []
        print(f"\n[INFO] Testiram model: {model}")
        model_start = time.perf_counter()
        total_cases = len(cases)

        for index, case in enumerate(cases, start=1):
            prompt = render_case_prompt(case)
            final_prompt = build_instruction(prompt, strict_domain_mode=args.strict_domain_mode)
            try:
                answer, latency, tokens = call_vllm_openai(
                    base_url=args.base_url,
                    api_key=args.api_key,
                    model=model,
                    prompt=final_prompt,
                    temperature=args.temperature,
                    timeout=args.timeout,
                    max_retries=args.max_retries,
                    retry_backoff_sec=args.retry_backoff_sec,
                )
                scores = evaluate_answer(case, answer)
                print(f"  - {case['id']}: ocena={scores['overall']:.2f}, čas={latency:.2f}s")
            except Exception as exc:
                answer = f"NAPAKA: {exc}"
                latency = 0.0
                tokens = None
                scores = {
                    "slovene_signal": 0.0,
                    "required_coverage": 0.0,
                    "fluency": 0.0,
                    "abstention": 0.0,
                    "forbidden_control": 0.0,
                    "overall": 0.0,
                }
                print(f"  - {case['id']}: napaka ({exc})")

            hard_fail, hard_fail_reasons = detect_hard_fail(
                case=case,
                text=answer,
                scores=scores,
                hard_fail_enabled=not args.disable_hard_fail,
                abstention_threshold=args.hard_fail_abstention_threshold,
            )

            model_cases.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "prompt": prompt,
                    "required_keywords": case.get("required_keywords", case.get("expected_keywords", [])),
                    "forbidden_keywords": case.get("forbidden_keywords", []),
                    "expected_abstain": case.get("expected_abstain", False),
                    "source_topic": case.get("source_topic", ""),
                    "source_url": case.get("source_url", ""),
                    "answer": answer,
                    "latency_sec": round(latency, 3),
                    "tokens": tokens,
                    "scores": scores,
                    "notes": case.get("notes", ""),
                    "hard_fail": hard_fail,
                    "hard_fail_reasons": hard_fail_reasons,
                }
            )

            elapsed = time.perf_counter() - model_start
            avg_case = elapsed / index if index > 0 else 0.0
            remaining = total_cases - index
            eta = remaining * avg_case
            percent = (index / total_cases * 100.0) if total_cases else 100.0
            
            # Print less often to speed up console output
            if index % 5 == 0 or index == total_cases:
                print(
                    f"    napredek: {index}/{total_cases} ({percent:.1f}%) | "
                    f"elapsed {format_seconds(elapsed)} | ETA {format_seconds(eta)}"
                )

        all_results[model] = {"cases": model_cases}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_prefix = args.csv_prefix.strip() or f"gams_benchmark_{timestamp}"
    json_out = out_dir / f"{csv_prefix}.json"
    md_out = out_dir / f"{csv_prefix}.md"
    csv_cases_out = out_dir / f"{csv_prefix}_cases.csv"
    csv_summary_out = out_dir / f"{csv_prefix}_summary.csv"

    json_out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_report(all_results, md_out, min_average_score=args.min_average_score)
    write_csv_outputs(
        all_results,
        cases_csv_path=csv_cases_out,
        summary_csv_path=csv_summary_out,
        min_average_score=args.min_average_score,
    )

    total_elapsed = time.perf_counter() - benchmark_start

    print("\n[OK] Benchmark končan")
    print(f"- JSON: {json_out}")
    print(f"- MD:   {md_out}")
    print(f"- CSV cases:   {csv_cases_out}")
    print(f"- CSV summary: {csv_summary_out}")
    print(f"- Total duration: {format_seconds(total_elapsed)}")


if __name__ == "__main__":
    main()

