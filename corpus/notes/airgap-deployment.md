# Air-gapped deployment notes

An air-gapped deployment is one where the runtime host has no outbound
network access — no internet, sometimes not even DNS for internal
services. The constraint cascades through every layer of a RAG stack:
model download, embedding model download, package install, telemetry,
update channels, and even some default health-check behaviours expect
to phone home.

## Pre-stage every artifact

A reproducible air-gapped build needs each of the following to be
side-loaded ahead of time:

1. **The Python interpreter and its packages.** `uv` can install a
   pinned Python (no system Python dependency) and a `uv.lock` makes
   the dependency set exact. Tarballs of the venv can move between
   machines; pin to the same OS / arch.
2. **The embedding model.** `sentence-transformers` will, by default,
   download from Hugging Face on first use. The fix is to download
   the model on a connected machine, then copy the `~/.cache/huggingface`
   directory onto the air-gapped host. Set
   `TRANSFORMERS_OFFLINE=1` and `HF_HUB_OFFLINE=1` to make any
   attempted download fail loudly instead of silently waiting for a
   network that isn't there.
3. **The reranker model.** Same path as the embedding model.
4. **The generation model.** For Ollama, pull the model on a connected
   machine and copy `~/.ollama/models`. For `llama-cpp-python`, copy
   the `.gguf` blob directly.

## Disable every "report home" default

Two surprises worth squashing:

- `transformers`, `sentence-transformers`, and `huggingface_hub` all
  hit the Hub for version-check pings unless you set their offline
  flags. Combined with a firewall that drops outbound, this manifests
  as 30-second startup delays.
- `qdrant-client` does not phone home, but its telemetry has been
  asked for in the past. Audit before deploy.

## Logging without a sink

The default is to log to local files only. Keep the log rotation
policy in line with the host's disk allocation — uncontrolled growth
of structured logs is a common air-gapped outage.

## The model-update playbook

Updates require a connected staging machine, a versioned bundle, and
an out-of-band transport. The minimum-viable bundle includes the
model files, the package lockfile, the chunker config, and a release
notes file with the SHA-256 of every artifact. The deploying operator
verifies the hashes, swaps the model directory, and runs a smoke test
before lifting traffic.

## What you should plan to lose

Two capabilities don't survive an air-gap without significant
investment:

1. **Live evaluation telemetry.** No prod traces flowing back to a
   central dashboard; you have to ship them out manually.
2. **Continuous benchmark refresh.** The model accuracy drift you'd
   notice in a connected deploy goes undetected unless your release
   process re-runs the gold set on each new bundle.
