def analyze_log(file):
    latency_count = 0
    packet_loss = 0
    errors = 0
    warnings = 0

    try:
        with open(file, "r") as f:
            for line in f:
                l = line.lower()

                # latency / ICMP / ping indicators
                if "icmp_seq" in l or "ttl=" in l or "time=" in l:
                    latency_count += 1

                # packet loss / unreachable
                if "100% packet loss" in l or "unreachable" in l or "timeout" in l:
                    packet_loss += 1

                # errors
                if "error" in l or "fail" in l or "exception" in l:
                    errors += 1

                # warnings (docker/containerlab logs often use this)
                if "warn" in l or "warning" in l:
                    warnings += 1

    except FileNotFoundError:
        print("Log file not found. Make sure sample.log exists in this folder.")
        return

    print("===== NETWORK REPORT =====")
    print("Latency events:", latency_count)
    print("Packet loss events:", packet_loss)
    print("Error events:", errors)
    print("Warnings:", warnings)

    # FINAL DECISION LOGIC 
    if packet_loss > 0:
        print("Network Status: UNSTABLE (Packet Loss Detected)")
    elif errors > 0:
        print("Network Status: DEGRADED (Errors Detected)")
    elif warnings > 5:
        print("Network Status: WARNING (High System Warnings)")
    elif latency_count > 10:
        print("Network Status: HIGH TRAFFIC (Latency Spike)")
    else:
        print("Network Status: HEALTHY")


analyze_log("sample.log")
