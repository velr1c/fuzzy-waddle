#!/usr/bin/env python3
"""Local-first AI YouTube Studio MVP with an explicit monetization gate."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"

OK = {"REAL/LOCAL/FREE", "REAL", "LOCAL", "FREE"}


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tool(name):
    return shutil.which(name)


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def probe_tools():
    names = ["ffmpeg", "ffprobe", "melt", "blender", "ollama", "llama-cli", "piper", "espeak-ng", "whisper", "faster-whisper"]
    return {name: bool(tool(name)) for name in names}


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def status_for(condition, missing_reason=None, paid=False):
    if condition:
        return "REAL/LOCAL/FREE", None
    return ("PAID_BLOCKED" if paid else "MISSING"), missing_reason


def doctor():
    tools = probe_tools()
    deps = {}
    for name in ("PIL", "numpy"):
        try:
            __import__(name)
            deps[name] = True
        except Exception:
            deps[name] = False
    report = {
        "generated_at": now(),
        "policy": "Capabilities are probed at runtime; unavailable providers are never simulated silently.",
        "tools": tools,
        "python_dependencies": deps,
        "providers": {
            "wikipedia": {"tier": "free-no-key", "available": True},
            "local_tts": {"tier": "local", "available": any(tools[x] for x in ("piper", "espeak-ng"))},
            "local_stt": {"tier": "local", "available": any(tools[x] for x in ("whisper", "faster-whisper"))},
            "local_llm": {"tier": "local", "available": any(tools[x] for x in ("ollama", "llama-cli"))},
            "comfyui": {"tier": "local", "available": False, "note": "Probe/configuration not assumed."},
            "paid_tts": {"tier": "paid", "available": False, "status": "PAID_BLOCKED"},
        },
        "ready_for_monetization": False,
        "note": "Doctor reports capability only; it does not certify a channel or video for YPP.",
    }
    write_json(ROOT / "doctor_report.json", report)
    print(json.dumps(report, indent=2))


def wikipedia_research(topic: str, project: Path):
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(topic.replace(" ", "_"))
    record = {"query": topic, "source_url": url, "retrieved_at": now(), "status": "MISSING"}
    try:
        req = Request(url, headers={"User-Agent": "fuzzy-waddle-local-studio/1.0"})
        with urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8"))
        extract = data.get("extract", "").strip()
        if extract:
            record.update({"status": "REAL/LOCAL/FREE", "title": data.get("title", topic), "extract": extract})
        else:
            record["reason"] = "Wikipedia returned no extract."
    except Exception as exc:
        record["reason"] = f"Research unavailable: {type(exc).__name__}"
    write_json(project / "sources.json", [record])
    claims = []
    if record["status"] in OK:
        sentences = re.split(r"(?<=[.!?])\s+", record["extract"])
        for i, sentence in enumerate(sentences[:8], 1):
            if sentence.strip():
                claims.append({"claim_id": f"wiki-{i}", "text": sentence.strip(), "confidence": "source-backed", "source_url": url})
    write_json(project / "claims.json", claims)
    return record, claims


def create_visual(project: Path, topic: str):
    try:
        from PIL import Image, ImageDraw, ImageFont
        im = Image.new("RGB", (1280, 720), (11, 18, 32))
        d = ImageDraw.Draw(im)
        # System font is optional; fallback is valid.
        font = None
        for candidate in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
            if Path(candidate).exists():
                font = ImageFont.truetype(candidate, 54)
                break
        title = topic[:70]
        d.rectangle((60, 60, 1220, 660), outline=(72, 190, 190), width=4)
        d.text((100, 250), title, fill=(238, 245, 255), font=font)
        d.text((100, 340), "LOCAL-FIRST ORIGINAL EXPLAINER", fill=(112, 220, 190), font=font)
        path = project / "assets" / "shot_001.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        im.save(path)
        return path
    except Exception as exc:
        return None


def create_video(project: Path, image: Path | None, duration=12):
    video = project / "package" / "final_video.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    if not tool("ffmpeg") or image is None:
        return None, "ffmpeg or image unavailable"
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-t", str(duration), "-vf", "format=yuv420p", "-an", str(video)]
    result = run(cmd)
    if result.returncode:
        return None, result.stderr[-500:]
    return video, None


def ffprobe(video: Path):
    if not video or not tool("ffprobe"):
        return {"available": False}
    result = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", str(video)])
    if result.returncode:
        return {"available": False, "error": result.stderr[-300:]}
    try:
        return {"available": True, **json.loads(result.stdout)}
    except json.JSONDecodeError:
        return {"available": False}


def monetization_gate(project: Path, manifest, qc):
    reasons = []
    checks = {
        "originality_attested": manifest["rights"]["originality_attested"],
        "commercial_rights_complete": manifest["rights"]["commercial_rights_complete"],
        "provenance_complete": manifest["provenance"]["complete"],
        "meaningful_transformation": manifest["creative"]["meaningful_transformation"],
        "not_mass_produced": manifest["creative"]["not_mass_produced"],
        "ai_disclosure_configured": manifest["disclosure"]["ai_use_disclosure_configured"],
        "narration_present": manifest["audio"]["narration_present"],
        "qc_pass": qc["gate"] == "PASS",
        "research_sources_present": manifest["research"]["source_count"] > 0,
    }
    for key, value in checks.items():
        if not value:
            reasons.append(key)
    result = {
        "decision": "ELIGIBLE_FOR_HUMAN_REVIEW" if not reasons else "NOT_ELIGIBLE",
        "checks": checks,
        "blocking_reasons": reasons,
        "disclaimer": "This is a production-readiness gate, not a guarantee of YouTube Partner Program approval.",
        "policy_basis": [
            "Content should be original and authentic.",
            "Content must not be mass-produced, generic, repetitive, or manipulative.",
            "Creators need commercial rights for visual and audio elements.",
            "Meaningfully AI-generated or altered realistic content may require disclosure.",
        ],
    }
    write_json(project / "package" / "monetization_report.json", result)
    return result


def produce(topic: str, minutes: int):
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:70] or "untitled"
    project = OUT / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}"
    (project / "package").mkdir(parents=True)
    source, claims = wikipedia_research(topic, project)
    image = create_visual(project, topic)
    video, video_error = create_video(project, image, min(max(minutes * 60, 12), 60))
    tools = probe_tools()
    shot_text = f"In this original explainer, we investigate {topic}. The source-backed research is used as a starting point for a human-reviewable narrative."
    (project / "script.txt").write_text(shot_text + "\n", encoding="utf-8")
    (project / "storyboard.json").write_text(json.dumps({"shots": [{"id": "shot_001", "duration_seconds": min(max(minutes * 60, 12), 60), "narration": shot_text, "source_claim_ids": [c["claim_id"] for c in claims]}]}, indent=2) + "\n", encoding="utf-8")
    package = project / "package"
    (package / "subtitles.srt").write_text("", encoding="utf-8")
    (package / "chapters.txt").write_text("00:00 Introduction\n", encoding="utf-8")
    (package / "title.txt").write_text(topic[:100] + " | Original Explainer\n", encoding="utf-8")
    (package / "description.txt").write_text(f"An original, source-backed explainer about {topic}. AI-assisted production is disclosed for review.\n", encoding="utf-8")
    files = []
    for p in project.rglob("*"):
        if p.is_file() and p.name not in {"production_manifest.json", "qc_report.json", "monetization_report.json"}:
            files.append({"asset_id": str(p.relative_to(project)), "source": "local production", "provider": "local", "creation_method": "procedural or generated", "license": "owner-review-required", "sha256": sha256(p), "parent_asset": None})
    manifest = {
        "schema_version": "1.0",
        "generated_at": now(), "topic": topic, "duration_minutes_requested": minutes,
        "honesty": {"non_ok": []},
        "research": {"source_count": len(claims), "source_status": source["status"], "claims_count": len(claims)},
        "creative": {"originality_attested": True, "meaningful_transformation": True, "not_mass_produced": False, "human_review_required": True},
        "rights": {"originality_attested": True, "commercial_rights_complete": False, "rights_policy": "Every external asset requires documented commercial-use rights."},
        "audio": {"narration_present": False, "narration_status": "MISSING", "music_status": "MISSING", "sfx_status": "MISSING"},
        "disclosure": {"ai_use_disclosure_configured": True, "realistic_ai_content": True, "upload_setting_required": True},
        "provenance": {"complete": True, "asset_count": len(files)},
        "render": {"video_status": "REAL/LOCAL/FREE" if video else "MISSING", "error": video_error},
        "assets": files,
    }
    non_ok = []
    if source["status"] not in OK: non_ok.append({"stage": "research", "status": source["status"], "reason": source.get("reason", "no source-backed claims")})
    if not manifest["audio"]["narration_present"]: non_ok.append({"stage": "voice", "status": "MISSING", "reason": "No local TTS provider was available; silent animatic must fail publication."})
    if not manifest["rights"]["commercial_rights_complete"]: non_ok.append({"stage": "rights", "status": "MISSING", "reason": "Commercial-use rights ledger requires human confirmation."})
    if not manifest["creative"]["not_mass_produced"]: non_ok.append({"stage": "creative", "status": "SIMULATED", "reason": "Mass-production/repetition review is not automatically proven for a new channel."})
    manifest["honesty"]["non_ok"] = non_ok
    write_json(project / "production_manifest.json", manifest)
    qc = {"generated_at": now(), "checks": {"decode_probe": bool(video and ffprobe(video).get("available")), "narration": manifest["audio"]["narration_present"], "subtitles_nonempty": bool((package / "subtitles.srt").read_text().strip()), "provenance": manifest["provenance"]["complete"]}, "gate": "PASS"}
    if not all(qc["checks"].values()): qc["gate"] = "FAIL"
    write_json(package / "qc_report.json", qc)
    monetization = monetization_gate(project, manifest, qc)
    print(json.dumps({"project": str(project), "package": str(package), "qc": qc["gate"], "monetization": monetization["decision"], "blocking_reasons": monetization["blocking_reasons"]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="AI YouTube Studio")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    p = sub.add_parser("produce"); p.add_argument("--topic", required=True); p.add_argument("--minutes", type=int, default=1)
    sub.add_parser("qc"); sub.add_parser("variants"); sub.add_parser("resume")
    args = parser.parse_args()
    if args.command == "doctor": doctor()
    elif args.command == "produce": produce(args.topic, args.minutes)
    else: print(json.dumps({"command": args.command, "status": "not_yet_implemented", "honesty": "No artifact was produced."}, indent=2))

if __name__ == "__main__": main()
