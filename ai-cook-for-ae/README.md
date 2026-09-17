# AI Cook for After Effects

AI Cook is a CEP panel that connects After Effects to the completed fuzzy-waddle studio backend. The studio is the production brain; this panel is the hands and face that turns a generated comp plan into an After Effects composition.

## Architecture

```text
After Effects CEP panel
  └── localhost HTTP → kitchen/kitchen.py:8765
        └── kitchen/director.py → deterministic comp plan
              └── fuzzy-waddle run.py capability probes and local assets
```

## Install

1. Copy the `panel/` folder to the CEP extensions directory:
   - Windows: `C:\Program Files (x86)\Common Files\Adobe\CEP\extensions\com.aicook.panel\`
   - macOS: `~/Library/Application Support/Adobe/CEP/extensions/com.aicook.panel\`
2. Enable unsigned extensions for CEP 11:
   - Windows: set `HKCU\Software\Adobe\CSXS.11\PlayerDebugMode` to string `1`.
   - macOS: `defaults write com.adobe.CSXS.11 PlayerDebugMode 1`.
3. From the fuzzy-waddle root, start the kitchen:

```bash
python3 ai-cook-for-ae/kitchen/kitchen.py
```

4. Open After Effects 2022 or newer and choose **Window → Extensions → AI Cook**.

## Use

1. Enter a prompt such as `30 second title sequence about the Fermi Paradox, dark sci-fi`.
2. Choose a duration from 3–300 seconds and a style.
3. Click **COOK**. The panel calls `POST /cook` and displays the capability/honesty report.
4. Click **APPLY TO AE**. ExtendScript reads the versioned plan and builds the composition.

The plan schema is versioned as `1.0` and contains comp settings, layers, transforms, audio, and metadata. The current director uses a deterministic template fallback. A future local-LLM authoring path can be added without changing the panel contract.

## HTTP API

```bash
curl http://127.0.0.1:8765/status
curl -X POST http://127.0.0.1:8765/cook \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"30 second title sequence about the Fermi Paradox","seconds":30,"style":"dark_sci_fi"}'
```

`/status` returns probed tools and provider statuses. `/cook` returns `{plan_path, plan, report}`. The report explicitly distinguishes `REAL/LOCAL/FREE`, `SIMULATED`, and `MISSING` capabilities.

## Honesty

- Without Ollama, the plan is a deterministic template and is labeled `SIMULATED`.
- Without `espeak-ng` or Piper, audio is `MISSING`; Apply warns that the comp will be silent.
- Without FFmpeg or an existing studio mix, audio remains `MISSING`.
- A failed background render or import is reported rather than replaced by a fake success.

The plugin does not alter the existing studio `run.py`.

## Files

- `kitchen/kitchen.py`: stdlib localhost server.
- `kitchen/director.py`: prompt-to-plan director.
- `panel/CSXS/manifest.xml`: CEP 11 / AEFT manifest.
- `panel/index.html`: dockable UI.
- `panel/jsx/apply_plan.jsx`: ES3-compatible ExtendScript applicator.

## Limitations

The panel cannot be fully exercised without After Effects. The standalone kitchen and plan schema can be tested on any machine with Python and the studio dependencies. ExtendScript uses conservative ES3 syntax and wraps individual layer builds in warnings so one failed layer does not abort the composition.
