# AKOS Gold Eval Set v1 – opombe

## Kaj je to

Primarni dataset je `akos_gold_eval_set_v2_2000.json` (2000 primerov).

Za celoten operativni postopek uporabi:
- `MODEL_BENCHMARK_RUNBOOK_SL.md`
- `run_benchmark_matrix.ps1`

`akos_gold_eval_set_v1.json` je začetni seed "gold" eval nabor s 40 anonimiziranimi vprašanji v slovenščini za domeno AKOS.

## Kako je bil sestavljen

Nabor je bil pripravljen iz javno dostopnih vsebin AKOS:
- Pogosta vprašanja in odgovori,
- Reševanje sporov uporabnikov,
- Koristni nasveti in opozorila,
- Novinarska vprašanja in odgovori.

Gre za **public-proxy** različico "realnih" vprašanj, ker dejanski inbox/call-center zapisi niso javni. V2 (2000) je generiran iz teh seed primerov z različnimi realističnimi slogovnimi variacijami.

## Zakaj je primeren

- pokrije glavne tokove uporabniških vprašanj (računi, nedelovanje, menjava operaterja, gostovanje),
- vključuje regulatorni in javno-komunikacijski kontekst,
- ohranja anonimizacijo in se izogne obdelavi osebnih podatkov.

## Kako ga uporabljati

Primer zagona:

```bash
python run_slovenian_llm_benchmark.py --cases akos_gold_eval_set_v2_2000.json --models llama3.1:8b mistral-nemo:12b-instruct gemma2:9b --strict-domain-mode --temperature 0.2
```

Priporočeni profili izvajanja:

- **Smoke test (hiter):**
```bash
python run_slovenian_llm_benchmark.py --max-cases 120 --sample-strategy stratified --sample-seed 42 --models llama3.1:8b --strict-domain-mode
```

- **Primerjava kandidatov:**
```bash
python run_slovenian_llm_benchmark.py --max-cases 400 --sample-strategy stratified --sample-seed 42 --models llama3.1:8b mistral-nemo:12b-instruct gemma2:9b --strict-domain-mode
```

- **Release benchmark (polni):**
```bash
python run_slovenian_llm_benchmark.py --max-cases 0 --models mistral-nemo:12b-instruct gemma2:9b --strict-domain-mode
```

## Kaj dodati v v2 (priporočilo)

Za produkcijski nivo kakovosti dodajte 30–50 **internih anonimiziranih** primerov:
- iz e-poštnega inboxa,
- iz klicnega centra,
- iz novinarskih zahtevkov.

Za vsak primer dodajte:
- `prompt`,
- `reference_answer` (odobren s strani vsebinske ekipe),
- `required_keywords`, `forbidden_keywords`,
- kategorijo (npr. potrošnik, spor, mediji, digitalne storitve).

Priporočeno razmerje končnega gold seta:
- 60% uporabniki storitev,
- 25% regulatorna/pravna pojasnila,
- 15% novinarska vprašanja.
