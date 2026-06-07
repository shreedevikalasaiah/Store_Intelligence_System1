

```md
# Key Design Choices

## 1. Event-based architecture
We chose event-based logging (JSONL) instead of direct DB writes because:
- scalable
- easy replay/debugging
- decouples pipeline from analytics

## 2. Lightweight FastAPI backend
FastAPI was chosen due to:
- high performance
- async support
- easy API generation for metrics layer

## 3. Rule-based anomaly detection
Instead of heavy ML models, we used statistical rules:
- moving average spikes
- threshold-based detection
Reason: reduces compute cost and improves interpretability

## 4. Model selection

- We selected YOLOv8 (ultralytics) for person and product detection because it offers fast inference and satisfactory accuracy on commodity GPUs and CPUs. For demo and low-latency scenarios we use `yolov8n`; for production higher-accuracy variants (`yolov8m`, `yolov8l`) are recommended.
- Alternative options considered: Detectron2 (accurate but heavier), MobileNet-SSD (lighter but lower accuracy). YOLOv8 provided the best balance for this project.

## 5. Schema design

- Events use a compact JSON structure to maximize write throughput and ease of streaming. Example schema (per-line JSONL):

	- `event_id` (string UUID)
	- `visitor_id` (string): `VIS_{CAM}_{hex}` or `STAFF_{CAM}_{hex}`
	- `event_type` (string): ENTRY, ZONE_DWELL, CHECKOUT, EXIT
	- `zone_id` (string): logical zone name
	- `timestamp` (ISO 8601 UTC)
	- `metadata` (object): free-form map including `product_count`, `sku_zone`, `model_confidence`, `iou_score`, `centroid_distance`, `at_checkout`, `staff_tag`

This design supports replay, auditing, and downstream analytics without tight coupling to a relational schema.

## 6. API architecture decisions

- Ingestion endpoint (`/events/ingest`) accepts batched JSON arrays for efficiency and idempotency. The backend stores raw events to SQLite (or S3 in a production deployment) and emits metrics asynchronously.
- Design goals:
	- **Batching** to reduce HTTP-overhead
	- **Idempotency**: event producers include deterministic `event_id` to avoid duplicates
	- **Observability**: include model confidence, IoU, and centroid distance in metadata
	- **Schema evolution**: use JSON metadata to allow backward-compatible extension of event fields

## 7. Staff exclusion & edge cases

- Staff are excluded from analytics by detection of staff zones or staff tags (metadata `staff_tag: true`). The ingestion path drops or marks staff events so they do not count in conversion metrics.
- Re-entry handling: default session timeout is 30 minutes. If a visitor leaves and returns within timeout, the same session is continued when re-identified by tracker. Adjust timeout per store.

