# Skupno poročilo: Primerjalna analiza (Benchmark) LLM modelov za slovenski jezik

Ta dokument združuje rezultate vseh testiranih jezikovnih modelov pri obravnavi slovenskih domen (AKOS primeri). Vključuje podatke o zmogljivosti (ocena, hitrost), nastavitvah izvajanja ter pregled transparentnosti učnih podatkov, kar je pomembno merilo pri uvajanju rešitev.

## 1. Zbirna tabela rezultatov

Modeli so razvrščeni od najvišje do najnižje povprečne ocene. Rezultati vključujejo tako modele zagnane znotraj HPC sistema kot modele klicane prek API-ja (kjer so časi odzivov seveda znatno nižji).

| Model | Status | Povpr. ocena | Povpr. čas (s) | Testi | Kritične napake | Hard-fail |
|---|---|---:|---:|---:|---:|---:|
| GaMS-Beta/GaMS-27B-Instruct-Nemotron | PASS | 4.02 | 30.71 | 120 | 0 | 0 |
| llama-3.3-70b-versatile | PASS | 3.99 | 1.78 | 120 | 0 | 0 |
| openai/gpt-oss-safeguard-20b | PASS | 3.97 | 2.05 | 120 | 1 | 0 |
| meta-llama/llama-4-scout-17b-16e-instruct | PASS | 3.97 | 1.40 | 120 | 1 | 0 |
| llama-3.1-8b-instant | PASS | 3.95 | 1.27 | 120 | 0 | 0 |
| qwen/qwen3-32b | PASS | 3.92 | 2.74 | 120 | 0 | 0 |
| CohereForAI/aya-expanse-8b | PASS | 3.88 | 18.23 | 120 | 0 | 0 |
| openai/gpt-oss-20b | FAIL | 3.76 | 1.71 | 120 | 4 | 0 |
| cjvt/GaMS-9B | FAIL | 3.42 | 5.96 | 120 | 7 | 0 |
| cjvt/GaMS-1B | FAIL | 2.79 | 5.30 | 120 | 35 | 0 |

---

## 2. Podatki o izvajanju in strojni opremi

Rezultati so bili pridobljeni v dveh zelo ločenih infrastrukturnih okoljih:

### A) Lokalno gostovanje na HPC (SLING Arnes)
Lokalno postavljeni in gostovani modeli (On-Premise), kar omogoča varovanje organizacijskih podatkov, saj ti ne zapustijo strežnika. Izvajali so se preko **vLLM** znotraj **Apptainer kontejnerja** (`docker://vllm/vllm-openai:latest`). Vsi uporabljajo *Localhost port-forwarding*.
*   **GaMS-27B:** `srun` particija z 1x H100 GPU (80GB), 120GB RAM, obdelava v `bfloat16`. Max length nastavljen na 4096.
*   **Aya-Expanse-8B:** 
    - **Strojna oprema:** Slurm HPC GPU vozlišče (`--gres=gpu:1`), dodeljeno vozlišče `wn221`.
    - **Zagon modela:** Apptainer okolje z `vLLM` in neposrednim prenosom modela iz omejenega skladišča z avtentikacijo (`--env HF_TOKEN="..."`).
    - **Konfiguracija:** `max_model_len` nastavljen na 4096, klican preko port-forwardinga na `localhost:8000`.
*   **GaMS-9B in GaMS-1B:** 1x GPU lokalne HPC infrastrukture.

### B) Zunanje API storitve (GroqCloud / ponudniki)
Naslednji modeli so bili testirani preko zmogljivih zunanjih API strežnikov opremljenih s specializiranimi čipi (LPU ipd.), zaradi česar dosegajo ekstremno hitre čase. V produkciji pomenijo iznos podatkov organizacije na zunanji server.
*   **qwen, gpt-oss, llama-3.1, llama-3.3, llama-4-scout:** Testirani preko API klicev (metrika kaže `api.groq.com`).

*Opomba: Vsi benchmarki (tako lokalni kot API) so vzorčili **120** primerov iz baze `akos_gold_eval_set_v2_2000.json`, z uporabo stratificiranega vzorčenja (seed: `42`), pod orkestracijo skripte `run_gams_benchmark.py`.*

---

## 3. Transparentnost učnih podatkov (Data Disclosure)

Po vprašanju razkrivanja podatkov, na katerih je model učen, obstajajo močne razlike med vrhunskimi modeli na lestvici.

### CohereForAI/aya-expanse-8b
*   **Transparentnost:** **Visoka (Instruction Data)**
*   **Pojasnilo:** Cohere For AI zagovarja odprto znanost. Čeprav bazični *pre-training* internetni korpus ("kaj" model ve o svetu) ni povsem javno dostopen dokument-po-dokumentu, pa je **celoten instruction-tuning dataset**, na katerem se je model poliral do vrhunskega asistenta (več kot 513 milijonov interakcij v 114 jezikih), popolnoma **odprtokoden in objavljen** na HuggingFace (`Aya Collection`).

### GaMS modeli (GaMS-27B, GaMS-9B itd.)
*   **Transparentnost:** **Srednje-Visoka (Za slovenski jezik)**
*   **Pojasnilo:** Sam arhitekturni temelj modela izhaja od komercialnih gigantov (npr. Google Gemma, Nemotron, Mistral), katerih bazični podatki so "Closed Data". Vseeno pa ljubljanski raziskovalci (CJVT) natančno sepišejo in javno **odprejo** vse lokalne slovenske korpuse (MaCoCu, Janes, specifični prevodi MMLU), ki so preoblikovali ameriški model v domorodnega govorca. 

### Llama (3.1 / 3.3 / Scout) in Qwen3
*   **Transparentnost:** **Nizka**
*   **Pojasnilo:** Ti modeli zastopajo koncept "Open Weights" (uteži za zagon so prosto dostopne). Podatkovni korpusi za učenje pa predstavljajo poslovno skrivnost in se jih **ne razkriva javnosti**. Na voljo so obsežna tehnična poročila, kjer je s tortnimi diagrami prikazano kakšno mešanico jezikov ali kode so ti modeli prebrali, dostopa do pravih virov pa se ne nudi.

### GPT modeli
*   **Transparentnost:** **Zaprto**
*   **Pojasnilo:** Gre za API-only storitve, ki uteži in podatkov ne posredujejo nikomur.
