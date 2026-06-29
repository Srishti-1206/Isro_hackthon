import requests
from queries import QUERIES

PROMETHEUS_URL = "http://localhost:9090/api/v1/query"


def fetch_metric(metric_name):
    query = QUERIES[metric_name]

    response = requests.get(
        PROMETHEUS_URL,
        params={"query": query}
    )

    data = response.json()

    return data["data"]["result"]


if __name__ == "__main__":
    for metric in ["cpu", "memory"]:
        print(f"\n===== {metric.upper()} =====")
        results = fetch_metric(metric)

        for result in results:
            instance = result["metric"].get("instance", "Unknown")
            value = float(result["value"][1])
            print(f"{instance}: {value:.2f}")