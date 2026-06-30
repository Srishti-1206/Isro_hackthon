# ISRO Hackathon NOC Copilot

Local predictive AIOps/NOC copilot for network incident simulation, telemetry analysis, and remediation playbook selection. The project combines scenario fixtures, Prometheus metric collection, Prophet-style forecasting, and a local Ollama LLM workflow.

## Features

- Tkinter desktop GUI for running local incident analysis.
- CLI orchestrator for live Prometheus telemetry with scenario fallback.
- Phase 6 simulation fixtures for common network failure modes.
- JSON playbooks for remediation recommendations.
- Scenario and optional LLM response validation.
- Docker Compose stack for Prometheus and node-exporter.

## Project Structure

```text
.
|-- backend/                 # Prometheus collection and prediction helpers
|-- configs/                 # Network/container configuration files
|-- data/                    # Sample CSV/log data
|-- playbooks/               # Remediation playbook fixtures
|-- prometheus/              # Prometheus configuration
|-- scenarios/               # Incident simulation fixtures
|-- analyzer.py              # Simple log analyzer
|-- gui_app.py               # Desktop GUI entry point
|-- main_orchestrator.py     # Main AI decision pipeline
|-- validate_scenarios.py    # Fixture and LLM validation
`-- docker-compose.yml       # Prometheus + node-exporter stack
```

## Requirements

- Python 3.10+
- Docker Desktop, if using Prometheus locally
- Ollama, if running AI analysis with the default local model
- Default Ollama model: `qwen3:8b`

Python packages used by the current scripts include:

```text
customtkinter
matplotlib
ollama
pandas
prophet
requests
```

## Quick Start

Install dependencies:

```powershell
pip install customtkinter matplotlib ollama pandas prophet requests
```

Pull the default Ollama model:

```powershell
ollama pull qwen3:8b
```

Run the GUI:

```powershell
python gui_app.py
```

Run the CLI orchestrator:

```powershell
python main_orchestrator.py --scenario buffer_exhaustion
```

List available scenarios:

```powershell
python main_orchestrator.py --list-scenarios
```

## Prometheus Stack

Start Prometheus and node-exporter:

```powershell
docker compose up -d
```

Prometheus will be available at:

```text
http://localhost:9090
```

If Prometheus is not reachable, `main_orchestrator.py` falls back to the selected simulation scenario.

## Validation

Validate scenario fixtures and playbook links:

```powershell
python validate_scenarios.py
```

Run validation through the local LLM:

```powershell
python validate_scenarios.py --run-llm --model qwen3:8b
```

## Utility Scripts

Analyze the sample log:

```powershell
python analyzer.py
```

Run backend metric collection:

```powershell
python backend/collector.py
```

Run CPU prediction from `backend/metrics.csv`:

```powershell
python backend/predict.py
```

## Notes

- Generated logs, metrics, Python cache files, virtual environments, local secrets, and Containerlab runtime outputs are ignored by Git.
- Files already tracked by Git remain tracked even if they now match `.gitignore`.
- Keep real credentials, private keys, and generated lab artifacts out of commits.
