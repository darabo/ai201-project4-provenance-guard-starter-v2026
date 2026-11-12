# Capstone run: before

- When: 2026-11-11T21:36:47-05:00
- Code tested: commit `2d276f8`
- Service started with: `gunicorn app:app --bind 127.0.0.1:5000 --workers 1 --timeout 120`
- Run tag (appears in every creator_id this run used): `3133e8`
- Produced by: `python run_capstone.py --label before`

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Reproducible local run path | 2 of 2 checks (health, submit) per clean start | 2/2 | 2/2 | 2/2 | MET |
| 2. Complete structured run logging | 10 of 10 requests | 9/10 | 9/10 | 9/10 | MISSED |
| 3. Bad submission input is rejected and logged | 5 of 5 bodies | 5/5 | 5/5 | 5/5 | MET |
| 4. Warm submissions remain responsive | 9 of 10 within 500 ms | 10/10 | 10/10 | 10/10 | MET |
| 5. Appeals preserve the original evidence | 4 of 4 checks | 4/4 | 4/4 | 4/4 | MET |

## Criterion 1: Reproducible local run path

Target: 2 of 2 checks (health, submit) per clean start, in each of three trials. Produced by `run_capstone.py::criterion_1`.

### Trial 1: 2/2 (pass)

```text
source cloned: /Users/darabonakdar/ai201-project4-provenance-guard-starter-v2026
'Booting worker with pid' seen after 26.7s
last lines of the start output:
  perplexity     12.5
  model_signal   0.8864   (higher = more likely AI)
  [2026-11-11 21:35:27 -0500] [17651] [INFO] Starting gunicorn 23.0.0
  [2026-11-11 21:35:27 -0500] [17651] [INFO] Listening at: http://127.0.0.1:5000 (17651)
  [2026-11-11 21:35:27 -0500] [17651] [INFO] Using worker: sync
  [2026-11-11 21:35:27 -0500] [17687] [INFO] Booting worker with pid: 17687
GET /health -> 200 {"detector_loaded": false, "detector_model": "gpt2", "log_entries": 575, "ok": true, "rate_limiting": true}
POST /submit -> 200 {"confidence": 0.8137, "content_id": "c_7b79071cd586", "creator_id": "demo_instructor", "guess": "ai", "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wr
last record in the clone's logs/runs.jsonl:
  {"timestamp": "2026-11-12T02:35:27.731+00:00", "request_id": "r_0b30a6949ec0", "method": "POST", "path": "/submit", "input": {"body_bytes": 725, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "demo_instructor", "text_chars": 680, "text_words": 91, "text_preview": "The importance of effective time management cannot be overst"}, "output": {"status_code": 200, "content_id": "c_7b79071cd586", "guess": "ai", "confidence": 0.8137, "model_score": 0.7544, "style_score": 0.7145, "marker_score": 0.9943, "status": "decided"}, "outcome": "ok", "duration_ms": 2248.7, "cpu_ms": 1583.8, "cold_start": true, "stages_ms": {"model": 2247.0, "style": 0.2, "markers": 0.2, "scoring": 0.0}}
```

### Trial 2: 2/2 (pass)

```text
source cloned: /Users/darabonakdar/ai201-project4-provenance-guard-starter-v2026
'Booting worker with pid' seen after 28.2s
last lines of the start output:
  perplexity     12.5
  model_signal   0.8864   (higher = more likely AI)
  [2026-11-11 21:36:00 -0500] [17689] [INFO] Starting gunicorn 23.0.0
  [2026-11-11 21:36:00 -0500] [17689] [INFO] Listening at: http://127.0.0.1:5000 (17689)
  [2026-11-11 21:36:00 -0500] [17689] [INFO] Using worker: sync
  [2026-11-11 21:36:00 -0500] [17722] [INFO] Booting worker with pid: 17722
GET /health -> 200 {"detector_loaded": false, "detector_model": "gpt2", "log_entries": 575, "ok": true, "rate_limiting": true}
POST /submit -> 200 {"confidence": 0.8137, "content_id": "c_bdd77cdb8e22", "creator_id": "demo_instructor", "guess": "ai", "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wr
last record in the clone's logs/runs.jsonl:
  {"timestamp": "2026-11-12T02:36:00.429+00:00", "request_id": "r_713f32b15920", "method": "POST", "path": "/submit", "input": {"body_bytes": 725, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "demo_instructor", "text_chars": 680, "text_words": 91, "text_preview": "The importance of effective time management cannot be overst"}, "output": {"status_code": 200, "content_id": "c_bdd77cdb8e22", "guess": "ai", "confidence": 0.8137, "model_score": 0.7544, "style_score": 0.7145, "marker_score": 0.9943, "status": "decided"}, "outcome": "ok", "duration_ms": 1854.2, "cpu_ms": 1563.7, "cold_start": true, "stages_ms": {"model": 1852.2, "style": 0.2, "markers": 0.2, "scoring": 0.0}}
```

