from prometheus_client import Counter, Histogram
requests_total = Counter("requests_total", "Total requests", ["endpoint"])
latency = Histogram("latency_seconds", "Request latency", ["endpoint"])
