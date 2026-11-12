"""Start the real API server, call a few endpoints, then stop it.

Usage: python scripts/smoke_server.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8765"

proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8765"],
                        cwd=ROOT / "backend", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    for _ in range(120):
        try:
            if httpx.get(f"{BASE}/api/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.5)
    else:
        raise SystemExit("server did not start")
    print("health :", httpx.get(f"{BASE}/api/health").json())
    print("docs   :", httpx.get(f"{BASE}/docs").status_code)
    for text in ["I have chest pain spreading to my left arm", "మాకు బాబుకి జ్వరం ఉంది", "मुझे सिरदर्द है"]:
        r = httpx.post(f"{BASE}/api/assess", json={"text": text}, timeout=30).json()
        print(f"assess : {text!r} -> status={r['status']} level={r['level']} "
              f"questions={[q['id'] for q in r['questions']]}")
    with httpx.Client(base_url=BASE) as c:
        c.post("/api/auth/register", json={"email": f"smoke{int(time.time())}@example.com", "password": "smoke-pass-1"})
        r = c.post("/api/assess", json={"text": "runny nose and sneezing, I am 25 years old", "save": True}).json()
        print("saved  :", r["level"], "| history items:", len(c.get("/api/history").json()))
    print("OK")
finally:
    proc.terminate()
    proc.wait(timeout=10)