### Trial 3: 2/2 (pass)

```text
source cloned: /Users/darabonakdar/ai201-project4-provenance-guard-starter-v2026
'Booting worker with pid' seen after 24.4s
last lines of the start output:
  perplexity     12.5
  model_signal   0.8864   (higher = more likely AI)
  [2026-11-11 21:36:28 -0500] [17724] [INFO] Starting gunicorn 23.0.0
  [2026-11-11 21:36:28 -0500] [17724] [INFO] Listening at: http://127.0.0.1:5000 (17724)
  [2026-11-11 21:36:28 -0500] [17724] [INFO] Using worker: sync
  [2026-11-11 21:36:28 -0500] [17736] [INFO] Booting worker with pid: 17736
GET /health -> 200 {"detector_loaded": false, "detector_model": "gpt2", "log_entries": 575, "ok": true, "rate_limiting": true}
POST /submit -> 200 {"confidence": 0.8137, "content_id": "c_f1b9c239cc00", "creator_id": "demo_instructor", "guess": "ai", "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wr
last record in the clone's logs/runs.jsonl:
  {"timestamp": "2026-11-12T02:36:28.993+00:00", "request_id": "r_848b994c8cae", "method": "POST", "path": "/submit", "input": {"body_bytes": 725, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "demo_instructor", "text_chars": 680, "text_words": 91, "text_preview": "The importance of effective time management cannot be overst"}, "output": {"status_code": 200, "content_id": "c_f1b9c239cc00", "guess": "ai", "confidence": 0.8137, "model_score": 0.7544, "style_score": 0.7145, "marker_score": 0.9943, "status": "decided"}, "outcome": "ok", "duration_ms": 2143.7, "cpu_ms": 1551.6, "cold_start": true, "stages_ms": {"model": 2141.9, "style": 0.2, "markers": 0.2, "scoring": 0.0}}
```

## Criterion 2: Complete structured run logging

Target: 10 of 10 requests, in each of three trials. Produced by `run_capstone.py::criterion_2`.

### Trial 1: 9/10 (FAIL)

```text
 1. GET /health -> 200  r_319de5bacbd3  ok
 2. POST /submit -> 200  r_ac7fb41ff53f  ok
 3. POST /submit -> 200  r_536e192607fc  ok
 4. POST /submit -> 200  r_b1978c40682b  ok
 5. POST /submit -> 200  r_f024ef0294ec  ok
 6. POST /submit -> 400  r_19068964b076  ok
 7. POST /submit -> 400  r_f12685745cf2  ok
 8. POST /appeal -> 200  r_17187aa1a9bc  ok
 9. POST /appeal -> 404  r_9e58a5832dea  ok
10. GET /submitt -> 404  r_5b1241aaba3f  FAIL: output has no error
    {"timestamp": "2026-11-12T02:36:36.724+00:00", "request_id": "r_5b1241aaba3f", "method": "GET", "path": "/submitt", "input": {"body_bytes": 0, "body_type": "empty"}, "output": {"status_code": 404}, "outcome": "rejected", "duration_ms": 0.1, "cpu_ms": 0.1, "cold_start": false}
```

### Trial 2: 9/10 (FAIL)

```text
 1. GET /health -> 200  r_02a888638872  ok
 2. POST /submit -> 200  r_6a69dabcabf3  ok
 3. POST /submit -> 200  r_76413bb69ed2  ok
 4. POST /submit -> 200  r_19fc01cefd44  ok
 5. POST /submit -> 200  r_0e40521939f0  ok
 6. POST /submit -> 400  r_816c3b067d47  ok
 7. POST /submit -> 400  r_9d8d16f0c060  ok
 8. POST /appeal -> 200  r_8b815e68426a  ok
 9. POST /appeal -> 404  r_db89a8e9af19  ok
10. GET /submitt -> 404  r_58fd2706cbcd  FAIL: output has no error
    {"timestamp": "2026-11-12T02:36:36.929+00:00", "request_id": "r_58fd2706cbcd", "method": "GET", "path": "/submitt", "input": {"body_bytes": 0, "body_type": "empty"}, "output": {"status_code": 404}, "outcome": "rejected", "duration_ms": 0.1, "cpu_ms": 0.1, "cold_start": false}
```

