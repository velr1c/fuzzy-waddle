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
