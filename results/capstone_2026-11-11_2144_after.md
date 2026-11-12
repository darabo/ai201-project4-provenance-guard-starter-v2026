# Capstone run: after

- When: 2026-11-11T21:44:37-05:00
- Code tested: commit `72aef9a` plus uncommitted changes to `run_capstone.py, runlog.py`
- Service started with: `gunicorn app:app --bind 127.0.0.1:5000 --workers 1 --timeout 120`
- Run tag (appears in every creator_id this run used): `88792b`
- Produced by: `python run_capstone.py --label after`

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Reproducible local run path | 2 of 2 checks (health, submit) per clean start | 2/2 | 2/2 | 2/2 | MET |
| 2. Complete structured run logging | 10 of 10 requests | 10/10 | 10/10 | 10/10 | MET |
| 3. Bad submission input is rejected and logged | 5 of 5 bodies | 5/5 | 5/5 | 5/5 | MET |
| 4. Warm submissions remain responsive | 9 of 10 within 500 ms | 10/10 | 10/10 | 10/10 | MET |
| 5. Appeals preserve the original evidence | 4 of 4 checks | 4/4 | 4/4 | 4/4 | MET |

## Criterion 1: Reproducible local run path

Target: 2 of 2 checks (health, submit) per clean start, in each of three trials. Produced by `run_capstone.py::criterion_1`.

### Trial 1: 2/2 (pass)

```text
source cloned: /Users/darabonakdar/ai201-project4-provenance-guard-starter-v2026
'Booting worker with pid' seen after 24.4s
last lines of the start output:
  perplexity     12.5
  model_signal   0.8864   (higher = more likely AI)
  [2026-11-11 21:43:17 -0500] [18148] [INFO] Starting gunicorn 23.0.0
  [2026-11-11 21:43:17 -0500] [18148] [INFO] Listening at: http://127.0.0.1:5000 (18148)
  [2026-11-11 21:43:17 -0500] [18148] [INFO] Using worker: sync
  [2026-11-11 21:43:17 -0500] [18160] [INFO] Booting worker with pid: 18160
GET /health -> 200 {"detector_loaded": false, "detector_model": "gpt2", "log_entries": 653, "ok": true, "rate_limiting": true}
POST /submit -> 200 {"confidence": 0.8137, "content_id": "c_7e70705cee48", "creator_id": "demo_instructor", "guess": "ai", "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wr
last record in the clone's logs/runs.jsonl:
  {"timestamp": "2026-11-12T02:43:17.444+00:00", "request_id": "r_e92da4e03f31", "method": "POST", "path": "/submit", "input": {"body_bytes": 725, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "demo_instructor", "text_chars": 680, "text_words": 91, "text_preview": "The importance of effective time management cannot be overst"}, "output": {"status_code": 200, "content_id": "c_7e70705cee48", "guess": "ai", "confidence": 0.8137, "model_score": 0.7544, "style_score": 0.7145, "marker_score": 0.9943, "status": "decided"}, "outcome": "ok", "duration_ms": 2126.7, "cpu_ms": 1523.8, "cold_start": true, "stages_ms": {"model": 2124.6, "style": 0.2, "markers": 0.2, "scoring": 0.0}}
```

### Trial 2: 2/2 (pass)

```text
source cloned: /Users/darabonakdar/ai201-project4-provenance-guard-starter-v2026
'Booting worker with pid' seen after 25.1s
last lines of the start output:
  perplexity     12.5
  model_signal   0.8864   (higher = more likely AI)
  [2026-11-11 21:43:46 -0500] [18161] [INFO] Starting gunicorn 23.0.0
  [2026-11-11 21:43:46 -0500] [18161] [INFO] Listening at: http://127.0.0.1:5000 (18161)
  [2026-11-11 21:43:46 -0500] [18161] [INFO] Using worker: sync
  [2026-11-11 21:43:46 -0500] [18173] [INFO] Booting worker with pid: 18173
GET /health -> 200 {"detector_loaded": false, "detector_model": "gpt2", "log_entries": 653, "ok": true, "rate_limiting": true}
POST /submit -> 200 {"confidence": 0.8137, "content_id": "c_8b04f1adfebf", "creator_id": "demo_instructor", "guess": "ai", "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wr
last record in the clone's logs/runs.jsonl:
  {"timestamp": "2026-11-12T02:43:46.941+00:00", "request_id": "r_f0ac2ed45fba", "method": "POST", "path": "/submit", "input": {"body_bytes": 725, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "demo_instructor", "text_chars": 680, "text_words": 91, "text_preview": "The importance of effective time management cannot be overst"}, "output": {"status_code": 200, "content_id": "c_8b04f1adfebf", "guess": "ai", "confidence": 0.8137, "model_score": 0.7544, "style_score": 0.7145, "marker_score": 0.9943, "status": "decided"}, "outcome": "ok", "duration_ms": 2101.9, "cpu_ms": 1526.0, "cold_start": true, "stages_ms": {"model": 2099.8, "style": 0.2, "markers": 0.2, "scoring": 0.0}}
```

