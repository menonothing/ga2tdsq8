import json
import sys
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

EMAIL = "24f2008930@ds.study.iitm.ac.in"   # <-- CHANGE THIS

app = FastAPI()
START = time.monotonic()           # when the app started

# The click-counter. Exposed as "http_requests_total".
REQUESTS = Counter("http_requests_total", "Total HTTP requests")

# The diary: keeps only the newest 1000 entries in memory.
LOGS = deque(maxlen=1000)


@app.middleware("http")
async def observe(request: Request, call_next):
    """Runs on EVERY request, before the endpoint's own code."""
    REQUESTS.inc()                                   # count it
    request_id = str(uuid.uuid4())
    started = time.monotonic()

    response = await call_next(request)              # run the real endpoint

    entry = {
        "level": "INFO",
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "request_id": request_id,
        "method": request.method,
        "status": response.status_code,
        "duration_ms": round((time.monotonic() - started) * 1000, 2),
    }
    LOGS.append(entry)                               # write in the diary
    print(json.dumps(entry), file=sys.stdout, flush=True)  # also print it
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/work")
def work(n: int = 1):
    n = max(0, min(n, 5_000_000))      # keep it sane
    total = 0
    for i in range(n):                 # "K units of work"
        total += i
    return {"email": EMAIL, "done": n}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": float(time.monotonic() - START)}


@app.get("/logs/tail")
def logs_tail(limit: int = 10):
    if limit <= 0:
        return []
    return list(LOGS)[-limit:]