### Trial 3: 9/10 (FAIL)

```text
 1. GET /health -> 200  r_3040bca20e3d  ok
 2. POST /submit -> 200  r_64ea1efb26dc  ok
 3. POST /submit -> 200  r_8dd4034ed943  ok
 4. POST /submit -> 200  r_68fbac4015e5  ok
 5. POST /submit -> 200  r_7c8b30a7f639  ok
 6. POST /submit -> 400  r_fe18dbbdc2f9  ok
 7. POST /submit -> 400  r_5b37f5e1b7e5  ok
 8. POST /appeal -> 200  r_9985beae3397  ok
 9. POST /appeal -> 404  r_7262f55de58c  ok
10. GET /submitt -> 404  r_aee4af003f28  FAIL: output has no error
    {"timestamp": "2026-11-12T02:36:37.107+00:00", "request_id": "r_aee4af003f28", "method": "GET", "path": "/submitt", "input": {"body_bytes": 0, "body_type": "empty"}, "output": {"status_code": 404}, "outcome": "rejected", "duration_ms": 0.1, "cpu_ms": 0.1, "cold_start": false}
```

## Criterion 3: Bad submission input is rejected and logged

Target: 5 of 5 bodies, in each of three trials. Produced by `run_capstone.py::criterion_3`.

### Trial 1: 5/5 (pass)

```text
missing text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:36:38.321+00:00", "request_id": "r_30562a1abb0d", "method": "POST", "path": "/submit", "input": {"body_bytes": 34, "body_type": "object", "fields": ["creator_id"], "creator_id": "c3_3133e8_trial1"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.7, "cpu_ms": 0.8, "cold_start": true}
empty text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:36:38.324+00:00", "request_id": "r_7be1819eca1e", "method": "POST", "path": "/submit", "input": {"body_bytes": 46, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial1", "text_chars": 0, "text_words": 0, "text_preview": ""}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
whitespace-only text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:36:38.327+00:00", "request_id": "r_b66523e6f1d7", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial1", "text_chars": 3, "text_words": 0, "text_preview": "   "}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
non-string text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:36:38.329+00:00", "request_id": "r_62545b7e8d07", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial1"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
JSON array: -> 400 {"error": "bad_request", "message": "Send a JSON object like {\"text\": \"...\", \"creator_id\": \"...\"}."}  ok
    {"timestamp": "2026-11-12T02:36:38.331+00:00", "request_id": "r_dd9f71e56ddc", "method": "POST", "path": "/submit", "input": {"body_bytes": 9, "body_type": "list"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
```

### Trial 2: 5/5 (pass)

```text
missing text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:36:38.332+00:00", "request_id": "r_85c3227c9cd4", "method": "POST", "path": "/submit", "input": {"body_bytes": 34, "body_type": "object", "fields": ["creator_id"], "creator_id": "c3_3133e8_trial2"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
empty text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:36:38.334+00:00", "request_id": "r_c68a8ac2f706", "method": "POST", "path": "/submit", "input": {"body_bytes": 46, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial2", "text_chars": 0, "text_words": 0, "text_preview": ""}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
whitespace-only text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:36:38.336+00:00", "request_id": "r_86649b3bc79e", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial2", "text_chars": 3, "text_words": 0, "text_preview": "   "}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
non-string text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:36:38.337+00:00", "request_id": "r_c8f60ba26c02", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial2"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
JSON array: -> 400 {"error": "bad_request", "message": "Send a JSON object like {\"text\": \"...\", \"creator_id\": \"...\"}."}  ok
    {"timestamp": "2026-11-12T02:36:38.339+00:00", "request_id": "r_b21d366b43fb", "method": "POST", "path": "/submit", "input": {"body_bytes": 9, "body_type": "list"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.1, "cpu_ms": 0.1, "cold_start": true}
```

### Trial 3: 5/5 (pass)