### Trial 3: 2/2 (pass)

```text
source cloned: /Users/darabonakdar/ai201-project4-provenance-guard-starter-v2026
'Booting worker with pid' seen after 27.9s
last lines of the start output:
  perplexity     12.5
  model_signal   0.8864   (higher = more likely AI)
  [2026-11-11 21:44:19 -0500] [18177] [INFO] Starting gunicorn 23.0.0
  [2026-11-11 21:44:19 -0500] [18177] [INFO] Listening at: http://127.0.0.1:5000 (18177)
  [2026-11-11 21:44:19 -0500] [18177] [INFO] Using worker: sync
  [2026-11-11 21:44:19 -0500] [18200] [INFO] Booting worker with pid: 18200
GET /health -> 200 {"detector_loaded": false, "detector_model": "gpt2", "log_entries": 653, "ok": true, "rate_limiting": true}
POST /submit -> 200 {"confidence": 0.8137, "content_id": "c_ba3707422eab", "creator_id": "demo_instructor", "guess": "ai", "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wr
last record in the clone's logs/runs.jsonl:
  {"timestamp": "2026-11-12T02:44:19.320+00:00", "request_id": "r_31076fa9da34", "method": "POST", "path": "/submit", "input": {"body_bytes": 725, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "demo_instructor", "text_chars": 680, "text_words": 91, "text_preview": "The importance of effective time management cannot be overst"}, "output": {"status_code": 200, "content_id": "c_ba3707422eab", "guess": "ai", "confidence": 0.8137, "model_score": 0.7544, "style_score": 0.7145, "marker_score": 0.9943, "status": "decided"}, "outcome": "ok", "duration_ms": 2101.1, "cpu_ms": 1519.2, "cold_start": true, "stages_ms": {"model": 2099.3, "style": 0.2, "markers": 0.2, "scoring": 0.0}}
```

## Criterion 2: Complete structured run logging

Target: 10 of 10 requests, in each of three trials. Produced by `run_capstone.py::criterion_2`.

### Trial 1: 10/10 (pass)

```text
 1. GET /health -> 200  r_7496e62a2e0a  ok
 2. POST /submit -> 200  r_9e1a3dfdb1c7  ok
 3. POST /submit -> 200  r_678f51d16ccd  ok
 4. POST /submit -> 200  r_099391261f75  ok
 5. POST /submit -> 200  r_ba7503d1e7a0  ok
 6. POST /submit -> 400  r_d63abb2ce4f8  ok
 7. POST /submit -> 400  r_a63a53f3fbca  ok
 8. POST /appeal -> 200  r_40acc5f756dc  ok
 9. POST /appeal -> 404  r_f4e18bffcf0d  ok
10. GET /submitt -> 404  r_53d8518017d4  ok
```

### Trial 2: 10/10 (pass)

```text
 1. GET /health -> 200  r_11fa291b1932  ok
 2. POST /submit -> 200  r_531019431027  ok
 3. POST /submit -> 200  r_5ebdf543d292  ok
 4. POST /submit -> 200  r_17a8c12235e2  ok
 5. POST /submit -> 200  r_01dd2cd3312f  ok
 6. POST /submit -> 400  r_e581766b190f  ok
 7. POST /submit -> 400  r_3937ae17e2b2  ok
 8. POST /appeal -> 200  r_464a8aeb1413  ok
 9. POST /appeal -> 404  r_40eca51372e0  ok
10. GET /submitt -> 404  r_385091c125ba  ok
```

