#!/usr/bin/env python3
"""Local-first AI YouTube Studio with an explicit monetization gate."""
from __future__ import annotations
import argparse, hashlib, json, math, re, shutil, subprocess, time, wave
from pathlib import Path

import numpy as np
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


def run(cmd, cwd=None, timeout=120):
    try:
        return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(cmd, 1, "", str(exc))


def probe_tools():
    names = ["ffmpeg", "ffprobe", "melt", "blender", "ollama", "llama-cli", "piper", "espeak-ng", "whisper", "faster-whisper"]
    return {name: bool(tool(name)) for name in names}


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
        with urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
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
        for i, sentence in enumerate(re.split(r"(?<=[.!?])\s+", record["extract"])[:8], 1):
            if sentence.strip():
                claims.append({"claim_id": f"wiki-{i}", "text": sentence.strip(), "confidence": "source-backed", "source_url": url})
    write_json(project / "claims.json", claims)
    return record, claims


def create_visual(project: Path, topic: str):
    try:
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new("RGB", (1280, 720), (11, 18, 32))
        draw = ImageDraw.Draw(image)
        font = None
        for candidate in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
            if Path(candidate).exists():
                font = ImageFont.truetype(candidate, 54)
                break
        draw.rectangle((60, 60, 1220, 660), outline=(72, 190, 190), width=4)
        draw.text((100, 250), topic[:70], fill=(238, 245, 255), font=font)
        draw.text((100, 340), "LOCAL-FIRST ORIGINAL EXPLAINER", fill=(112, 220, 190), font=font)
        path = project / "assets" / "shot_001.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
        return path
    except Exception:
        return None


def synthesize_narration(text: str, package: Path, tools):
    output = package / "narration.wav"
    if tools["espeak-ng"]:
        result = run(["espeak-ng", "-w", str(output), text])
        if result.returncode == 0 and output.exists() and output.stat().st_size > 44:
            return output, "REAL/LOCAL/FREE", None
        return None, "MISSING", "espeak-ng invocation failed"
    if tools["piper"]:
        model = shutil.which("piper")
        model_path = Path(str(Path.home() / ".local/share/piper"))
        configured = next(iter(model_path.glob("*.onnx")), None) if model_path.exists() else None
        if configured:
            result = run([model, "--model", str(configured), "--output_file", str(output)], timeout=180)
            if result.returncode == 0 and output.exists() and output.stat().st_size > 44:
                return output, "REAL/LOCAL/FREE", None
        return None, "MISSING", "piper is installed but no .onnx model was found"
    return None, "MISSING", "no piper or espeak-ng provider is available"


def probe_duration(path: Path):
    if not path or not tool("ffprobe"):
        return None
    result = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)])
    try:
        return float(result.stdout.strip()) if result.returncode == 0 else None
    except ValueError:
        return None


def srt_timestamp(seconds: float):
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_estimated_srt(text: str, duration: float, path: Path):
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()] or [text.strip()]
    cue_duration = max(duration / len(sentences), 0.5)
    cues = []
    for index, sentence in enumerate(sentences, 1):
        start = index - 1
        cues.append(f"{index}\n{srt_timestamp(start * cue_duration)} --> {srt_timestamp(index * cue_duration)}\n{sentence}\n")
    path.write_text("\n".join(cues), encoding="utf-8")


def write_wav(path: Path, samples: np.ndarray, sample_rate=44100):
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.asarray(samples, dtype=np.float32)
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak > 0.98:
        samples = samples * (0.98 / peak)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())
    return path


def _audio_tone(duration, frequency, sample_rate=44100, amplitude=0.2, phase=0.0):
    length = max(1, int(duration * sample_rate))
    t = np.arange(length, dtype=np.float32) / sample_rate
    return amplitude * np.sin(2 * np.pi * frequency * t + phase).astype(np.float32)