```text
missing text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:36:38.340+00:00", "request_id": "r_3da3c0ad4566", "method": "POST", "path": "/submit", "input": {"body_bytes": 34, "body_type": "object", "fields": ["creator_id"], "creator_id": "c3_3133e8_trial3"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
empty text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:36:38.341+00:00", "request_id": "r_2ddf58c0d1bc", "method": "POST", "path": "/submit", "input": {"body_bytes": 46, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial3", "text_chars": 0, "text_words": 0, "text_preview": ""}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
whitespace-only text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:36:38.343+00:00", "request_id": "r_5ae2086bff37", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial3", "text_chars": 3, "text_words": 0, "text_preview": "   "}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
non-string text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:36:38.344+00:00", "request_id": "r_e0771af19340", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial3"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
JSON array: -> 400 {"error": "bad_request", "message": "Send a JSON object like {\"text\": \"...\", \"creator_id\": \"...\"}."}  ok
    {"timestamp": "2026-11-12T02:36:38.346+00:00", "request_id": "r_8f075a861013", "method": "POST", "path": "/submit", "input": {"body_bytes": 9, "body_type": "list"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
```

## Criterion 4: Warm submissions remain responsive

Target: 9 of 10 within 500 ms, in each of three trials. Produced by `run_capstone.py::criterion_4`.

### Trial 1: 10/10 (pass)

```text
warm-up -> 200, duration_ms 2203.4, cold_start True
GET /health -> detector_loaded: True
 1. 86 words -> 200, duration_ms 47.8, within
    {"timestamp": "2026-11-12T02:36:41.446+00:00", "request_id": "r_e9d849ee0556", "method": "POST", "path": "/submit", "input": {"body_bytes": 549, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c4_3133e8_t1_00", "text_chars": 494, "text_words": 86, "text_preview": "Few nations in the world share polarizing views among people"}, "output": {"status_code": 200, "content_id": "c_a1629da39dfd", "guess": "unsure", "confidence": 0.5259, "model_score": 0.5643, "style_score": 0.4874, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 47.8, "cpu_ms": 66.3, "cold_start": false, "stages_ms": {"model": 46.1, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
 2. 51 words -> 200, duration_ms 33.8, within
 3. 62 words -> 200, duration_ms 39.9, within
 4. 48 words -> 200, duration_ms 34.0, within
 5. 54 words -> 200, duration_ms 38.4, within
 6. 58 words -> 200, duration_ms 38.2, within
 7. 78 words -> 200, duration_ms 41.6, within
 8. 54 words -> 200, duration_ms 32.7, within
 9. 83 words -> 200, duration_ms 45.3, within
10. 42 words -> 200, duration_ms 32.1, within
```

### Trial 2: 10/10 (pass)

```text
warm-up -> 200, duration_ms 47.0, cold_start False
GET /health -> detector_loaded: True
 1. 86 words -> 200, duration_ms 46.8, within
    {"timestamp": "2026-11-12T02:36:41.897+00:00", "request_id": "r_e587019f1bbe", "method": "POST", "path": "/submit", "input": {"body_bytes": 549, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c4_3133e8_t2_00", "text_chars": 494, "text_words": 86, "text_preview": "Few nations in the world share polarizing views among people"}, "output": {"status_code": 200, "content_id": "c_811d336927fd", "guess": "unsure", "confidence": 0.5259, "model_score": 0.5643, "style_score": 0.4874, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 46.8, "cpu_ms": 63.7, "cold_start": false, "stages_ms": {"model": 45.2, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
 2. 51 words -> 200, duration_ms 34.2, within
 3. 62 words -> 200, duration_ms 38.0, within
 4. 48 words -> 200, duration_ms 33.5, within
 5. 54 words -> 200, duration_ms 36.6, within
 6. 58 words -> 200, duration_ms 36.8, within
 7. 78 words -> 200, duration_ms 40.7, within
 8. 54 words -> 200, duration_ms 33.8, within
 9. 83 words -> 200, duration_ms 47.1, within
10. 42 words -> 200, duration_ms 32.7, within
```

### Trial 3: 10/10 (pass)