### Trial 3: 10/10 (pass)

```text
 1. GET /health -> 200  r_7bff1d1298fa  ok
 2. POST /submit -> 200  r_d1a8a3de8563  ok
 3. POST /submit -> 200  r_2efa93864a1f  ok
 4. POST /submit -> 200  r_413ee0d38522  ok
 5. POST /submit -> 200  r_74b23e0f2cab  ok
 6. POST /submit -> 400  r_eaff79bf4d7c  ok
 7. POST /submit -> 400  r_c9c249c0f54b  ok
 8. POST /appeal -> 200  r_fe495ce789a5  ok
 9. POST /appeal -> 404  r_9c42257bea2d  ok
10. GET /submitt -> 404  r_e49a62057b14  ok
```

## Criterion 3: Bad submission input is rejected and logged

Target: 5 of 5 bodies, in each of three trials. Produced by `run_capstone.py::criterion_3`.

### Trial 1: 5/5 (pass)

```text
missing text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:44:27.818+00:00", "request_id": "r_1a46a04cc85b", "method": "POST", "path": "/submit", "input": {"body_bytes": 34, "body_type": "object", "fields": ["creator_id"], "creator_id": "c3_88792b_trial1"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.5, "cpu_ms": 0.5, "cold_start": true}
empty text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:44:27.821+00:00", "request_id": "r_5a06528109e0", "method": "POST", "path": "/submit", "input": {"body_bytes": 46, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_88792b_trial1", "text_chars": 0, "text_words": 0, "text_preview": ""}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
whitespace-only text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:44:27.824+00:00", "request_id": "r_e0ca90c32221", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_88792b_trial1", "text_chars": 3, "text_words": 0, "text_preview": "   "}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
non-string text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:44:27.826+00:00", "request_id": "r_96641a45e116", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_88792b_trial1"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
JSON array: -> 400 {"error": "bad_request", "message": "Send a JSON object like {\"text\": \"...\", \"creator_id\": \"...\"}."}  ok
    {"timestamp": "2026-11-12T02:44:27.828+00:00", "request_id": "r_c29d7f99adda", "method": "POST", "path": "/submit", "input": {"body_bytes": 9, "body_type": "list"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
```

### Trial 2: 5/5 (pass)

```text
missing text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:44:27.829+00:00", "request_id": "r_0cbc4d05b63a", "method": "POST", "path": "/submit", "input": {"body_bytes": 34, "body_type": "object", "fields": ["creator_id"], "creator_id": "c3_88792b_trial2"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
empty text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:44:27.832+00:00", "request_id": "r_c5b58870b88a", "method": "POST", "path": "/submit", "input": {"body_bytes": 46, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_88792b_trial2", "text_chars": 0, "text_words": 0, "text_preview": ""}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.5, "cpu_ms": 0.5, "cold_start": true}
whitespace-only text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:44:27.834+00:00", "request_id": "r_03f28c2f8271", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_88792b_trial2", "text_chars": 3, "text_words": 0, "text_preview": "   "}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
non-string text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:44:27.836+00:00", "request_id": "r_1f088c732e2b", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_88792b_trial2"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
JSON array: -> 400 {"error": "bad_request", "message": "Send a JSON object like {\"text\": \"...\", \"creator_id\": \"...\"}."}  ok
    {"timestamp": "2026-11-12T02:44:27.838+00:00", "request_id": "r_6ade769cdbf3", "method": "POST", "path": "/submit", "input": {"body_bytes": 9, "body_type": "list"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
```

### Trial 3: 5/5 (pass)

