Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location "c:/Users/lukap/Documents/PUS/AKOS-ChatBot"
$python = "C:/Users/lukap/Documents/PUS/.venv/Scripts/python.exe"

& $python -u backend/evaluation/run_slovenian_llm_benchmark.py `
  --models llama3.2:3b `
  --cases backend/evaluation/akos_internal_proxy_cases_40.json `
  --max-cases 2 `
  --sample-strategy stratified `
  --sample-seed 42 `
  --strict-domain-mode `
  --timeout 420 `
  --csv-prefix demo_2cases_llama32
