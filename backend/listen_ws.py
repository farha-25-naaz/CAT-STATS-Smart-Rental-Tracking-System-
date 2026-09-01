"""Minimal WebSocket listener for manual demo/testing.

    python listen_ws.py            # connects to ws://localhost:8000/ws/live
    python listen_ws.py 20         # ...and auto-exits after 20 seconds

Prints each frame with a wall-clock timestamp and seconds since the previous
frame, so replay pacing is visible.
"""

import asyncio
import json
import sys
import time
from datetime import datetime

import websockets

URL = "ws://localhost:8000/ws/live"


async def main(run_seconds: float | None) -> None:
    async with websockets.connect(URL) as ws:
        print(f"[{datetime.now():%H:%M:%S}] connected {URL}")
        last = time.monotonic()
        stop_at = (time.monotonic() + run_seconds) if run_seconds else None
        while True:
            timeout = None if stop_at is None else max(0.1, stop_at - time.monotonic())
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            except asyncio.TimeoutError:
                print(f"[{datetime.now():%H:%M:%S}] done (timeout)")
                return
            now = time.monotonic()
            try:
                msg = json.loads(raw)
                event = msg.get("event", "?")
            except json.JSONDecodeError:
                msg, event = raw, "raw"
            print(f"[{datetime.now():%H:%M:%S}] (+{now - last:5.2f}s) {event:20} {msg}")
            last = now


if __name__ == "__main__":
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else None
    try:
        asyncio.run(main(secs))
    except KeyboardInterrupt:
        pass
