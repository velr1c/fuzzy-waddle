"""Prompt-to-plan director for the AI Cook After Effects panel."""
import hashlib
import json
import re
from pathlib import Path

SCHEMA_VERSION = "1.0"
PALETTES = {
    "dark_sci_fi": ([0.93, 0.94, 0.96], [0.03, 0.05, 0.10]),
    "neon": ([0.90, 0.98, 1.0], [0.08, 0.01, 0.16]),
    "warm_documentary": ([1.0, 0.85, 0.62], [0.16, 0.08, 0.03]),
    "minimal": ([0.95, 0.95, 0.95], [0.08, 0.08, 0.08]),
}


def _title(prompt):
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", prompt)
    ignored = {"second", "seconds", "title", "sequence", "about", "a", "the", "and"}
    kept = [w for w in words if w.lower() not in ignored]
    return " ".join(kept[-6:] or words[:6] or ["AI COOK"]).upper()


def direct(prompt, seconds, style, caps, providers, assets_dir):
    seconds = max(3, min(300, float(seconds)))
    style = style if style in PALETTES else "dark_sci_fi"
    seed = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16)
    foreground, background = PALETTES[style]
    assets_dir = Path(assets_dir); assets_dir.mkdir(parents=True, exist_ok=True)
    bg_path = assets_dir / "cook_background.png"
    try:
        from PIL import Image, ImageDraw
        image = Image.new("RGB", (1920, 1080), tuple(int(x * 255) for x in background))
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 80, 1840, 1000), outline=tuple(int(x * 255) for x in foreground), width=5)
        image.save(bg_path)
        background_status = "REAL/LOCAL/FREE"
    except Exception as exc:
        background_status = "MISSING"
        bg_path = None
    title = _title(prompt)
    layers = [
        {"name": "TITLE", "type": "text", "text": {"content": title, "size": 110, "color": foreground}, "in_point": 0.0, "duration": seconds, "transform": {"position": [[0, [960, 500]]], "scale": [[0, [100, 100]], [seconds, [104, 104]]], "opacity": [[0, 0], [2, 100]]}},
        {"name": "BACKGROUND", "type": "footage", "file": str(bg_path.resolve()) if bg_path else "", "status": background_status, "in_point": 0.0, "duration": seconds, "transform": {"position": [[0, [960, 540]]], "scale": [[0, [100, 100]], [seconds, [110, 110]]] }},
        {"name": "ACCENT", "type": "solid", "color": foreground, "in_point": 0.0, "duration": seconds, "transform": {"position": [[0, [960, 850]]], "scale": [[0, [55, 3]], [seconds, [70, 3]]], "opacity": [[0, 0], [1, 75]]}},
    ]
    audio_file = str((Path(assets_dir).parent / "package" / "final_mix.wav").resolve())
    audio_status = "LOCAL" if Path(audio_file).exists() else "MISSING"
    report = {"authoring_mode": "SIMULATED", "capabilities": {"background": background_status, "audio": audio_status, "local_llm": "REAL/LOCAL/FREE" if providers.get("ollama") else "MISSING"}, "honesty": []}
    if not providers.get("ollama"): report["honesty"].append({"stage": "director", "status": "SIMULATED", "reason": "ollama unavailable; deterministic template plan used"})
    if audio_status == "MISSING": report["honesty"].append({"stage": "audio", "status": "MISSING", "reason": "studio final_mix.wav is not available for this cook"})
    plan = {"schema_version": SCHEMA_VERSION, "comp": {"name": "Cook - " + title.title(), "width": 1920, "height": 1080, "fps": 25, "duration": seconds}, "layers": layers, "audio": {"file": audio_file, "status": audio_status}, "meta": {"prompt": prompt, "style": style, "seed": seed}}
    return plan, report


if __name__ == "__main__":
    print(json.dumps(direct("Fermi Paradox", 30, "dark_sci_fi", {}, {}, "/tmp/ai-cook-assets"), indent=2))
