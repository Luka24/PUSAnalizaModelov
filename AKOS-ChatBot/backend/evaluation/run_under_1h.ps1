Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location "c:/Users/lukap/Documents/PUS/AKOS-ChatBot"
$python = "C:/Users/lukap/Documents/PUS/.venv/Scripts/python.exe"

# Conservative profile intended to finish roughly within 1 hour on a modest machine.
& $python -u backend/evaluation/run_slovenian_llm_benchmark.py `
  --models llama3.1:8b gemma2:9b mistral-nemo:12b `
  --cases backend/evaluation/akos_internal_proxy_cases_40.json `
  --max-cases 6 `
  --sample-strategy stratified `
  --sample-seed 42 `
  --strict-domain-mode `
  --timeout 420 `
  --csv-prefix under_1h_6cases_3models
