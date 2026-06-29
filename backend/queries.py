QUERIES = {
    "cpu": '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)',

    "memory": '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',

    "network_receive":
        'sum(rate(node_network_receive_bytes_total[1m]))',

    "network_transmit":
        'sum(rate(node_network_transmit_bytes_total[1m]))'
}