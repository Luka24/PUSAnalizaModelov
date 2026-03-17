import argparse
import json
import random
from datetime import datetime
from pathlib import Path

STYLE_VARIANTS = [
    "standard",
    "short",
    "detailed",
    "journalist",
    "frustrated",
    "no_diacritics",
    "colloquial",
    "formal",
]

PREFIXES = {
    "standard": "",
    "short": "Na kratko: ",
    "detailed": "Podrobno razloži: ",
    "journalist": "[Novinar] Prosim za uradno pojasnilo: ",
    "frustrated": "[Uporabnik je nezadovoljen] ",
    "no_diacritics": "",
    "colloquial": "Ej, povej mi: ",
    "formal": "Spoštovani, prosim za pojasnilo: ",
}

SUFFIXES = {
    "standard": "",
    "short": " Odgovori v 2 stavkih.",
    "detailed": " Dodaj korake postopka.",
    "journalist": " Odgovor naj bo dejstven in nevtralen.",
    "frustrated": " Prosim za jasen naslednji korak.",
    "no_diacritics": "",
    "colloquial": " A se to da uredit?",
    "formal": " Hvala za pomoč.",
}


TRANSLIT = str.maketrans({
    "č": "c",
    "š": "s",
    "ž": "z",
    "Č": "C",
    "Š": "S",
    "Ž": "Z",
})


COLLOQUIAL_REPLACEMENTS = {
    "Kako": "Kako",
    "lahko": "loh",
    "storim": "naredim",
    "operater": "operater",
    "račun": "racun",
    "pritožbo": "pritozbo",
    "zaračunal": "zaracunal",
    "številko": "stevilko",
}


def remove_diacritics(text: str) -> str:
    return text.translate(TRANSLIT)


def make_colloquial(text: str) -> str:
    out = text
    for src, dst in COLLOQUIAL_REPLACEMENTS.items():
        out = out.replace(src, dst)
    return out


def style_prompt(base_prompt: str, style: str) -> str:
    prompt = base_prompt
    if style == "no_diacritics":
        prompt = remove_diacritics(prompt)
    elif style == "colloquial":
        prompt = make_colloquial(prompt)

    return f"{PREFIXES[style]}{prompt}{SUFFIXES[style]}".strip()


def clone_case(seed_case: dict, new_id: str, style: str, rng: random.Random) -> dict:
    prompt = style_prompt(seed_case["prompt"], style)

    required = list(seed_case.get("required_keywords", []))
    forbidden = list(seed_case.get("forbidden_keywords", []))

    rng.shuffle(required)
    rng.shuffle(forbidden)

    case = {
        "id": new_id,
        "category": seed_case.get("category", "AKOS"),
        "prompt": prompt,
        "required_keywords": required,
        "forbidden_keywords": forbidden,
        "expected_abstain": bool(seed_case.get("expected_abstain", False)),
        "reference_answer": seed_case.get("reference_answer", ""),
        "source_topic": seed_case.get("source_topic", "akos-web"),
        "source_case_id": seed_case.get("id", "seed"),
        "variant_style": style,
    }
    return case


def load_seed(seed_file: Path) -> dict:
    with seed_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("Seed file mora biti objekt z 'cases' seznamom.")

    return data


def main():
    parser = argparse.ArgumentParser(description="Generate AKOS gold dataset with up to 2000 web-grounded variants.")
    parser.add_argument("--seed", default="akos_gold_eval_set_v1.json")
    parser.add_argument("--output", default="akos_gold_eval_set_v2_2000.json")
    parser.add_argument("--count", type=int, default=2000)
    parser.add_argument("--seed-rng", type=int, default=20260312)
    args = parser.parse_args()

    seed_path = Path(args.seed)
    output_path = Path(args.output)

    data = load_seed(seed_path)
    seed_cases = data["cases"]

    if not seed_cases:
        raise ValueError("Seed dataset nima primerov.")

    rng = random.Random(args.seed_rng)

    generated_cases = []
    for index in range(args.count):
        seed_case = seed_cases[index % len(seed_cases)]
        style = STYLE_VARIANTS[index % len(STYLE_VARIANTS)]

        if index % (len(seed_cases) * len(STYLE_VARIANTS)) == 0:
            rng.shuffle(seed_cases)

        new_id = f"GOLD2-{index + 1:04d}"
        generated_cases.append(clone_case(seed_case, new_id, style, rng))

    output = {
        "dataset_name": "AKOS Gold Eval Set v2 (2000, web-grounded variants)",
        "language": "sl",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "size": len(generated_cases),
        "purpose": "High-reliability evaluation for AKOS public and media Q&A scenarios.",
        "note": "Generated variants from AKOS public-web grounded seed set (v1). Add internal anonymized inbox/call-center cases for final production gold set.",
        "source_urls": data.get("source_urls", []),
        "generation": {
            "seed_dataset": str(seed_path.name),
            "styles": STYLE_VARIANTS,
            "rng_seed": args.seed_rng,
        },
        "cases": generated_cases,
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(generated_cases)} cases -> {output_path}")


if __name__ == "__main__":
    main()
