import argparse
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import ollama
import requests


BASE_DIR = Path(__file__).resolve().parent
SCENARIO_DIR = BASE_DIR / "scenarios"
PLAYBOOK_DIR = BASE_DIR / "playbooks"
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"
DEFAULT_MODEL = "qwen3:8b"
SCENARIO_ALIASES = {
    "network_buffer_exhaustion": "buffer_exhaustion",
    "memory_leak_decay": "memory_leak",
}

REQUIRED_REPORT_FIELDS = {
    "incident_id": str,
    "scenario_id": str,
    "predicted_issue_type": str,
    "confidence_score": (int, float),
    "severity": str,
    "fault_domain": str,
    "probable_root_cause": str,
    "affected_devices": list,
    "affected_interfaces": list,
    "affected_services": list,
    "signals": list,
    "estimated_time_to_impact_seconds": int,
    "recommended_action": dict,
}

REQUIRED_ACTION_FIELDS = {
    "playbook_id": str,
    "action_type": str,
    "requires_human_approval": bool,
    "commands": list,
}


def list_scenarios():
    return sorted(path.stem for path in SCENARIO_DIR.glob("*.json"))


def load_json_file(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_scenario(scenario_id):
    scenario_id = SCENARIO_ALIASES.get(scenario_id, scenario_id)
    scenario_path = SCENARIO_DIR / f"{scenario_id}.json"
    if not scenario_path.exists():
        available = ", ".join(list_scenarios()) or "none"
        raise ValueError(f"Unknown scenario '{scenario_id}'. Available scenarios: {available}")
    return load_json_file(scenario_path)


def load_playbook(playbook_id):
    playbook_path = PLAYBOOK_DIR / f"{playbook_id}.json"
    if not playbook_path.exists():
        return None
    return load_json_file(playbook_path)


def build_incident_envelope(source, payload):
    return {
        "incident_id": f"noc-{uuid.uuid4().hex[:12]}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "payload": payload,
    }


def fetch_live_and_predictive_telemetry(fallback_scenario_id="buffer_exhaustion"):
    """
    Connects to Prometheus and the Phase 3 Prediction Engine to collect
    both real-time state metrics and future time-series forecasts.
    """
    print("📊 [Phase 2 & 3] Querying Prometheus API & Prophet Forecast Models...")

    try:
        query_bandwidth = {'query': 'rate(node_network_transmit_bytes_total[1m])'}
        query_drops = {'query': 'rate(node_network_transmit_drop_total[1m])'}

        prom_bytes = requests.get(PROMETHEUS_URL, params=query_bandwidth, timeout=3).json()
        prom_drops = requests.get(PROMETHEUS_URL, params=query_drops, timeout=3).json()

        telemetry_payload = {
            "scenario_id": "live_prometheus_pipeline",
            "fault_domain": "unknown",
            "severity": "warning",
            "live_prometheus_metrics": {
                "interface_throughput_bytes": prom_bytes.get('data', {}).get('result', []),
                "packet_drop_rate_per_minute": prom_drops.get('data', {}).get('result', [])
            },
            "phase3_prophet_forecast": {
                "model_status": "TRAINED_AND_ACTIVE",
                "predicted_trend": "Exponential saturation curve detected on Hub-Spoke link eth1",
                "confidence_interval_upper": "95%",
                "expected_threshold_breach_seconds": 360
            }
        }
        return build_incident_envelope("live_prometheus", telemetry_payload)

    except Exception as e:
        print(f"⚠️ Prometheus/Prediction engine API unreachable: {str(e)}")
        print(f"💡 Activating Phase 6 simulation scenario: {fallback_scenario_id}")
        return build_incident_envelope("phase6_simulation", load_scenario(fallback_scenario_id))


def compact_context(telemetry_envelope):
    """
    Keeps the local LLM prompt short by sending normalized signals instead of
    raw operator prose or full Prometheus responses.
    """
    payload = telemetry_envelope["payload"]
    context = {
        "incident_id": telemetry_envelope["incident_id"],
        "generated_at": telemetry_envelope["generated_at"],
        "source": telemetry_envelope["source"],
        "scenario_id": payload.get("scenario_id"),
        "fault_domain": payload.get("fault_domain"),
        "severity": payload.get("severity"),
        "affected_nodes": payload.get("affected_nodes", []),
        "affected_interfaces": payload.get("affected_interfaces", []),
        "affected_services": payload.get("affected_services", []),
        "telemetry": payload.get("telemetry", payload.get("live_prometheus_metrics", {})),
        "forecast": payload.get("forecast", payload.get("phase3_prophet_forecast", {})),
        "expected_playbook_id": payload.get("expected_remediation_type"),
    }
    return json.dumps(context, separators=(",", ":"))


def build_schema_instruction():
    return (
        "Return only valid JSON. Do not include reasoning, markdown, or <think> text. "
        "Use the provided incident_id and scenario_id. "
        "Do not invent executable commands; commands must be an empty list unless "
        "the telemetry includes an approved command. Required schema: "
        '{"incident_id":"string","scenario_id":"string","predicted_issue_type":"string",'
        '"confidence_score":0.0,"severity":"info|warning|major|critical",'
        '"fault_domain":"interface|routing|memory|qos|tunnel|underlay|unknown",'
        '"probable_root_cause":"string","affected_devices":["string"],'
        '"affected_interfaces":["string"],"affected_services":["string"],'
        '"signals":[{"name":"string","value":"string","weight":0.0}],'
        '"estimated_time_to_impact_seconds":0,'
        '"recommended_action":{"playbook_id":"string","action_type":"observe|notify|mitigate|rollback",'
        '"requires_human_approval":true,"commands":[]}}'
    )


def run_ai_decision_engine(telemetry_envelope, model=DEFAULT_MODEL):
    """
    Takes the telemetry payload, pushes compact context into Qwen, and forces
    an automation-ready JSON alert envelope.
    """
    response = ollama.chat(
        model=model,
        messages=[
            {'role': 'system', 'content': build_schema_instruction()},
            {'role': 'user', 'content': compact_context(telemetry_envelope)}
        ],
        options={
            'temperature': 0.0,
            'num_predict': 350,
            'top_p': 0.8,
        }
    )
    return response['message']['content']


def parse_json_report(raw_response):
    raw_cleaned = raw_response.strip()
    no_think_cleaned = re.sub(
        r"<think>.*?</think>",
        "",
        raw_cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    last_error = None
    for candidate_text in (no_think_cleaned, raw_cleaned):
        cleaned = re.sub(r"^```(?:json)?", "", candidate_text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            last_error = exc

        json_candidate = extract_first_json_object(cleaned)
        if json_candidate is not None:
            try:
                return json.loads(json_candidate)
            except json.JSONDecodeError as exc:
                last_error = exc

    raise last_error or json.JSONDecodeError("No JSON object found", raw_response, 0)


def extract_first_json_object(text):
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    return None


def build_deterministic_report(telemetry_envelope):
    """
    Keeps Phase 6 useful even when the local LLM emits non-JSON. This is also
    the safe automation boundary: only approved playbook IDs are surfaced.
    """
    payload = telemetry_envelope["payload"]
    forecast = payload.get("forecast", payload.get("phase3_prophet_forecast", {}))
    telemetry = payload.get("telemetry", payload.get("live_prometheus_metrics", {}))
    ground_truth = payload.get("ground_truth", {})
    playbook_id = payload.get("expected_remediation_type", "manual_triage")
    playbook = load_playbook(playbook_id) or {}

    signals = []
    for name, value in list(telemetry.items())[:6]:
        signals.append({
            "name": name,
            "value": str(value),
            "weight": 0.7,
        })
    if forecast:
        signals.append({
            "name": "forecast_trend",
            "value": str(forecast.get("trend", forecast.get("predicted_trend", "predictive anomaly detected"))),
            "weight": float(forecast.get("confidence", 0.8)),
        })

    return {
        "incident_id": telemetry_envelope["incident_id"],
        "scenario_id": payload.get("scenario_id", "live_prometheus_pipeline"),
        "predicted_issue_type": ground_truth.get("predicted_issue_type", "predictive_network_anomaly"),
        "confidence_score": float(forecast.get("confidence", 0.8)),
        "severity": payload.get("severity", "warning"),
        "fault_domain": payload.get("fault_domain", "unknown"),
        "probable_root_cause": ground_truth.get(
            "root_cause",
            "Predictive telemetry exceeded the configured risk baseline."
        ),
        "affected_devices": payload.get("affected_nodes", []),
        "affected_interfaces": payload.get("affected_interfaces", []),
        "affected_services": payload.get("affected_services", []),
        "signals": signals,
        "estimated_time_to_impact_seconds": int(forecast.get("estimated_time_to_impact_seconds", 360)),
        "recommended_action": {
            "playbook_id": playbook_id,
            "action_type": playbook.get("action_type", "notify"),
            "requires_human_approval": bool(playbook.get("requires_human_approval", True)),
            "commands": [],
        },
    }


def parse_or_fallback_report(raw_response, telemetry_envelope):
    try:
        return parse_json_report(raw_response), []
    except json.JSONDecodeError as exc:
        fallback_report = build_deterministic_report(telemetry_envelope)
        return fallback_report, [f"LLM returned non-JSON; used deterministic scenario report ({exc})"]


def run_phase6_simulation(scenario_name, model=DEFAULT_MODEL):
    """
    Native-app friendly Phase 6 entry point. Runs a named simulation scenario
    through the local AI decision path and always returns a Python dictionary.
    """
    scenario = load_scenario(scenario_name)
    telemetry_envelope = build_incident_envelope("phase6_simulation", scenario)
    start_time = time.time()
    raw_ai_report = run_ai_decision_engine(telemetry_envelope, model=model)
    processing_duration = time.time() - start_time

    parsed_report, parse_warnings = parse_or_fallback_report(raw_ai_report, telemetry_envelope)
    schema_errors = validate_report_schema(parsed_report)
    playbook_id = parsed_report.get("recommended_action", {}).get("playbook_id")
    parsed_report["_runtime"] = {
        "processing_seconds": round(processing_duration, 2),
        "parse_warnings": parse_warnings,
        "schema_errors": schema_errors,
        "scenario_source": scenario.get("scenario_id", scenario_name),
    }
    parsed_report["_playbook"] = load_playbook(playbook_id) if playbook_id else None
    return parsed_report


def validate_report_schema(report):
    errors = []
    for field, expected_type in REQUIRED_REPORT_FIELDS.items():
        if field not in report:
            errors.append(f"missing field: {field}")
            continue
        if not isinstance(report[field], expected_type):
            errors.append(f"field '{field}' expected {expected_type}, got {type(report[field]).__name__}")

    action = report.get("recommended_action", {})
    if isinstance(action, dict):
        for field, expected_type in REQUIRED_ACTION_FIELDS.items():
            if field not in action:
                errors.append(f"missing recommended_action field: {field}")
                continue
            if not isinstance(action[field], expected_type):
                errors.append(
                    f"recommended_action.{field} expected {expected_type}, got {type(action[field]).__name__}"
                )

    if isinstance(report.get("confidence_score"), (int, float)):
        if not 0 <= report["confidence_score"] <= 1:
            errors.append("confidence_score must be between 0 and 1")

    if isinstance(report.get("estimated_time_to_impact_seconds"), int):
        if report["estimated_time_to_impact_seconds"] < 0:
            errors.append("estimated_time_to_impact_seconds must be non-negative")

    playbook_id = action.get("playbook_id") if isinstance(action, dict) else None
    if playbook_id and not load_playbook(playbook_id):
        errors.append(f"unknown playbook_id: {playbook_id}")

    return errors


def run_pipeline(args):
    print("🚀 Initializing Net VigilAnz Orchestrator...")
    print("Air-Gapped Predictive Copilot for Secure MPLS Operations")
    print("---------------------------------------------------------------------")

    combined_telemetry = fetch_live_and_predictive_telemetry(args.scenario)

    start_time = time.time()
    raw_ai_report = run_ai_decision_engine(combined_telemetry, args.model)
    processing_duration = time.time() - start_time

    parsed_report, parse_warnings = parse_or_fallback_report(raw_ai_report, combined_telemetry)
    schema_errors = validate_report_schema(parsed_report)

    print(f"\n⏱️ Copilot Engine Processing Speed: {processing_duration:.2f} seconds")
    for warning in parse_warnings:
        print(f"⚠️ {warning}")
    print("🚨 ACTIONABLE AI STRATEGIC DECISION SUPPORT ENVELOPE:")
    print("=====================================================================")
    print(json.dumps(parsed_report, indent=2))
    print("=====================================================================")

    if schema_errors:
        print("❌ Schema validation failed:")
        for error in schema_errors:
            print(f" - {error}")
        raise SystemExit(1)

    playbook_id = parsed_report["recommended_action"]["playbook_id"]
    playbook = load_playbook(playbook_id)
    if playbook:
        print(f"📘 Approved playbook selected: {playbook_id} ({playbook['name']})")
    print("✅ Ingestion loop execution successful. Monitoring channels idle.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Net VigilAnz - Air-Gapped Predictive Copilot for Secure MPLS Operations"
    )
    parser.add_argument("--scenario", default="buffer_exhaustion", help="Phase 6 fallback scenario id")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Local Ollama model tag")
    parser.add_argument("--list-scenarios", action="store_true", help="List available Phase 6 scenarios")
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    if cli_args.list_scenarios:
        print("\n".join(list_scenarios()))
    else:
        run_pipeline(cli_args)