```text
missing text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:44:27.840+00:00", "request_id": "r_6cbd54f30fbe", "method": "POST", "path": "/submit", "input": {"body_bytes": 34, "body_type": "object", "fields": ["creator_id"], "creator_id": "c3_88792b_trial3"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
empty text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:44:27.842+00:00", "request_id": "r_fe2272e93918", "method": "POST", "path": "/submit", "input": {"body_bytes": 46, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_88792b_trial3", "text_chars": 0, "text_words": 0, "text_preview": ""}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.1, "cpu_ms": 0.1, "cold_start": true}
whitespace-only text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:44:27.844+00:00", "request_id": "r_744e65157693", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_88792b_trial3", "text_chars": 3, "text_words": 0, "text_preview": "   "}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
non-string text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:44:27.846+00:00", "request_id": "r_a1d3c7bb762e", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_88792b_trial3"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.4, "cold_start": true}
JSON array: -> 400 {"error": "bad_request", "message": "Send a JSON object like {\"text\": \"...\", \"creator_id\": \"...\"}."}  ok
    {"timestamp": "2026-11-12T02:44:27.848+00:00", "request_id": "r_17be7062da7c", "method": "POST", "path": "/submit", "input": {"body_bytes": 9, "body_type": "list"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
```

## Criterion 4: Warm submissions remain responsive

Target: 9 of 10 within 500 ms, in each of three trials. Produced by `run_capstone.py::criterion_4`.

### Trial 1: 10/10 (pass)

```text
warm-up -> 200, duration_ms 2255.5, cold_start True
GET /health -> detector_loaded: True
 1. 86 words -> 200, duration_ms 50.9, within
    {"timestamp": "2026-11-12T02:44:31.008+00:00", "request_id": "r_a902d6baf45c", "method": "POST", "path": "/submit", "input": {"body_bytes": 549, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c4_88792b_t1_00", "text_chars": 494, "text_words": 86, "text_preview": "Few nations in the world share polarizing views among people"}, "output": {"status_code": 200, "content_id": "c_0b060a31423e", "guess": "unsure", "confidence": 0.5259, "model_score": 0.5643, "style_score": 0.4874, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 50.9, "cpu_ms": 67.2, "cold_start": false, "stages_ms": {"model": 49.3, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
 2. 51 words -> 200, duration_ms 37.8, within
 3. 62 words -> 200, duration_ms 40.2, within
 4. 48 words -> 200, duration_ms 35.5, within
 5. 54 words -> 200, duration_ms 42.5, within
 6. 58 words -> 200, duration_ms 41.3, within
 7. 78 words -> 200, duration_ms 40.4, within
 8. 54 words -> 200, duration_ms 33.8, within
 9. 83 words -> 200, duration_ms 83.4, within
10. 42 words -> 200, duration_ms 39.4, within
```

### Trial 2: 10/10 (pass)

```text
warm-up -> 200, duration_ms 54.9, cold_start False
GET /health -> detector_loaded: True
 1. 86 words -> 200, duration_ms 52.2, within
    {"timestamp": "2026-11-12T02:44:31.533+00:00", "request_id": "r_d2723fb07b69", "method": "POST", "path": "/submit", "input": {"body_bytes": 549, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c4_88792b_t2_00", "text_chars": 494, "text_words": 86, "text_preview": "Few nations in the world share polarizing views among people"}, "output": {"status_code": 200, "content_id": "c_2446ee43ad3d", "guess": "unsure", "confidence": 0.5259, "model_score": 0.5643, "style_score": 0.4874, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 52.2, "cpu_ms": 68.6, "cold_start": false, "stages_ms": {"model": 50.5, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
 2. 51 words -> 200, duration_ms 37.7, within
 3. 62 words -> 200, duration_ms 40.6, within
 4. 48 words -> 200, duration_ms 33.9, within
 5. 54 words -> 200, duration_ms 40.6, within
 6. 58 words -> 200, duration_ms 39.0, within
 7. 78 words -> 200, duration_ms 44.6, within
 8. 54 words -> 200, duration_ms 34.3, within
 9. 83 words -> 200, duration_ms 47.9, within
10. 42 words -> 200, duration_ms 33.4, within
```

### Trial 3: 10/10 (pass)

