# AI YouTube Studio

A local-first, honest production pipeline for turning a topic into a reviewable YouTube package. This repository treats monetization as a **hard readiness gate**, not as a promise of YouTube Partner Program approval.

## Run

```bash
python3 run.py doctor
python3 run.py produce --topic "The Fermi Paradox" --minutes 1
```

The output is written under `out/<timestamp>-<topic>/package/` and includes a video when FFmpeg and Pillow are available, source-backed research files, storyboard, title, description, chapters, subtitles, `production_manifest.json`, `qc_report.json`, and `monetization_report.json`.

## Monetization gate

A package is marked `ELIGIBLE_FOR_HUMAN_REVIEW` only when originality is attested, commercial-use rights are complete, provenance is complete, the work has meaningful transformation, the project is not marked mass-produced, AI disclosure is configured, narration is present, research sources exist, and QC passes. Otherwise it is marked `NOT_ELIGIBLE` with explicit blocking reasons.

This implements a conservative production-readiness check informed by [YouTube channel monetization policies](https://support.google.com/youtube/answer/1311392), [what content can be monetized](https://support.google.com/youtube/answer/2490020), and [AI disclosure guidance](https://support.google.com/youtube/answer/14328491). It cannot guarantee acceptance into YPP, advertiser suitability, copyright clearance, or revenue.

## Honesty contract

Artifacts are labeled as `REAL/LOCAL/FREE`, `SIMULATED`, `MISSING`, or `PAID_BLOCKED`. Missing narration, rights evidence, or QC never gets silently replaced with a fake success state.

## Current scope

The MVP implements runtime capability probing, Wikipedia research, source-backed claims, a procedural visual, an FFmpeg animatic, asset hashes, a production manifest, QC, and the monetization gate. Future work can add local TTS/STT, canonical multi-track timelines, MLT/Kdenlive export, audio buses, real subtitle timing, richer craft modules, creative-memory similarity checks, and a human review UI.
