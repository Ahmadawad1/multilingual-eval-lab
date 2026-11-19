"""Seed the running local API. Safe to repeat; existing demo runs are reused."""

import json
from urllib.request import Request, urlopen

if __name__ == "__main__":
    request = Request(
        "http://127.0.0.1:8000/api/demo",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        print(json.dumps(json.load(response), indent=2))
