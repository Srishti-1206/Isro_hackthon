import docker
import ollama

def get_router_telemetry(container_name, command):
    """Executes a vtysh command directly inside a running FRR container."""
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        # Run vtysh inside the target container
        exec_res = container.exec_run(f"vtysh -c '{command}'")
        return exec_res.output.decode('utf-8')
    except Exception as e:
        return f"Error gathering data from {container_name}: {str(e)}"

def ask_qwen_copilot(telemetry_data):
    """Feeds the live data to Qwen 3 for analysis."""
    prompt = f"""
    You are an expert Network Operations Center (NOC) Copilot analyzing a live corporate enterprise network.
    Review the following live 'show ip route' routing table output from the backbone provider router (p1):

    ```text
    {telemetry_data}
    ```

    Please perform the following tasks:
    1. Check if the OSPF dynamic routing protocol paths are healthy.
    2. Explicitly note if any expected connections (like dc-hub at 10.1.1.0/24 or branch-1 at 10.2.2.0/24) are missing from the routing table.
    3. Provide a clear, professional summary statement for the on-duty network engineering team.
    """
    
    print("🤖 Sending live telemetry data directly to Qwen 3...")
    response = ollama.chat(model='qwen3:8b', messages=[
        {
            'role': 'user',
            'content': prompt,
        },
    ])
    return response['message']['content']

if __name__ == "__main__":
    # Target our live provider container created by containerlab
    target_node = "clab-enterprise-noc-core-p1"
    telemetry_cmd = "show ip route"
    
    print(f"📡 Extracting live state metrics from {target_node}...")
    live_output = get_router_telemetry(target_node, telemetry_cmd)
    
    print("\n--- Live Router Output Captured ---")
    print(live_output)
    print("-----------------------------------\n")
    
    analysis = ask_qwen_copilot(live_output)
    print("\n========== QWEN 3 NOC COPILOT REPORT ==========")
    print(analysis)
    print("=================================================")
    