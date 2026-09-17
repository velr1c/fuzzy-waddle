#!/usr/bin/env python3
"""AI Cook localhost kitchen: a thin wrapper around fuzzy-waddle studio capabilities."""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KITCHEN_OUT = ROOT / "ai-cook-for-ae" / "kitchen" / "out"
sys.path.insert(0, str(ROOT))
import run as studio  # noqa: E402
from director import direct  # noqa: E402


def capability_report():
    tools = studio.probe_tools()
    return {"tools": tools, "providers": {"local_tts": {"available": any(tools[x] for x in ("piper", "espeak-ng")), "status": "REAL/LOCAL/FREE" if any(tools[x] for x in ("piper", "espeak-ng")) else "MISSING"}, "local_llm": {"available": bool(tools.get("ollama")), "status": "REAL/LOCAL/FREE" if tools.get("ollama") else "MISSING"}, "ffmpeg": {"available": bool(tools.get("ffmpeg")), "status": "REAL/LOCAL/FREE" if tools.get("ffmpeg") else "MISSING"}}, "honesty": "Capabilities are probed; missing providers are never simulated silently."}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        if self.path == "/status": self._send(200, capability_report())
        else: self._send(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/cook": self._send(404, {"error": "not_found"}); return
        try:
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length).decode("utf-8"))
            prompt = str(payload.get("prompt", "")).strip()
            seconds = float(payload.get("seconds", 30)); style = str(payload.get("style", "auto"))
            if not prompt: raise ValueError("prompt is required")
            if style == "auto": style = "dark_sci_fi"
            project = KITCHEN_OUT / ("cook-" + str(abs(hash(prompt))))
            assets = project / "assets"; assets.mkdir(parents=True, exist_ok=True)
            caps = capability_report(); providers = {k: v.get("available", False) for k, v in caps["providers"].items()}
            plan, report = direct(prompt, seconds, style, caps, providers, assets)
            plan_path = project / "plan.json"; plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            self._send(200, {"plan_path": str(plan_path), "plan": plan, "report": {**report, "providers": caps["providers"]}})
        except Exception as exc:
            self._send(400, {"error": str(exc), "honesty": "No plan was produced."})

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    print("AI Cook kitchen on http://127.0.0.1:8765", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
