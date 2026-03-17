# Poročilo testiranja LLM modelov za slovenščino (AKOS)

Datum: 2026-03-16

## 1) Kaj je bil cilj

Cilj je bil izbrati model, ki dobro odgovarja v slovenščini za AKOS scenarije (računi, gostovanje, menjava operaterja, postopki pri AKOS, novinarska vprašanja) in hkrati ne halucinira.

## 2) Lokalno okolje: poskusil sem, ampak ni šlo

Lokalno sem modela `gemma2:9b` in `mistral-nemo:12b` (ter tudi `llama3.1:8b`) testiral prek Ollama, ampak na tem računalniku to ni bilo stabilno.

Kaj se je dogajalo:
- benchmark se je sicer zagnal,
- pri generiranju odgovorov je pogosto prišlo do `Read timed out` po 420 sekundah,
- zato so primeri dobivali oceno 0.00 (ker ni bilo dejanskega odgovora),
- to je pokvarilo primerljivost rezultatov.


Zato je moj zaključek:
- za `gemma2:9b` in `mistral-nemo:12b` je za relevanten test treba uporabiti **Sling/HPC** (močnejši GPU),


## 3) Testiranje z Groq (podrobneje)

Ker lokalni testi za večje modele niso bili stabilni, sem primerjalni test izvedel prek Groq API.

Kako je teklo:
- backend v skripti je nastavljen na `--backend groq`,
- uporabljena je OpenAI-kompatibilna pot `https://api.groq.com/openai/v1/chat/completions`,
- dodan je retry/backoff za `429` in prehodne napake,
- test je bil izveden na 120 primerih, stratified, seed 42.

Modeli v Groq 120-testu:
- `qwen/qwen3-32b`
- `openai/gpt-oss-20b`
- `openai/gpt-oss-safeguard-20b`
- `llama-3.1-8b-instant`
- `meta-llama/llama-4-scout-17b-16e-instruct`
- `llama-3.3-70b-versatile`

Izhodi testa:
- `results/groq_requested_6models_120cases_summary.csv`
- `results/groq_requested_6models_120cases_cases.csv`
- `results/sl_benchmark_20260316_222339.md`

## 4) Kako sem generiral primere

Uporabil sem dva generatorja:

1. `backend/evaluation/generate_akos_gold_2000.py`
- iz seed dataseta (v1) naredi 2000 variant,
- menja slog prompta: `standard`, `short`, `detailed`, `journalist`, `frustrated`, `no_diacritics`, `colloquial`, `formal`,
- isto vsebino tako preverjam v različnih jezikovnih oblikah.

2. `backend/evaluation/generate_internal_proxy_40.py`
- ustvari 40 anonimiziranih “internih proxy” primerov,
- kategorije: račun, gostovanje, pošta, signal, menjava operaterja, postopek,
- vsak primer ima več slogov (npr. short/formal/frustrated).

### 4.1 Viri primerov (od kod so)

Primeri so pripravljeni iz javno dostopnih AKOS vsebin. Glavni viri so:

- https://www.akos-rs.si/pogosta-vprasanja-in-odgovori
- https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/postopek-pred-akos
- https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/o-gostovanju
- https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/storitev-ne-deluje-ali-ni-ustrezna
- https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/o-menjavi-operaterja-ali-spremembi-paketa
- https://www.akos-rs.si/pogosta-vprasanja-in-odgovori/neupravicen-racun
- https://www.akos-rs.si/uporabniki-storitev/raziscite/spori-med-operaterji-oz-izvajalci-postnih-storitev-in-koncnimi-uporabniki
- https://www.akos-rs.si/uporabniki-storitev/raziscite/koristni-nasveti-in-opozorila
- https://www.akos-rs.si/medijsko-sredisce/novinarska-vprasanja-in-odgovori

Zakaj se mi je to zdelo smiselno:

