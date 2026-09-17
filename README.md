# AI YouTube Studio

A local-first, AI-assisted YouTube production pipeline with an explicit monetization-readiness gate. Topic in; a reviewable production package out. The system is designed to be honest about local capabilities and never promises YouTube Partner Program approval, copyright clearance, advertiser suitability, or revenue.

## Installation

```bash
git clone https://github.com/velr1c/fuzzy-waddle.git
cd fuzzy-waddle
pip install numpy Pillow
```

Recommended local tools:

```bash
sudo apt install ffmpeg espeak-ng kdenlive melt
```

Piper can be added separately with a compatible local voice model. The pipeline probes capabilities at runtime and never silently substitutes a missing provider.

## Quick start

```bash
python3 run.py doctor
python3 run.py produce --topic "The Fermi Paradox" --minutes 2 \
  --confirm-commercial-rights \
  --confirm-not-mass-produced
python3 run.py variants --topic "The Fermi Paradox" --n 3
python3 run.py resume --project-dir out/<project-dir>
```

## Pipeline stages

### 1. Research

Wikipedia-backed research produces `sources.json` and source-linked `claims.json` with retrieval status and confidence labels.

### 2. Creative and visual production

The MVP creates an original explainer script, storyboard, and procedural title-card visual at `assets/shot_001.png`.

### 3. Audio buses

Four parallel buses are generated locally when possible:

- **VOICE**: narration through `espeak-ng` or a configured Piper model.
- **MUSIC**: deterministic NumPy synthesis with `ambient_dark`, `curious_pulse`, `wonder`, and `neutral` presets.
- **SFX**: procedural whoosh, impact, riser, and static effects.
- **AMBIENCE**: continuous procedural room tone or space hum.

Voice-driven sidechain ducking reduces music and ambience beneath narration. The package retains `narration.wav`, `music.wav`, `sfx_*.wav`, `ambience.wav`, and `final_mix.wav`.

### 4. Subtitles and render

Subtitles are generated from script-estimated timing and labeled `SIMULATED` because timing is not measured by STT. FFmpeg burns captions into the final MP4 and muxes the mixed audio.

### 5. Canonical timeline

`timeline/timeline.json` is the production source of truth with eight tracks: `VIDEO`, `GRAPHICS`, `VOICE`, `MUSIC`, `SFX`, `AMBIENCE`, `SUBTITLES`, and `TRANSITIONS`. It records 25 FPS, a 1920×1080 canvas, source-relative clips, measured narration timing, camera motion parameters, and audio events.

### 6. Kdenlive export

`kdenlive/project.kdenlive` is generated as MLT XML for Kdenlive 23.x–26.x. It includes `qimage` and `avformat` producers, playlists, tractor/multitrack, audio `mix` transitions, `qtblend` compositing, and affine keyframed camera geometry. If `melt` is installed, a null-consumer validation is attempted and recorded as `LOCAL`; otherwise the written XML is marked `SIMULATED`.

### 7. QC

The QC report checks decode probe, narration, non-empty subtitles, provenance, EBU R128 loudness, black frames, silence ratio, and decode errors. WARN results do not block; hard FAIL results do.

### 8. Monetization-readiness gate

The package is marked `ELIGIBLE_FOR_HUMAN_REVIEW` only when originality, commercial rights, provenance, meaningful transformation, non-mass-production attestation, AI disclosure, narration, research, and QC all pass. Otherwise it returns `NOT_ELIGIBLE` with explicit blocking reasons.

## Creative memory

`out/creative_memory.json` persists across projects and records each production’s topic, timestamp, music preset, script sample, shot count, duration, word count, QC gate, and monetization verdict. The pipeline computes topic Jaccard similarity, tracks preset usage, rotates away from presets used in the last three productions when possible, and records repetition warnings above 0.8 similarity. Similarity analysis is an aid to review, not proof of originality.

## Variants

Variants mode does not render video:

```bash
python3 run.py variants --topic "The Fermi Paradox" --n 3
```

It varies hook template, music preset, and SFX pattern, then scores each concept using:

```text
0.4 * originality + 0.3 * music diversity + 0.3 * research coverage
```

The JSON report includes the recommended index and preset.

## Resume

Resume checks completed artifacts and reports `SKIP` versus `RUN` for research, creative, voice, mixing, timeline, Kdenlive, render, QC, and monetization. If an upstream output such as the final video is removed, downstream QC and monetization are invalidated and rerun.

```bash
python3 run.py resume --project-dir out/<project-dir>
```

## Human attestation

These flags record operator attestations that software cannot prove:

```text
--confirm-commercial-rights
--confirm-not-mass-produced
--no-originality
```

Attestation does not waive copyright obligations or guarantee platform approval.

## Honesty contract

Every capability is represented as one of:

- **REAL/LOCAL/FREE** — it actually worked with local or free tools.
- **SIMULATED** — a development substitute or estimated result.
- **MISSING** — unavailable and not produced.
- **PAID_BLOCKED** — intentionally blocked because it requires paid access.

`production_manifest.json` includes an `honesty.non_ok` list. Missing narration produces a silent animatic and fails publication QC; it is never presented as a narrated success.

## Output layout

```text
out/<timestamp>-<topic>/
├── sources.json
├── claims.json
├── script.txt
├── storyboard.json
├── assets/shot_001.png
├── package/
│   ├── narration.wav
│   ├── music.wav
│   ├── sfx_whoosh.wav
│   ├── sfx_impact.wav
│   ├── sfx_riser.wav
│   ├── ambience.wav
│   ├── final_mix.wav
│   ├── subtitles.srt
│   ├── final_video.mp4
│   ├── qc_report.json
│   └── monetization_report.json
├── timeline/timeline.json
├── kdenlive/project.kdenlive
└── production_manifest.json
```

The shared memory file is `out/creative_memory.json`.

## Examples

Executable examples are in `examples/`:

```bash
./examples/fermi_paradox.sh
./examples/variants.sh
./examples/resume.sh out/<project-dir>
```

## Troubleshooting

### `espeak-ng not found`

Install `sudo apt install espeak-ng` on Ubuntu/Debian or `brew install espeak-ng` on macOS. Without TTS, the system honestly creates a silent animatic and fails the narration gate.

### `piper not found`

Install Piper and configure a local `.onnx` voice model. The pipeline only uses Piper when its executable and model are available.

### `ffmpeg not found`

Install `sudo apt install ffmpeg` or `brew install ffmpeg`. Rendering and media QC require FFmpeg.

### `melt not found`

Install Kdenlive, which provides `melt` on many distributions. Without it, Kdenlive XML is retained and marked `SIMULATED`, not falsely marked validated.

### Monetization returns `NOT_ELIGIBLE`

Inspect `package/monetization_report.json`. Common causes are missing commercial-rights or non-mass-produced attestations, missing narration, missing research, or QC failure.

### Video is silent

A local TTS provider was unavailable. Install `espeak-ng` or configure Piper, then use `resume` or rerun production.

### Subtitle timing says `script_estimated`

This is expected. Real subtitle timing requires STT measurement with Whisper or another local recognizer; estimated timing remains explicitly labeled.

## Testing

```bash
python3 -m py_compile run.py
python3 run.py doctor
python3 run.py produce --topic "Test Topic" --minutes 1 \
  --confirm-commercial-rights --confirm-not-mass-produced
python3 run.py variants --topic "Test Topic" --n 3
python3 run.py resume --project-dir out/<project-dir>
```

## Limitations and future work

The current implementation uses a single procedural shot, simple explainer scripts, estimated subtitle timing, procedural audio, and no true multi-shot VFX or motion-graphics authoring. Future work could add local LLM scripting, Whisper timing, ComfyUI visuals, multi-shot storyboards, advanced motion graphics, and licensed music workflows.

## Monetization disclaimer

The monetization gate is a conservative production-readiness check, not a guarantee of YouTube Partner Program approval. YouTube policies can change and are applied by platform reviewers. This software cannot guarantee YPP acceptance, certify copyright clearance, predict advertiser suitability, or promise revenue.

## License

MIT