```text
warm-up -> 200, duration_ms 48.2, cold_start False
GET /health -> detector_loaded: True
 1. 86 words -> 200, duration_ms 49.8, within
    {"timestamp": "2026-11-12T02:36:42.348+00:00", "request_id": "r_92d4af40456b", "method": "POST", "path": "/submit", "input": {"body_bytes": 549, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c4_3133e8_t3_00", "text_chars": 494, "text_words": 86, "text_preview": "Few nations in the world share polarizing views among people"}, "output": {"status_code": 200, "content_id": "c_e9597aedd840", "guess": "unsure", "confidence": 0.5259, "model_score": 0.5643, "style_score": 0.4874, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 49.8, "cpu_ms": 67.1, "cold_start": false, "stages_ms": {"model": 48.2, "style": 0.2, "markers": 0.1, "scoring": 0.0}}
 2. 51 words -> 200, duration_ms 36.8, within
 3. 62 words -> 200, duration_ms 40.1, within
 4. 48 words -> 200, duration_ms 35.7, within
 5. 54 words -> 200, duration_ms 41.3, within
 6. 58 words -> 200, duration_ms 40.9, within
 7. 78 words -> 200, duration_ms 44.3, within
 8. 54 words -> 200, duration_ms 35.9, within
 9. 83 words -> 200, duration_ms 46.5, within
10. 42 words -> 200, duration_ms 35.0, within
```

## Criterion 5: Appeals preserve the original evidence

Target: 4 of 4 checks, in each of three trials. Produced by `run_capstone.py::criterion_5`.

### Trial 1: 4/4 (pass)

```text
POST /submit -> 200 {"content_id": "c_bb796c445be8", "guess": "unsure", "confidence": 0.5478, "model_score": 0.3913, "style_score": 0.7044}
POST /appeal -> 200 {"appealed_at": "2026-11-12T02:36:46+00:00", "content_id": "c_bb796c445be8", "message": "Thank you. Your appeal has been recorded and this piece is now marked a
    audit: {"combined_score": 0.5478, "content_id": "c_bb796c445be8", "creator_id": "c5_3133e8_t1", "guess": "unsure", "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it
    audit: {"content_id": "c_bb796c445be8", "creator_id": "c5_3133e8_t1", "event": "appeal", "reasoning": "I wrote this myself for a history class.", "status": "under_review", "timestamp": "2026-11-12T02:36:46+00:00"}
GET /content/c_bb796c445be8 -> 200 {"status": "under_review", "confidence": 0.5478, "model_score": 0.3913, "style_score": 0.7044}
```

### Trial 2: 4/4 (pass)

```text
POST /submit -> 200 {"content_id": "c_823f8923c59b", "guess": "unsure", "confidence": 0.6937, "model_score": 0.6715, "style_score": 0.7159}
POST /appeal -> 200 {"appealed_at": "2026-11-12T02:36:46+00:00", "content_id": "c_823f8923c59b", "message": "Thank you. Your appeal has been recorded and this piece is now marked a
    audit: {"combined_score": 0.6937, "content_id": "c_823f8923c59b", "creator_id": "c5_3133e8_t2", "guess": "unsure", "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it
    audit: {"content_id": "c_823f8923c59b", "creator_id": "c5_3133e8_t2", "event": "appeal", "reasoning": "I wrote this myself for a history class.", "status": "under_review", "timestamp": "2026-11-12T02:36:46+00:00"}
GET /content/c_823f8923c59b -> 200 {"status": "under_review", "confidence": 0.6937, "model_score": 0.6715, "style_score": 0.7159}
```

### Trial 3: 4/4 (pass)

```text
POST /submit -> 200 {"content_id": "c_fc90896eb8b8", "guess": "unsure", "confidence": 0.5871, "model_score": 0.5793, "style_score": 0.5949}
POST /appeal -> 200 {"appealed_at": "2026-11-12T02:36:46+00:00", "content_id": "c_fc90896eb8b8", "message": "Thank you. Your appeal has been recorded and this piece is now marked a
    audit: {"combined_score": 0.5871, "content_id": "c_fc90896eb8b8", "creator_id": "c5_3133e8_t3", "guess": "unsure", "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it
    audit: {"content_id": "c_fc90896eb8b8", "creator_id": "c5_3133e8_t3", "event": "appeal", "reasoning": "I wrote this myself for a history class.", "status": "under_review", "timestamp": "2026-11-12T02:36:46+00:00"}
GET /content/c_fc90896eb8b8 -> 200 {"status": "under_review", "confidence": 0.5871, "model_score": 0.5793, "style_score": 0.5949}
```
