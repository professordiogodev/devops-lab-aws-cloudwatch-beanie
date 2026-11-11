"""PROVIDED. Pretends to be Beanie: once a minute it writes 60 JSON request lines to its log.
The share of failing requests comes from the SSM parameter /beanie-lab/error-rate (a percentage, 0 to 100)."""
import json
import random
import time

import boto3

ssm = boto3.client("ssm")
ROUTES = ["/api/menu", "/api/orders", "/api/orders/{id}"]


def error_rate():
    try:
        return float(ssm.get_parameter(Name="/beanie-lab/error-rate")["Parameter"]["Value"])
    except Exception:
        return 0.0


def lambda_handler(event, context):
    rate = error_rate()
    for _ in range(60):
        failed = random.random() * 100 < rate
        status = random.choice([500, 502, 503]) if failed else random.choice([200, 200, 200, 201])
        print(json.dumps({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "level": "error" if failed else "info",
            "msg": "request",
            "route": random.choice(ROUTES),
            "status": status,
            "duration_ms": random.randint(900, 4000) if failed else random.randint(20, 180),
        }))
    return {"emitted": 60, "error_rate": rate}
