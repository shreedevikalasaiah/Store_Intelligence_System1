# DESIGN.md — Store Intelligence API

## Architecture Overview

The system is a four-stage pipeline:

## AI-Assisted Decisions

This section documents where and how AI is used to make operational decisions in the pipeline, and the rationale behind thresholds and fallbacks.

- Detection model: YOLOv8 (ultralytics) is used for person and product detection because of its speed/accuracy trade-off for edge/desktop use. We use `yolov8n` (nano) by default for low-latency demos, and recommend `yolov8m` or `yolov8l` for higher accuracy in production.

- Matching strategy: We apply a hybrid IoU-first matching strategy with a centroid-distance fallback. IoU is the primary signal (spatial overlap); if IoU is low or not applicable, we compute a normalized centroid-distance score. We accept a match when the best score >= 0.35. This value was chosen empirically to balance ID persistence vs false merges.

- Product inference: Products are associated with person boxes using IoU > 0.06. This low threshold accounts for small product bounding boxes relative to person boxes and brief occlusions when a hand holds an item.

- Confidence filtering: Detections are filtered by model confidence (default 0.3). For deployment, increase confidence to 0.5–0.7 to reduce false positives when lighting or camera quality is poor.

- Staff exclusion: We support explicit staff tags (e.g. `staff_tag` in metadata or wearing staff IDs). The pipeline can exclude `STAFF_*` visitor IDs from analytics and billing inference. A runtime configuration lists staff badge patterns or zones.

- Re-entry and session handling: Visitor IDs are persistent per camera session (e.g., `VIS_CAM_1_00042`). Cross-camera re-identification is out-of-scope for the current demo but noted as future work. If a visitor re-enters after a long gap (> 30 minutes), the system treats it as a new session by default; this timeout is configurable.

- AI-Assisted Parameter Tuning: The thresholds above (IoU 0.35, product IoU 0.06, confidence 0.3) are recommended starting points. We provide a small validation script (`pipeline/validate_thresholds.py`) to sweep thresholds against labeled video snippets and compute precision/recall for detection and matching. Use this to choose production thresholds per-store.

- Explainability & Auditing: Every match decision and event contains metadata (model confidence, IoU score, centroid distance) to support manual review and post-hoc auditing. This is critical for verifying AI-assisted decisions and debugging edge cases.

## Security and Privacy

The system only stores anonymized visitor IDs (no PII). Event payloads use hashed or synthetic visitor IDs and timestamps in ISO 8601 UTC. For compliance, store retention and masking are configurable in `app/main.py` and `app/database.py`.

