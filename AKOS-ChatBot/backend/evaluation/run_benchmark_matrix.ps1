Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location "c:/Users/lukap/Documents/PUS/AKOS-ChatBot"

$python = "C:/Users/lukap/Documents/PUS/.venv/Scripts/python.exe"
$script = "backend/evaluation/run_slovenian_llm_benchmark.py"
$gold = "backend/evaluation/akos_gold_eval_set_v2_2000.json"
$internalProxy = "backend/evaluation/akos_internal_proxy_cases_40.json"

function Get-InstalledOllamaModels {
	try {
		$resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 10
		$payload = $resp.Content | ConvertFrom-Json
		if ($null -eq $payload.models) {
			return @()
		}
		return @($payload.models | ForEach-Object { $_.name })
	}
	catch {
		Write-Warning "Ollama API ni dosegljiva na http://localhost:11434. Zaženi Ollama in poskusi znova."
		return @()
	}
}

function Resolve-AvailableModels {
	param(
		[string[]]$Requested,
		[string[]]$Installed
	)

	$available = @()
	foreach ($model in $Requested) {
		if ($Installed -contains $model) {
			$available += $model
		}
		else {
			Write-Warning "Model ni nameščen: $model"
		}
	}
	return $available
}

function Run-Stage {
	param(
		[string]$Title,
		[string[]]$RequestedModels,
		[string]$Cases,
		[int]$MaxCases,
		[string[]]$Installed,
		[bool]$UseSampling
	)

	Write-Host $Title
	$models = Resolve-AvailableModels -Requested $RequestedModels -Installed $Installed
	if ($models.Count -eq 0) {
		Write-Warning "Preskočeno: noben zahtevan model ni na voljo za ta korak."
		return
	}

	$args = @($script, "--models") + $models + @("--cases", $Cases, "--max-cases", "$MaxCases", "--strict-domain-mode")
	if ($UseSampling) {
		$args += @("--sample-strategy", "stratified", "--sample-seed", "42")
	}

	& $python @args
}

$installedModels = Get-InstalledOllamaModels
if ($installedModels.Count -eq 0) {
	throw "Ni najdenih nameščenih Ollama modelov. Namesti modele z 'ollama pull ...' in ponovi zagon."
}

Write-Host "Nameščeni modeli:" ($installedModels -join ", ")

Run-Stage -Title "[1/4] Smoke benchmark (120)" -RequestedModels @("llama3.1:8b", "gemma2:9b", "mistral-nemo:12b", "llama3.2:3b") -Cases $gold -MaxCases 120 -Installed $installedModels -UseSampling $true

Run-Stage -Title "[2/4] Candidate benchmark (400)" -RequestedModels @("llama3.1:8b", "gemma2:9b", "mistral-nemo:12b", "mistral:7b", "llama3.2:3b") -Cases $gold -MaxCases 400 -Installed $installedModels -UseSampling $true

Run-Stage -Title "[3/4] Internal-proxy benchmark (40)" -RequestedModels @("llama3.1:8b", "gemma2:9b", "mistral-nemo:12b", "llama3.2:3b") -Cases $internalProxy -MaxCases 0 -Installed $installedModels -UseSampling $false

Run-Stage -Title "[4/4] Release benchmark (2000)" -RequestedModels @("gemma2:9b", "mistral-nemo:12b", "gemma2:27b", "llama3.2:3b") -Cases $gold -MaxCases 0 -Installed $installedModels -UseSampling $false

Write-Host "Benchmark matrix completed."