```text
warm-up -> 200, duration_ms 65.8, cold_start False
GET /health -> detector_loaded: True
 1. 86 words -> 200, duration_ms 48.0, within
    {"timestamp": "2026-11-12T02:44:32.029+00:00", "request_id": "r_862c6bf2e7fb", "method": "POST", "path": "/submit", "input": {"body_bytes": 549, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c4_88792b_t3_00", "text_chars": 494, "text_words": 86, "text_preview": "Few nations in the world share polarizing views among people"}, "output": {"status_code": 200, "content_id": "c_2d5db3a68bf9", "guess": "unsure", "confidence": 0.5259, "model_score": 0.5643, "style_score": 0.4874, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 48.0, "cpu_ms": 65.3, "cold_start": false, "stages_ms": {"model": 46.2, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
 2. 51 words -> 200, duration_ms 34.3, within
 3. 62 words -> 200, duration_ms 44.0, within
 4. 48 words -> 200, duration_ms 37.0, within
 5. 54 words -> 200, duration_ms 39.9, within
 6. 58 words -> 200, duration_ms 41.8, within
 7. 78 words -> 200, duration_ms 54.2, within
 8. 54 words -> 200, duration_ms 37.1, within
 9. 83 words -> 200, duration_ms 47.5, within
10. 42 words -> 200, duration_ms 35.9, within
```

## Criterion 5: Appeals preserve the original evidence

Target: 4 of 4 checks, in each of three trials. Produced by `run_capstone.py::criterion_5`.

### Trial 1: 4/4 (pass)

```text
POST /submit -> 200 {"content_id": "c_4c673eecbf5d", "guess": "unsure", "confidence": 0.5478, "model_score": 0.3913, "style_score": 0.7044}
POST /appeal -> 200 {"appealed_at": "2026-11-12T02:44:35+00:00", "content_id": "c_4c673eecbf5d", "message": "Thank you. Your appeal has been recorded and this piece is now marked a
    audit: {"combined_score": 0.5478, "content_id": "c_4c673eecbf5d", "creator_id": "c5_88792b_t1", "guess": "unsure", "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it
    audit: {"content_id": "c_4c673eecbf5d", "creator_id": "c5_88792b_t1", "event": "appeal", "reasoning": "I wrote this myself for a history class.", "status": "under_review", "timestamp": "2026-11-12T02:44:35+00:00"}
GET /content/c_4c673eecbf5d -> 200 {"status": "under_review", "confidence": 0.5478, "model_score": 0.3913, "style_score": 0.7044}
```

### Trial 2: 4/4 (pass)

```text
POST /submit -> 200 {"content_id": "c_b76d78d32e6f", "guess": "unsure", "confidence": 0.6937, "model_score": 0.6715, "style_score": 0.7159}
POST /appeal -> 200 {"appealed_at": "2026-11-12T02:44:36+00:00", "content_id": "c_b76d78d32e6f", "message": "Thank you. Your appeal has been recorded and this piece is now marked a
    audit: {"combined_score": 0.6937, "content_id": "c_b76d78d32e6f", "creator_id": "c5_88792b_t2", "guess": "unsure", "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it
    audit: {"content_id": "c_b76d78d32e6f", "creator_id": "c5_88792b_t2", "event": "appeal", "reasoning": "I wrote this myself for a history class.", "status": "under_review", "timestamp": "2026-11-12T02:44:36+00:00"}
GET /content/c_b76d78d32e6f -> 200 {"status": "under_review", "confidence": 0.6937, "model_score": 0.6715, "style_score": 0.7159}
```

### Trial 3: 4/4 (pass)

```text
POST /submit -> 200 {"content_id": "c_4c05c2fd097a", "guess": "unsure", "confidence": 0.5871, "model_score": 0.5793, "style_score": 0.5949}
POST /appeal -> 200 {"appealed_at": "2026-11-12T02:44:36+00:00", "content_id": "c_4c05c2fd097a", "message": "Thank you. Your appeal has been recorded and this piece is now marked a
    audit: {"combined_score": 0.5871, "content_id": "c_4c05c2fd097a", "creator_id": "c5_88792b_t3", "guess": "unsure", "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it
    audit: {"content_id": "c_4c05c2fd097a", "creator_id": "c5_88792b_t3", "event": "appeal", "reasoning": "I wrote this myself for a history class.", "status": "under_review", "timestamp": "2026-11-12T02:44:36+00:00"}
GET /content/c_4c05c2fd097a -> 200 {"status": "under_review", "confidence": 0.5871, "model_score": 0.5793, "style_score": 0.5949}
```
