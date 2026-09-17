# AI YouTube Studio

A local-first, honest production pipeline for turning a topic into a reviewable YouTube package. This repository treats monetization as a **hard readiness gate**, not as a promise of YouTube Partner Program approval.

## Run

```bash
python3 run.py doctor
python3 run.py produce --topic "The Fermi Paradox" --minutes 1 \
  --confirm-commercial-rights \
  --confirm-not-mass-produced
```

The output is written under `out/<timestamp>-<topic>/package/` and includes a video when FFmpeg and Pillow are available, source-backed research files, storyboard, title, description, chapters, subtitles, `production_manifest.json`, `qc_report.json`, and `monetization_report.json`.

When `espeak-ng` or a configured Piper model is available, the studio synthesizes `narration.wav`, measures its duration, muxes it into the MP4, and burns the generated SRT captions. Without a local TTS provider, it produces a silent, captioned animatic and honestly fails the narration gate.

The audio stage now creates four buses without external Python audio dependencies: `VOICE`, deterministic NumPy `MUSIC` (with `ambient_dark`, `curious_pulse`, `wonder`, and `neutral` presets), procedural `SFX` (whoosh, impact, riser, and static), and continuous `AMBIENCE`. Voice-driven sidechain ducking is applied to music and ambience, and the result is written to `package/final_mix.wav` before FFmpeg muxing.

## Canonical timeline

Each production now writes `timeline/timeline.json` as the single source of truth. It contains eight tracks—`VIDEO`, `GRAPHICS`, `VOICE`, `MUSIC`, `SFX`, `AMBIENCE`, `SUBTITLES`, and `TRANSITIONS`—with source-relative clip references, measured narration timing when available, 25 fps, and a 1920x1080 canvas. Individual bus artifacts are retained alongside `final_mix.wav` so later renderers can rebuild or inspect the mix.

The same timeline is exported to `timeline/project.kdenlive` as MLT XML. The export includes an HD 1080p/25 fps profile, `qimage` and `avformat` producers, per-track playlists, a tractor/multitrack, `mix` transitions for audio tracks, `qtblend` graphics compositing, and `affine` keyframed geometry for slow push-in camera movement.

## Creative memory

Productions append to the persistent shared file `out/creative_memory.json`. Each record stores the topic, timestamp, music preset, script sample, shot count, measured duration, word count, QC gate, and final monetization verdict. The pipeline computes topic Jaccard similarity, tracks preset usage, rotates away from presets used in the last three productions when possible, and records repetition warnings without pretending that similarity analysis proves originality.

## Variants and resume

Variants mode generates only a scoring report; it does not render video:

```bash
python3 run.py variants --topic "The Fermi Paradox" --n 3
```

Each concept varies its opening hook, music preset, and SFX pattern, then scores originality, music diversity, research coverage, and a composite recommendation.

Resume mode reports stage status and reruns missing render, QC, and monetization work while preserving completed artifacts:

```bash
python3 run.py resume --project-dir out/<project>
```

Kdenlive output is written to `kdenlive/project.kdenlive`. If `melt` is available, the exporter attempts a null-consumer validation and records `LOCAL` with `validated_by: "melt"` on success. Without `melt`, the XML is retained and honestly marked `SIMULATED`.

## Monetization gate

A package is marked `ELIGIBLE_FOR_HUMAN_REVIEW` only when originality is attested, commercial-use rights are complete, provenance is complete, the work has meaningful transformation, the project is not marked mass-produced, AI disclosure is configured, narration is present, research sources exist, and QC passes. Otherwise it is marked `NOT_ELIGIBLE` with explicit blocking reasons.

This implements a conservative production-readiness check informed by [YouTube channel monetization policies](https://support.google.com/youtube/answer/1311392), [what content can be monetized](https://support.google.com/youtube/answer/2490020), and [AI disclosure guidance](https://support.google.com/youtube/answer/14328491). It cannot guarantee acceptance into YPP, advertiser suitability, copyright clearance, or revenue.

## Human attestation

The production gate is intentionally not one-way. An operator must explicitly attest to facts the software cannot prove:

```bash
--confirm-commercial-rights
--confirm-not-mass-produced
```

Originality is enabled by default for this local-original workflow. Use `--no-originality` for defensive testing. These flags record `attested_by_operator: true`; they do not waive copyright, rights-clearance, or YouTube review requirements.

## Honesty contract

Artifacts are labeled as `REAL/LOCAL/FREE`, `SIMULATED`, `MISSING`, or `PAID_BLOCKED`. Missing narration, rights evidence, or QC never gets silently replaced with a fake success state.

## Current scope

The MVP implements runtime capability probing, Wikipedia research, source-backed claims, a procedural visual, local TTS when available, measured narration duration, estimated SRT subtitles, FFmpeg audio/caption muxing, asset hashes, expanded loudness/black-frame/silence/decode QC, a production manifest, and the monetization gate. Future work can add local STT timing, canonical multi-track timelines, MLT/Kdenlive export, audio buses, richer craft modules, creative-memory similarity checks, and a human review UI.
