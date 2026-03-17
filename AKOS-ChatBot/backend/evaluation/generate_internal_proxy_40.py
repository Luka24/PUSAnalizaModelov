import json
from datetime import datetime
from pathlib import Path

BASE_CASES = [
    {
        "category": "Inbox - račun",
        "prompt": "[Anonimizirano] Prejel sem nenavadno visok račun za mobilne storitve. Kako naj pravilno ukrepam?",
        "required_keywords": ["reklamacija", "razčlenjen račun", "AKOS"],
        "forbidden_keywords": ["računa ni treba plačati nikoli"],
        "reference_answer": "Pojasni reklamacijo pri operaterju, zahtevo za razčlenitev in možnost postopka pri AKOS.",
        "source_topic": "neupravicen-racun",
        "source_url": "https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/neupravicen-racun"
    },
    {
        "category": "Inbox - gostovanje",
        "prompt": "[Anonimizirano] V EU gostovanju so mi zaračunali storitve kot izven EU. Kaj lahko storim?",
        "required_keywords": ["EU", "gostovanje", "reklamacija"],
        "forbidden_keywords": ["EU pravila ne veljajo"],
        "reference_answer": "Pojasni pravila gostovanja in postopek ugovora pri napačnem obračunu.",
        "source_topic": "o-gostovanju",
        "source_url": "https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/o-gostovanju"
    },
    {
        "category": "Inbox - menjava operaterja",
        "prompt": "[Anonimizirano] Pri prenosu številke je prišlo do zamude in dodatnih stroškov. Katere pravice imam?",
        "required_keywords": ["prenos številke", "zamuda", "pravice"],
        "forbidden_keywords": ["uporabnik nima nobene pravice"],
        "reference_answer": "Pojasni pravice ob zamudi in postopke reklamacije/spora.",
        "source_topic": "o-menjavi-operaterja-ali-spremembi-paketa",
        "source_url": "https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/o-menjavi-operaterja-ali-spremembi-paketa"
    },
    {
        "category": "Call-center - nedelovanje",
        "prompt": "[Anonimizirano] Internet mi več dni ne deluje, operater ne odpravi napake. Kako naj nadaljujem?",
        "required_keywords": ["prijava napake", "reklamacija", "AKOS"],
        "forbidden_keywords": ["nič se ne da storiti"],
        "reference_answer": "Predlaga dokumentirano prijavo, reklamacijo in nadaljnje postopke.",
        "source_topic": "storitev-ne-deluje-ali-ni-ustrezna",
        "source_url": "https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/storitev-ne-deluje-ali-ni-ustrezna"
    },
    {
        "category": "Call-center - postopek",
        "prompt": "[Anonimizirano] Operater je zavrnil mojo reklamacijo. Kako vložim predlog za rešitev spora?",
        "required_keywords": ["predlog", "rok", "AKOS"],
        "forbidden_keywords": ["tožba je obvezna"],
        "reference_answer": "Pojasni korake in roke za vložitev predloga pri AKOS.",
        "source_topic": "postopek-pred-akos",
        "source_url": "https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/postopek-pred-akos"
    },
    {
        "category": "Inbox - pošta",
        "prompt": "[Anonimizirano] Pošiljka ni bila dostavljena v običajnem roku. Kako lahko sprožim postopek?",
        "required_keywords": ["izvajalec poštnih storitev", "reklamacija", "AKOS"],
        "forbidden_keywords": ["AKOS neposredno dostavi pošiljko"],
        "reference_answer": "Pojasni reklamacijo pri izvajalcu in možnost spora pri AKOS.",
        "source_topic": "spori-med-operaterji",
        "source_url": "https://www.akos-rs.si/uporabniki-storitev/raziscite/spori-med-operaterji-oz-izvajalci-postnih-storitev-in-koncnimi-uporabniki"
    },
    {
        "category": "Call-center - signal",
        "prompt": "[Anonimizirano] Na stalnem naslovu nimam stabilnega mobilnega signala. Kako naj prijavim težavo?",
        "required_keywords": ["mobilni signal", "operater", "prijava"],
        "forbidden_keywords": ["AKOS zagotovi signal na lokaciji"],
        "reference_answer": "Usmeri na prijavo pri operaterju in nadaljnje korake pri nereševanju.",
        "source_topic": "storitev-ne-deluje-ali-ni-ustrezna",
        "source_url": "https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/storitev-ne-deluje-ali-ni-ustrezna"
    },
    {
        "category": "Inbox - administrativni stroški",
        "prompt": "[Anonimizirano] Operater je dodal administrativni strošek, ki ga ni bilo v pogodbi. Ali ga moram plačati?",
        "required_keywords": ["pogodba", "strošek", "reklamacija"],
        "forbidden_keywords": ["vsi dodatni stroški so dovoljeni"],
        "reference_answer": "Pojasni preverjanje pogodbenih podlag in postopek izpodbijanja stroška.",
        "source_topic": "neupravicen-racun",
        "source_url": "https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/neupravicen-racun"
    },
    {
        "category": "Call-center - center 080",
        "prompt": "[Anonimizirano] Želim preveriti, v kateri fazi je moj spor pri AKOS. Kam pokličem?",
        "required_keywords": ["080 2735", "klicni center"],
        "forbidden_keywords": ["pokličite policijo"],
        "reference_answer": "Navede kontakt klicnega centra in njegov namen.",
        "source_topic": "spori-med-operaterji",
        "source_url": "https://www.akos-rs.si/uporabniki-storitev/raziscite/spori-med-operaterji-oz-izvajalci-postnih-storitev-in-koncnimi-uporabniki"
    },
    {
        "category": "Inbox - novinarsko",
        "prompt": "[Anonimizirano - mediji] Kako AKOS javnost obvešča o spremembah regulacije?",
        "required_keywords": ["javna posvetovanja", "AKOS", "objava"],
        "forbidden_keywords": ["ne objavlja ničesar"],
        "reference_answer": "Pojasni javne objave, posvetovanja in uradna pojasnila.",
        "source_topic": "novinarska-vprasanja-in-odgovori",
        "source_url": "https://www.akos-rs.si/medijsko-sredisce/novinarska-vprasanja-in-odgovori"
    },
]

VARIANTS = [
    ("standard", "", ""),
    ("short", "Na kratko: ", " Odgovori v 2 stavkih."),
    ("formal", "Spoštovani, ", " Hvala."),
    ("frustrated", "[Stranka je nezadovoljna] ", " Prosim za konkreten korak."),
]


def main():
    out = {
        "dataset_name": "AKOS Internal Proxy Set (40)",
        "language": "sl",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "size": 40,
        "note": "To ni pravi interni inbox/call-center dump. Gre za anonimizirane proxy primere pripravljene iz javnih AKOS tematik.",
        "cases": [],
    }

    index = 1
    for base in BASE_CASES:
        for variant_name, prefix, suffix in VARIANTS:
            case = {
                "id": f"INTP-{index:03d}",
                "category": base["category"],
                "prompt": f"{prefix}{base['prompt']}{suffix}".strip(),
                "required_keywords": base["required_keywords"],
                "forbidden_keywords": base["forbidden_keywords"],
                "expected_abstain": False,
                "reference_answer": base["reference_answer"],
                "source_topic": base["source_topic"],
                "source_url": base["source_url"],
                "source_type": "proxy-internal",
                "variant_style": variant_name,
            }
            out["cases"].append(case)
            index += 1

    output_path = Path("akos_internal_proxy_cases_40.json")
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(out['cases'])} -> {output_path}")


if __name__ == "__main__":
    main()
