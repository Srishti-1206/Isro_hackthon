import csv
import os
import time
from datetime import datetime
from collector import fetch_metric

CSV_FILE = "backend/metrics.csv"

# Create the CSV file with headers if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "cpu", "memory", "network_receive"])

print("Starting metric collection... Press Ctrl+C to stop.\n")

try:
    while True:
        # Get current metrics
        cpu_data = fetch_metric("cpu")
        memory_data = fetch_metric("memory")
        network_data = fetch_metric("network_receive")

        # Extract values
        cpu = float(cpu_data[0]["value"][1])
        memory = float(memory_data[0]["value"][1])
        network_receive = float(network_data[0]["value"][1])

        # Save to CSV
        with open(CSV_FILE, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    round(cpu, 2),
    round(memory, 2),
    round(network_receive, 2)
  ])

        print(
    f"{datetime.now().strftime('%H:%M:%S')} | "
    f"CPU: {cpu:.2f}% | "
    f"Memory: {memory:.2f}% | "
    f"Network RX: {network_receive:.2f} B/s"
)

        # Wait 5 seconds
        time.sleep(5)

except KeyboardInterrupt:
    print("\nMetric collection stopped.")