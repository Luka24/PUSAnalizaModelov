$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "../..")

if (-not $env:GROQ_API_KEY) {
    throw "GROQ_API_KEY ni nastavljen. Najprej nastavi: `$env:GROQ_API_KEY = '<ključ>'"
}

& "C:/Users/lukap/Documents/PUS/.venv/Scripts/python.exe" -u "backend/evaluation/run_slovenian_llm_benchmark.py" `
  --backend groq `
  --models "qwen/qwen3-32b" "openai/gpt-oss-20b" `
  --cases "backend/evaluation/akos_internal_proxy_cases_40.json" `
  --max-cases 20 `
  --sample-strategy stratified `
  --sample-seed 42 `
  --strict-domain-mode `
  --timeout 120 `
  --csv-prefix "groq_near30_20cases"