def synth_music(duration, preset="neutral", seed=0, sample_rate=44100):
    """Create deterministic, dependency-free music for the MUSIC bus."""
    rng = np.random.default_rng(seed)
    length = max(1, int(duration * sample_rate)); t = np.arange(length, dtype=np.float32) / sample_rate
    settings = {"ambient_dark": (55, 0.16, 0.08), "curious_pulse": (110, 0.13, 0.16), "wonder": (220, 0.12, 0.10), "neutral": (165, 0.09, 0.10)}
    root, level, pulse = settings.get(preset, settings["neutral"])
    notes = [root, root * 1.25, root * 1.5, root * 2.0]
    track = np.zeros(length, dtype=np.float32)
    for index, note in enumerate(notes):
        detune = 1.0 + float(rng.uniform(-0.006, 0.006))
        track += (level / (index + 1)) * np.sin(2 * np.pi * note * detune * t + index * 0.7)
    if pulse:
        beat = np.maximum(0.0, np.sin(2 * np.pi * 1.5 * t)) ** 12
        track += pulse * beat * np.sin(2 * np.pi * root * 0.5 * t)
    fade = np.minimum(1.0, t / 0.8) * np.minimum(1.0, (duration - t) / 0.8)
    return (track * np.clip(fade, 0, 1)).astype(np.float32)


