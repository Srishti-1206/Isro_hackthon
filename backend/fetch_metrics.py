import requests

PROMETHEUS_URL = "http://localhost:9090/api/v1/query"

query = 'sum(rate(node_network_receive_bytes_total[1m]))'

response = requests.get(
    PROMETHEUS_URL,
    params={"query": query}
)

data = response.json()

print(data)