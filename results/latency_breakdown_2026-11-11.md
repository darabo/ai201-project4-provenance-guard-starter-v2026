# Latency breakdown

From `python runlog.py --stages`, 2026-11-11T21:49:26-0500, over logs/runs.jsonl before the load test was run.

Warm scored requests: 111   mean total: 40.13 ms

| Stage | Mean ms | Share of the request |
|---|---|---|
| gpt2 perplexity (detector.py) | 38.53 | 96.0% |
| style measures (stylometry.py) | 0.11 | 0.3% |
| stock-phrase search (markers.py) | 0.11 | 0.3% |
| combine and label (scoring.py) | 0.00 | 0.0% |
| everything else (checks, audit write, response) | 1.39 | 3.5% |
| **whole request** | 40.13 | 100.0% |

Cold starts: 7   mean total: 2265.4 ms, of which the model stage (load + first pass): 2263.4 ms (99.9%)
