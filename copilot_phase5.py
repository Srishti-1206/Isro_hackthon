import json
import ollama

def run_phase5_copilot(telemetry_data, predictive_metrics):
    """
    Phase 5: Fuses live telemetry context and predictive inputs 
    into Qwen 3 using a structured RAG formatting template.
    """
    
    # This strict system prompt forces Qwen 3 to behave like a deterministic API rather than a chat bot
    system_instruction = """
    You are an expert enterprise AIOps Copilot decision engine. 
    You will be handed a combination of live network telemetry and predictive time-series model outputs.
    You must evaluate these inputs and return a response strictly following this JSON structure. 
    Do not include any introductions, conclusions, explanations, or markdown text formatting other than valid JSON.

    {
        "predicted_issue_type": "string",
        "confidence_score": 0.00-1.00,
        "probable_root_cause": "string",
        "affected_sites_and_services": ["site1", "service2"],
        "estimated_time_to_impact": "string"
    }
    """

    user_payload = f"""
    [ALERT: TELEMETRY INGESTION PIPELINE]
    
    CRITICAL LIVE TELEMETRY:
    {telemetry_data}
    
    PREDICTIVE INTERPOLATION METRICS:
    {predictive_metrics}
    
    Analyze the payload and output the structured JSON report now:
    """

    print("🧠 Injecting context into Qwen 3 via RAG pipeline...")
    
    response = ollama.chat(
        model='qwen3:8b', # Adjust to your local model tag if different (e.g., qwen3:30b)
        messages=[
            {'role': 'system', 'content': system_instruction},
            {'role': 'user', 'content': user_payload}
        ],
        options={'temperature': 0.0} # Absolute minimum temperature ensures zero hallucination/creativity
    )
    
    return response['message']['content']

if __name__ == "__main__":
    # Simulated RAG Context Data (Bridges the gap until Phase 3 automation is finished)
    mock_telemetry = (
        "Device: clab-enterprise-noc-core-dc-hub\n"
        "Interface: eth1 (Link to branch-1)\n"
        "Status: UP\n"
        "Metrics: Output queue utilization at 94%. Packet discard rate spiked to 4.2% over last 120 seconds."
    )
    
    mock_predictions = (
        "Model: Time-Series Linear Regression Engine\n"
        "Trend Analysis: Outbound traffic volume exhibiting exponential slope expansion (+220Mbps/min).\n"
        "Threshold breach forecast: Total buffer exhaustion expected in less than 6 minutes."
    )
    
    # Run the engine
    json_output = run_phase5_copilot(mock_telemetry, mock_predictions)
    
    print("\n========== PHASING 5 STRUCTURED CO-PILOT RESPONSE ==========")
    print(json_output)
    print("=============================================================")