- ker je cilj asistenta odgovarjati na AKOS teme in vprašanja uporabnikov,
- ker so to uradne, javne in preverljive vsebine,
- ker lahko iz teh virov pripravim realne primere (računi, gostovanje, spori, postopki),
- ker se model tako ocenjuje na nalogah, ki so podobne dejanskim vprašanjem v praksi.

Nekaj konkretnih generiranih promptov:
- `GOLD2-0001`: "[Anonimizirano] Operater je zavrnil mojo reklamacijo. Kako lahko sprožim postopek pri AKOS?"
- `GOLD2-0002`: "Na kratko: Ali lahko operater zaračunava naročnino tudi, ko so storitve začasno izklopljene zaradi neplačila? Odgovori v 2 stavkih."
- `GOLD2-0003`: "Podrobno razloži: [Novinar] Kako AKOS sodeluje v javnih posvetovanjih ... Dodaj korake postopka."
- `INTP-001`: "[Anonimizirano] Prejel sem nenavadno visok račun za mobilne storitve. Kako naj pravilno ukrepam?"
- `INTP-004`: "[Stranka je nezadovoljna] ... Prosim za konkreten korak."

## 5) Kako se dodeli ocena

Vsak odgovor dobi 5 podocen (0–5):

1. `slovene_signal`
- preverja, ali je odgovor dejansko slovenski (šumniki + pogoste slovenske besede).

2. `required_coverage`
- ali odgovor pokrije ključne informacije (`required_keywords`).

3. `fluency`
- ali je odgovor berljiv in smiseln (stavki, dolžina, ponavljanje).

4. `abstention`
- pri primerih, kjer je pričakovana abstinenca (`expected_abstain=true`), model dobi točke samo, če ne ugiba in usmeri na uradne kanale.

5. `forbidden_control`
- kazen za prepovedane trditve (`forbidden_keywords`).

Končna ocena:

`overall = 0.25*slovene_signal + 0.30*required_coverage + 0.20*fluency + 0.15*abstention + 0.10*forbidden_control`

Status modela:
- `PASS`, če je povprečje `>= 3.8` in `hard_fail_count == 0`
- sicer `FAIL`

## 6) Rezultati 120-primernega testa

| Model | Status | Povpr. ocena | Povpr. čas (s) | Testi | Kritične napake | Hard-fail |
|---|---:|---:|---:|---:|---:|---:|
| qwen/qwen3-32b | PASS | 3.9153 | 2.7436 | 120 | 0 | 0 |
| openai/gpt-oss-20b | FAIL | 3.7632 | 1.7102 | 120 | 4 | 0 |
| openai/gpt-oss-safeguard-20b | PASS | 3.9675 | 2.0537 | 120 | 1 | 0 |
| llama-3.1-8b-instant | PASS | 3.9502 | 1.2742 | 120 | 0 | 0 |
| meta-llama/llama-4-scout-17b-16e-instruct | PASS | 3.9731 | 1.3968 | 120 | 1 | 0 |
| llama-3.3-70b-versatile | PASS | 3.9946 | 1.7757 | 120 | 0 | 0 |

## 7) Konkretni izpisi odgovorov modelov (slabši + boljši primer za vsak model)

Vir: `results/groq_requested_6models_120cases_examples.json`.

Vsi spodnji primeri so bili testirani na promptih, ki so bili pripravljeni iz zgornjih AKOS virov (FAQ, postopki, uporabniške pravice, medijska pojasnila).

### 7.1 qwen/qwen3-32b

Slabši (`GOLD2-0725`, 3.04):
- Prompt: "Za prijavo izpada sem dolgo čakal ... kako naj to uradno prijavim?"
- Odgovor (začetek):
  - "<think> Okay, the user is complaining about waiting a long time ..."
  - nato dolg angleški razmislek + deloma nepreverjena usmeritev.

Boljši (`GOLD2-1646`, 5.00):
- Prompt: "Kaj mora vsebovati predlog za rešitev spora, da bo popoln?"
- Odgovor (izsek):
  - "Predlog za rešitev spora mora vsebovati: osnovne podatke, opis spora, predlagano rešitev, dokumente, rok, podpis ..."