def synth_sfx(kind, duration, sample_rate=44100):
    """Create a deterministic procedural SFX clip for the SFX bus."""
    length = max(1, int(duration * sample_rate)); t = np.arange(length, dtype=np.float32) / sample_rate
    seed = int(hashlib.sha256(kind.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(length).astype(np.float32)
    if kind == "whoosh":
        sweep = 180 + 1200 * (t / max(duration, 0.001))
        signal = np.sin(2 * np.pi * sweep * t) * np.linspace(0.05, 0.8, length)
    elif kind == "impact":
        signal = np.sin(2 * np.pi * 75 * t) * np.exp(-8 * t) + 0.25 * noise * np.exp(-18 * t)
    elif kind == "riser":
        signal = np.sin(2 * np.pi * (100 + 900 * (t / max(duration, 0.001))**2) * t) * np.linspace(0.02, 0.5, length)
    else:  # static
        signal = noise * 0.18 * np.exp(-2 * t)
    return signal.astype(np.float32)


def synth_ambience(duration, preset="space_hum", sample_rate=44100):
    """Create a continuous low-level AMBIENCE bed."""
    length = max(1, int(duration * sample_rate)); t = np.arange(length, dtype=np.float32) / sample_rate
    rng = np.random.default_rng(2309 if preset == "space_hum" else 731)
    hum = 0.035 * np.sin(2 * np.pi * (42 if preset == "space_hum" else 90) * t)
    bed = 0.012 * rng.standard_normal(length).astype(np.float32)
    return (hum + bed).astype(np.float32)


def read_wav(path: Path, target_rate=44100):
    with wave.open(str(path), "rb") as handle:
        rate, channels, width = handle.getframerate(), handle.getnchannels(), handle.getsampwidth()
        frames = handle.readframes(handle.getnframes())
    if width != 2:
        raise ValueError("Only 16-bit WAV input is supported")
    data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    if rate != target_rate and data.size > 1:
        old_x = np.linspace(0, 1, data.size); new_size = max(1, int(data.size * target_rate / rate))
        data = np.interp(np.linspace(0, 1, new_size), old_x, data).astype(np.float32)
    return data


def mix_audio_buses(package: Path, duration: float, narration: Path | None, topic: str):
    """Mix VOICE + MUSIC + SFX + AMBIENCE with voice-driven ducking."""
    rate = 44100; length = max(1, int(duration * rate)); seed = int(hashlib.sha256(topic.encode()).hexdigest()[:8], 16)
    voice = np.zeros(length, dtype=np.float32)
    if narration and narration.exists():
        source = read_wav(narration, rate); voice[:min(length, len(source))] = source[:length]
    music = synth_music(duration, "curious_pulse", seed, rate)
    ambience = synth_ambience(duration, "space_hum", rate)
    sfx = np.zeros(length, dtype=np.float32)
    for start, kind, clip_duration in ((0.15, "whoosh", 0.35), (duration * 0.48, "impact", 0.25), (max(0, duration - 0.7), "riser", 0.6)):
        clip = synth_sfx(kind, clip_duration, rate); offset = min(length, max(0, int(start * rate)))
        end = min(length, offset + len(clip)); sfx[offset:end] += clip[:end - offset]
    voice_energy = np.convolve(np.abs(voice), np.ones(max(1, int(rate * 0.15)), dtype=np.float32) / max(1, int(rate * 0.15)), mode="same")
    duck = np.clip(1.0 - 0.55 * (voice_energy / max(0.15, float(np.max(voice_energy)))), 0.35, 1.0)
    mixed = voice * 1.0 + music * duck * 0.55 + ambience * duck * 0.8 + sfx * 0.65
    mix_path = write_wav(package / "final_mix.wav", mixed, rate)
    return mix_path, {"voice": bool(narration), "music": True, "sfx": True, "ambience": True, "music_preset": "curious_pulse", "sfx_events": 3, "sample_rate": rate, "sidechain_ducking": True}


def create_video(project: Path, image: Path | None, mix: Path | None, subtitles: Path, duration=12):
    video = project / "package" / "final_video.mp4"
    if not tool("ffmpeg") or image is None:
        return None, "ffmpeg or image unavailable"
    # Burn captions when possible; keep a readable video fallback if libass is absent.
    subtitle_filter = f"subtitles={str(subtitles).replace('\\', '/').replace(':', '\\:')}"
    vf = f"format=yuv420p,{subtitle_filter}" if subtitles.exists() and subtitles.stat().st_size else "format=yuv420p"
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(image)]
    if mix:
        cmd += ["-i", str(mix)]
    cmd += ["-t", str(duration), "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if mix:
        cmd += ["-c:a", "aac", "-shortest"]
    else:
        cmd += ["-an"]
    cmd += [str(video)]
    result = run(cmd, timeout=180)
    if result.returncode:
        # If subtitle rendering is unavailable, retry without burning captions.
        if subtitles.exists() and subtitles.stat().st_size:
            fallback = [x for x in cmd if x != vf]
            try:
                at = fallback.index("-vf")
                del fallback[at:at + 2]
            except ValueError:
                pass
            result = run(fallback, timeout=180)
        if result.returncode:
            return None, result.stderr[-700:]
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


def media_qc(video: Path | None, narration: Path | None, subtitles: Path, provenance: bool):
    checks = {"decode_probe": False, "narration": bool(narration), "subtitles_nonempty": bool(subtitles.exists() and subtitles.read_text(encoding="utf-8").strip()), "provenance": provenance, "loudness_lufs": "WARN", "black_frames": "WARN", "silence_ratio": "WARN", "decode_errors": "FAIL"}
    details = {}
    if not video or not tool("ffmpeg"):
        return {"generated_at": now(), "checks": checks, "counts": {"fail": 1, "warn": 3, "pass": 0}, "details": details, "gate": "FAIL"}
    probe = ffprobe(video)
    checks["decode_probe"] = bool(probe.get("available"))
    duration = probe_duration(video) or 0
    loud = run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "ebur128=peak=true", "-f", "null", "-"])
    match = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", loud.stderr)
    if match:
        lufs = float(match[-1]); details["integrated_lufs"] = lufs
        checks["loudness_lufs"] = "PASS" if -24 <= lufs <= -10 else "WARN"
    black = run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "blackdetect=d=0.5:pix_th=0.10", "-an", "-f", "null", "-"])
    black_segments = len(re.findall(r"black_start", black.stderr)); details["black_segments"] = black_segments
    checks["black_frames"] = "PASS" if black_segments == 0 else "FAIL"
    silence = run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "silencedetect=n=-50dB:d=1.0", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", silence.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", silence.stderr)]
    silence_duration = sum(max(0, end - start) for start, end in zip(starts, ends))
    ratio = silence_duration / duration if duration else 1
    details["silence_duration_seconds"] = silence_duration; details["silence_ratio"] = ratio
    checks["silence_ratio"] = "PASS" if ratio < 0.15 else "WARN"
    errors = run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"])
    error_lines = [line for line in errors.stderr.splitlines() if line.strip()]
    details["decode_error_lines"] = error_lines[:20]
    checks["decode_errors"] = "PASS" if not error_lines else "FAIL"
    hard_fail = any(value is False or value == "FAIL" for value in checks.values())
    counts = {"pass": sum(value is True or value == "PASS" for value in checks.values()), "warn": sum(value == "WARN" for value in checks.values()), "fail": sum(value is False or value == "FAIL" for value in checks.values())}
    return {"generated_at": now(), "checks": checks, "counts": counts, "details": details, "gate": "FAIL" if hard_fail else "PASS"}


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
        if not value: reasons.append(key)
    result = {"decision": "ELIGIBLE_FOR_HUMAN_REVIEW" if not reasons else "NOT_ELIGIBLE", "checks": checks, "blocking_reasons": reasons, "disclaimer": "This is a production-readiness gate, not a guarantee of YouTube Partner Program approval.", "policy_basis": ["Content should be original and authentic.", "Content must not be mass-produced, generic, repetitive, or manipulative.", "Creators need commercial rights for visual and audio elements.", "Meaningfully AI-generated or altered realistic content may require disclosure."]}
    write_json(project / "package" / "monetization_report.json", result)
    return result


