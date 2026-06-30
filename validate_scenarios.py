import argparse
import json
import time

from main_orchestrator import (
    build_incident_envelope,
    list_scenarios,
    load_playbook,
    load_scenario,
    parse_json_report,
    run_ai_decision_engine,
    validate_report_schema,
)


REQUIRED_SCENARIO_FIELDS = {
    "scenario_id": str,
    "fault_domain": str,
    "severity": str,
    "affected_nodes": list,
    "affected_interfaces": list,
    "affected_services": list,
    "telemetry": dict,
    "forecast": dict,
    "ground_truth": dict,
    "expected_remediation_type": str,
}


def validate_scenario_fixture(scenario):
    errors = []
    for field, expected_type in REQUIRED_SCENARIO_FIELDS.items():
        if field not in scenario:
            errors.append(f"missing field: {field}")
            continue
        if not isinstance(scenario[field], expected_type):
            errors.append(f"field '{field}' expected {expected_type}, got {type(scenario[field]).__name__}")

    playbook_id = scenario.get("expected_remediation_type")
    if playbook_id and not load_playbook(playbook_id):
        errors.append(f"missing playbook fixture: {playbook_id}")

    forecast = scenario.get("forecast", {})
    if "estimated_time_to_impact_seconds" not in forecast:
        errors.append("forecast missing estimated_time_to_impact_seconds")

    return errors


def run_fixture_validation():
    results = []
    for scenario_id in list_scenarios():
        scenario = load_scenario(scenario_id)
        errors = validate_scenario_fixture(scenario)
        results.append({
            "scenario_id": scenario_id,
            "status": "pass" if not errors else "fail",
            "errors": errors,
        })
    return results


def run_llm_validation(model):
    results = []
    for scenario_id in list_scenarios():
        scenario = load_scenario(scenario_id)
        envelope = build_incident_envelope("phase6_validation", scenario)
        start_time = time.time()
        raw_response = run_ai_decision_engine(envelope, model=model)
        duration = time.time() - start_time

        try:
            report = parse_json_report(raw_response)
            errors = validate_report_schema(report)
        except Exception as exc:
            report = {}
            errors = [f"invalid JSON response: {exc}"]

        expected_playbook = scenario["expected_remediation_type"]
        actual_playbook = report.get("recommended_action", {}).get("playbook_id")
        if actual_playbook != expected_playbook:
            errors.append(f"expected playbook {expected_playbook}, got {actual_playbook}")

        results.append({
            "scenario_id": scenario_id,
            "status": "pass" if not errors else "fail",
            "processing_seconds": round(duration, 2),
            "expected_playbook": expected_playbook,
            "actual_playbook": actual_playbook,
            "errors": errors,
        })
    return results


def parse_args():
    parser = argparse.ArgumentParser(description="Validate Phase 6 simulation fixtures and optional LLM outputs")
    parser.add_argument("--run-llm", action="store_true", help="Run every scenario through local Ollama/Qwen")
    parser.add_argument("--model", default="qwen3:8b", help="Local Ollama model tag")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    validation_results = run_llm_validation(args.model) if args.run_llm else run_fixture_validation()
    print(json.dumps(validation_results, indent=2))

    if any(result["status"] == "fail" for result in validation_results):
        raise SystemExit(1)