### 7.2 openai/gpt-oss-20b

Slabši (`GOLD2-0052`, 1.25):
- Prompt: novinarsko vprašanje o računu starega operaterja po menjavi.
- Odgovor:
  - prazen string (`""`).

Boljši (`GOLD2-1646`, 5.00):
- Odgovor (konkretno):
  - "Predlog za rešitev spora mora vsebovati: identifikacija strank, opis spora, pravna podlaga, zahteva po izidu, priloženi dokazi, podpis in datum."

### 7.3 openai/gpt-oss-safeguard-20b

Slabši (`GOLD2-0672`, 1.25):
- Prompt: "Ali lahko vlogo odda pooblaščenec?"
- Odgovor:
  - prazen string (`""`).

Boljši (`GOLD2-1646`, 5.00):
- Odgovor (izsek):
  - "Kaj mora vsebovati popoln predlog ... Identifikacija strank, opis spora, zakonska podlaga, zahtevek, dokazila, podpis in datum ..."

### 7.4 llama-3.1-8b-instant

Slabši (`GOLD2-1479`, 2.75):
- Prompt: previsok račun za prenos podatkov.
- Odgovor:
  - "Prosim za podrobnosti. Kateri operater uporabljate ..."

Boljši (`GOLD2-1679`, 4.99):
- Prompt: roki v postopku pred AKOS.
- Odgovor (izsek):
  - "V postopku pred AKOS se roki tečejo po naslednjih korakih: 1. Prijava ... 2. Preverjanje ..."

### 7.5 meta-llama/llama-4-scout-17b-16e-instruct

Slabši (`GOLD2-0616`, 0.00):
- Odgovor:
  - "NAPAKA: HTTPSConnectionPool(host='api.groq.com', port=443): Read timed out. (read timeout=120)"

Boljši (`GOLD2-0665`, 5.00):
- Odgovor:
  - "Med postopkom pri AKOS ni potrebno poravnati sporni račun ... lahko počakate na izid postopka ..."

### 7.6 llama-3.3-70b-versatile

Slabši (`GOLD2-0303`, 3.25):
- Prompt: operater ne zagotavlja dogovorjene hitrosti interneta.
- Odgovor (izsek):
  - "... lahko kontaktiraš podporo ... lahko kontaktiraš AKOS ..."
  - smer je pravilna, ampak odgovor je precej splošen.

Boljši (`GOLD2-0665`, 5.00):
- Odgovor (izsek):
  - "Med postopkom pri AKOS ni potrebno takoj poravnati sporni račun ... čakajte na odločbo komisije ..."

## 8) Primer konkretnega izračuna ocene

Primer: `openai/gpt-oss-20b`, `GOLD2-0052`

- podocene: `slovene=0.0`, `coverage=0.0`, `fluency=0.0`, `abstention=5.0`, `forbidden=5.0`

Izračun:

`0.25*0 + 0.30*0 + 0.20*0 + 0.15*5 + 0.10*5 = 1.25`

Končna ocena = `1.25`.

## 9) Odgovor na "Llama, Gemma, Mistral, GaMS"

- Llama: DA (testirano)
- Gemma: lokalno DA (`gemma2:9b`), v Groq testu ne
- Mistral: lokalno DA (`mistral-nemo:12b`), v Groq testu ne
- GaMS: ni razpoložljiv v trenutnem okolju

## 10) Končni zaključek

Če je cilj model blizu 30B:
- najboljši kandidat iz testa je `qwen/qwen3-32b`.

Če je cilj maksimalna kakovost ne glede na velikost:
- najboljši je `llama-3.3-70b-versatile`.

Za `gemma2:9b` in `mistral-nemo:12b` je moj jasen predlog:
- test naj se naredi na **Sling/HPC**, ker lokalno okolje ni dalo stabilnih rezultatov (timeouti),
- potem se rezultate neposredno primerja s tem 120-primerim Groq benchmarkom.