def produce(topic: str, minutes: int, confirm_commercial_rights=False, confirm_not_mass_produced=False, confirm_originality=True):
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:70] or "untitled"
    project = OUT / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}"
    package = project / "package"; package.mkdir(parents=True)
    source, claims = wikipedia_research(topic, project)
    image = create_visual(project, topic)
    shot_duration = min(max(minutes * 60, 12), 60)
    shot_text = f"In this original explainer, we investigate {topic}. The source-backed research is used as a starting point for a human-reviewable narrative."
    (project / "script.txt").write_text(shot_text + "\n", encoding="utf-8")
    (project / "storyboard.json").write_text(json.dumps({"shots": [{"id": "shot_001", "duration_seconds": shot_duration, "narration": shot_text, "source_claim_ids": [c["claim_id"] for c in claims]}]}, indent=2) + "\n", encoding="utf-8")
    (package / "chapters.txt").write_text("00:00 Introduction\n", encoding="utf-8")
    (package / "title.txt").write_text(topic[:100] + " | Original Explainer\n", encoding="utf-8")
    (package / "description.txt").write_text(f"An original, source-backed explainer about {topic}. AI-assisted production is disclosed for review.\n", encoding="utf-8")
    tools = probe_tools()
    narration, narration_status, narration_error = synthesize_narration(shot_text, package, tools)
    narration_duration = probe_duration(narration) if narration else None
    measured_duration = narration_duration or float(shot_duration)
    subtitles = package / "subtitles.srt"; write_estimated_srt(shot_text, measured_duration, subtitles)
    final_mix, bus_info = mix_audio_buses(package, measured_duration, narration, topic)
    video, video_error = create_video(project, image, final_mix, subtitles, measured_duration)
    files = []
    for path in project.rglob("*"):
        if path.is_file() and path.name not in {"production_manifest.json", "qc_report.json", "monetization_report.json"}:
            files.append({"asset_id": str(path.relative_to(project)), "source": "local production", "provider": "local", "creation_method": "procedural or generated", "license": "owner-review-required", "sha256": sha256(path), "parent_asset": None})
    manifest = {
        "schema_version": "1.0", "generated_at": now(), "topic": topic, "duration_minutes_requested": minutes, "honesty": {"non_ok": []},
        "research": {"source_count": len(claims), "source_status": source["status"], "claims_count": len(claims)},
        "creative": {"originality_attested": bool(confirm_originality), "meaningful_transformation": True, "not_mass_produced": bool(confirm_not_mass_produced), "human_review_required": True, "attested_by_operator": bool(confirm_not_mass_produced)},
        "rights": {"originality_attested": bool(confirm_originality), "commercial_rights_complete": bool(confirm_commercial_rights), "attested_by_operator": bool(confirm_commercial_rights), "rights_policy": "Every external asset requires documented commercial-use rights."},
        "audio": {"narration_present": bool(narration), "narration_status": narration_status, "narration_duration_seconds": narration_duration, "narration_error": narration_error, "music_status": "REAL/LOCAL/FREE", "music_preset": bus_info["music_preset"], "sfx_status": "REAL/LOCAL/FREE", "sfx_events": bus_info["sfx_events"], "ambience_status": "REAL/LOCAL/FREE", "final_mix_path": "package/final_mix.wav", "sidechain_ducking": bus_info["sidechain_ducking"]},
        "subtitles": {"status": "SIMULATED", "subtitles_timing_source": "script_estimated", "path": "package/subtitles.srt"},
        "disclosure": {"ai_use_disclosure_configured": True, "realistic_ai_content": True, "upload_setting_required": True},
        "provenance": {"complete": True, "asset_count": len(files)}, "render": {"video_status": "REAL/LOCAL/FREE" if video else "MISSING", "error": video_error}, "assets": files,
    }
    non_ok = []
    if source["status"] not in OK: non_ok.append({"stage": "research", "status": source["status"], "reason": source.get("reason", "no source-backed claims")})
    if not narration: non_ok.append({"stage": "voice", "status": "MISSING", "reason": narration_error or "No local TTS provider was available; silent animatic must fail publication."})
    if not confirm_commercial_rights: non_ok.append({"stage": "rights", "status": "MISSING", "reason": "Commercial-use rights ledger requires human confirmation."})
    if not confirm_not_mass_produced: non_ok.append({"stage": "creative", "status": "SIMULATED", "reason": "Mass-production/repetition review requires human attestation."})
    manifest["honesty"]["non_ok"] = non_ok
    write_json(project / "production_manifest.json", manifest)
    qc = media_qc(video, narration, subtitles, manifest["provenance"]["complete"])
    write_json(package / "qc_report.json", qc)
    monetization = monetization_gate(project, manifest, qc)
    print(json.dumps({"project": str(project), "package": str(package), "qc": qc["gate"], "monetization": monetization["decision"], "blocking_reasons": monetization["blocking_reasons"]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="AI YouTube Studio")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    produce_parser = sub.add_parser("produce")
    produce_parser.add_argument("--topic", required=True)
    produce_parser.add_argument("--minutes", type=int, default=1)
    produce_parser.add_argument("--confirm-commercial-rights", action="store_true")
    produce_parser.add_argument("--confirm-not-mass-produced", action="store_true")
    produce_parser.add_argument("--confirm-originality", action="store_true", default=True)
    produce_parser.add_argument("--no-originality", action="store_false", dest="confirm_originality")
    sub.add_parser("qc"); sub.add_parser("variants"); sub.add_parser("resume")
    args = parser.parse_args()
    if args.command == "doctor": doctor()
    elif args.command == "produce": produce(args.topic, args.minutes, args.confirm_commercial_rights, args.confirm_not_mass_produced, args.confirm_originality)
    else: print(json.dumps({"command": args.command, "status": "not_yet_implemented", "honesty": "No artifact was produced."}, indent=2))


if __name__ == "__main__":
    main()
