# Hardware fingerprint — the rig the committed numbers came from

Every `studies/<N>/results.json` embeds the runtime fingerprint of
the box that produced its numbers, under the top-level `hardware`
key. Anyone re-running an experiment on different hardware should
expect different absolute latencies; the *relative ordering* of
configurations is what should transfer.

## Reference rig

The committed `results.json` files are produced on:

| Field | Value |
|---|---|
| Machine | MacBook Pro, 14-inch |
| Chip | Apple M3 Pro |
| CPU cores | 11 (5 performance + 6 efficiency) |
| RAM | 16 GB unified memory |
| GPU | No discrete; integrated 14-core GPU (used only via Metal where the framework supports it) |
| OS | macOS 26 (Tahoe) |
| Python | 3.11.15 |
| PyTorch | 2.12.0 |
| qdrant-client | 1.18 (embedded local mode) |
| sentence-transformers | 5.x |

This is **not** the brief's target rig (RTX 3060, 6 GB VRAM, 16 GB
RAM). The reference rig is what is available; the brief's rig is
what the system is designed for. Two implications:

1. **Embedding throughput on the reference is slower than the
   target.** The RTX 3060 (CUDA, fp16) is roughly 8–12× faster at
   embedding than the M3 Pro on CPU. The committed numbers represent
   a worst-case timing for ingest.
2. **The generation step (Ollama) is not exercised in committed
   studies.** Studies 00–04 in this artifact measure
   retrieval-only metrics, which are insensitive to the GPU. Studies
   05 (generation bake-off) and the answer-faithfulness section of
   study 07 require GPU + Ollama and ship as `PLANNED.md` until the
   target rig is available.

## Per-`results.json` fingerprint schema

```jsonc
{
  "hardware": {
    "platform": "<uname -srm>",
    "machine": "<arch>",
    "processor": "<CPU label>",
    "python": "3.11.x",
    "ram_gb": 16.0,
    "cpu_count": 11,
    "started_at": "2026-05-27T20:32:01-0500",
    "git_sha": "<short SHA at run-time>",
    "torch": "2.12.0",
    "numpy": "2.x"
  }
}
```

The fingerprint is captured by `studies/_common.py::hardware_fingerprint`
and is stable across reruns on the same host.

## How to refresh the numbers on your rig

```
git clone https://github.com/naumanAhmed3/crag
cd crag
make setup
make ingest-sample
make reproduce
```

`make reproduce` overwrites every committed `results.json` with a
fresh run on your host. Compare against the originals (`git diff`)
to see the delta. The methodology doc (`01-methodology.md`)
documents the tolerance bands that constitute a meaningful drift
vs noise.
