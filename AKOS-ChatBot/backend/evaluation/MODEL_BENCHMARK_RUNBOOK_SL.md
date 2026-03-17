# Runbook: Preskus odprtokodnih LLM za slovenščino (AKOS)

## 1) Točno katere modele testirati (<=30B)

Priporočena matrika (po prioriteti):

### A. Obvezni kandidati
- `llama3.1:8b`
- `gemma2:9b`
- `mistral-nemo:12b`

### B. Dodatni kandidati
- `llama3.2:3b` (hiter lokalni baseline)
- `mistral:7b` (kompakten baseline)
- `gemma2:27b` (zgornja meja kakovosti; priporočeno HPC)

### C. GaMS
- Če obstaja javno dostopen model/uteži: testiraj `GaMS` varianto med 7B–13B.
- Če GaMS ni na voljo v Ollama, ga testiraj prek spletnega endpointa ali HF/vLLM okolja in rezultate primerjaj na istem datasetu.

## 2) Lokalno vs HPC

- Lokalno (šibkejši GPU/CPU): `llama3.2:3b`, `mistral:7b`, `llama3.1:8b`.
- HPC / zmogljiv stroj: `mistral-nemo:12b`, `gemma2:9b`, `gemma2:27b`, `GaMS`.

## 3) Namestitev modelov (Ollama)

```powershell
ollama pull llama3.2:3b
ollama pull mistral:7b
ollama pull llama3.1:8b
ollama pull gemma2:9b
ollama pull mistral-nemo:12b
ollama pull gemma2:27b
```

## 4) Benchmark profili

Lokacija skript:
- `backend/evaluation/run_slovenian_llm_benchmark.py`
- Dataset (glavni): `backend/evaluation/akos_gold_eval_set_v2_2000.json`
- Dataset (proxy-internal): `backend/evaluation/akos_internal_proxy_cases_40.json`

### Profil 1 — Smoke (hiter, 120 primerov)

```powershell
C:/Users/lukap/Documents/PUS/.venv/Scripts/python.exe backend/evaluation/run_slovenian_llm_benchmark.py --models llama3.1:8b gemma2:9b mistral-nemo:12b --cases backend/evaluation/akos_gold_eval_set_v2_2000.json --max-cases 120 --sample-strategy stratified --sample-seed 42 --strict-domain-mode
```

### Profil 2 — Kandidatni izbor (400 primerov)

```powershell
C:/Users/lukap/Documents/PUS/.venv/Scripts/python.exe backend/evaluation/run_slovenian_llm_benchmark.py --models llama3.1:8b gemma2:9b mistral-nemo:12b mistral:7b --cases backend/evaluation/akos_gold_eval_set_v2_2000.json --max-cases 400 --sample-strategy stratified --sample-seed 42 --strict-domain-mode
```

### Profil 3 — Release (2000 primerov)

```powershell
C:/Users/lukap/Documents/PUS/.venv/Scripts/python.exe backend/evaluation/run_slovenian_llm_benchmark.py --models gemma2:9b mistral-nemo:12b gemma2:27b --cases backend/evaluation/akos_gold_eval_set_v2_2000.json --max-cases 0 --strict-domain-mode
```

### Profil 4 — Realistični signal (proxy-internal 40)

```powershell
C:/Users/lukap/Documents/PUS/.venv/Scripts/python.exe backend/evaluation/run_slovenian_llm_benchmark.py --models llama3.1:8b gemma2:9b mistral-nemo:12b --cases backend/evaluation/akos_internal_proxy_cases_40.json --max-cases 0 --strict-domain-mode
```

## 5) Kriterij izbire modela

Model je **PASS**, če:
- nima hard-fail primerov,
- povprečna ocena >= 3.8,
- kategorija Abstention ni kritično slaba,
- latenca ustreza cilju (interaktivni odgovor v nekaj sekundah).

Priporočena končna odločitev:
1) `mistral-nemo:12b` ali `gemma2:9b` kot primarni,
2) `llama3.1:8b` kot cenejša alternativa,
3) `llama3.2:3b` kot fallback.

## 6) Predloga kratkega poročila

- Namen in okolje (lokalno/HPC)
- Testirani modeli in verzije
- Uporabljen dataset in velikost
- Povprečne ocene + hard-fail + latenca
- 3 dobri in 3 slabi primeri na top-2 modelih
- Končni predlog modela za uporabo
