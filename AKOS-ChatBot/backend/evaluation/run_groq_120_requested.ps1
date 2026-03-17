$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "../..")

if (-not $env:GROQ_API_KEY) {
    throw "GROQ_API_KEY ni nastavljen. Najprej nastavi: `$env:GROQ_API_KEY = '<ključ>'"
}

& "C:/Users/lukap/Documents/PUS/.venv/Scripts/python.exe" -u "backend/evaluation/run_slovenian_llm_benchmark.py" `
  --backend groq `
  --models "qwen/qwen3-32b" "openai/gpt-oss-20b" "openai/gpt-oss-safeguard-20b" "llama-3.1-8b-instant" "meta-llama/llama-4-scout-17b-16e-instruct" "llama-3.3-70b-versatile" `
  --cases "backend/evaluation/akos_gold_eval_set_v2_2000.json" `
  --max-cases 120 `
  --sample-strategy stratified `
  --sample-seed 42 `
  --strict-domain-mode `
  --timeout 120 `
  --max-retries 4 `
  --retry-backoff-sec 1.5 `
  --csv-prefix "groq_requested_6models_120cases"
