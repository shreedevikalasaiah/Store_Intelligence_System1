
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ultralytics import YOLO
import supervision as sv
import cv2
import shutil
from datetime import datetime, timedelta, timezone

from pipeline.tracker import VisitorTracker
from pipeline.emit import make_event, emit_to_file

STORE_ID   = "ST1008"
SKIP       = 5
CLIP_START = datetime(2026, 4, 10, 12, 42, 0, tzinfo=timezone.utc)

CAMERA_CONFIG = {
    "CAM 1.mp4": {"camera_id": "CAM_ENTRY_01",  "zone_id": "ENTRY_ZONE",   "is_entry": True},
    "CAM 2.mp4": {"camera_id": "CAM_FLOOR_01",  "zone_id": "MAIN_FLOOR",   "is_entry": False},
    "CAM 3.mp4": {"camera_id": "CAM_FLOOR_02",  "zone_id": "MAIN_FLOOR_2", "is_entry": False},
    "CAM 4.mp4": {"camera_id": "CAM_BILLING_01","zone_id": "BILLING_ZONE", "is_entry": False},
    "CAM 5.mp4": {"camera_id": "CAM_EXIT_01",   "zone_id": "EXIT_ZONE",    "is_entry": False},
}


def process_all(cam_base_path: str, output_path: str):
    local_model_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "yolov8n.pt"
    )
    model_path = os.environ.get("YOLO_MODEL_PATH", local_model_path)
    if not os.path.exists(model_path):
        print(f"⚠  Model file not found at {model_path}. Falling back to remote yolov8n model.")
        model_path = "yolov8n"

    model = YOLO(model_path)
    total_events = 0

    with open(output_path, "w") as out_f:
        for video_file, cam_cfg in CAMERA_CONFIG.items():
            video_path = os.path.join(cam_base_path, video_file)
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"⚠  Cannot open {video_file} — skipping")
                continue

            fps       = cap.get(cv2.CAP_PROP_FPS) or 15
            total     = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            bt        = sv.ByteTrack()
            tracker   = VisitorTracker(
                camera_id=cam_cfg["camera_id"],
                zone_id=cam_cfg["zone_id"],
                is_entry=cam_cfg["is_entry"]
            )
            frame_num = 0
            cam_count = 0

            print(f"\n📹 {video_file} | {total} frames | {total/fps/60:.1f} min")

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_num % SKIP == 0:
                    results    = model(frame, classes=[0], verbose=False)[0]
                    detections = sv.Detections.from_ultralytics(results)
                    detections = bt.update_with_detections(detections)
                    ts = (CLIP_START + timedelta(seconds=frame_num/fps)
                          ).strftime("%Y-%m-%dT%H:%M:%SZ")

                    q_depth = len(detections) if cam_cfg["zone_id"] == "BILLING_ZONE" else None

                    for i in range(len(detections)):
                        tid = (detections.tracker_id[i]
                               if detections.tracker_id is not None else None)
                        if tid is None:
                            continue

                        bbox = detections.xyxy[i]
                        cy   = float((bbox[1] + bbox[3]) / 2)
                        conf = (float(detections.confidence[i])
                                if detections.confidence is not None else 0.5)

                        staff = tracker.is_staff(frame, bbox)
                        visitor_id, etype, dwell = tracker.process_detection(
                            tid, cy, fps, SKIP)

                        if etype == "SKIP":
                            continue

                        event = make_event(
                            camera_id=cam_cfg["camera_id"],
                            visitor_id=visitor_id,
                            event_type=etype,
                            timestamp=ts,
                            zone_id=cam_cfg["zone_id"],
                            dwell_ms=dwell,
                            is_staff=staff,
                            confidence=conf,
                            queue_depth=q_depth,
                            sku_zone=cam_cfg["zone_id"],
                            session_seq=tracker.get_seq(visitor_id),
                        )
                        emit_to_file(event, out_f)
                        cam_count += 1

                frame_num += 1
                if frame_num % 500 == 0:
                    print(f"  Frame {frame_num}/{total} | Events: {cam_count}")

            cap.release()
            total_events += cam_count
            print(f"✅ {video_file} — {cam_count} events")

    print(f"\n✅ TOTAL: {total_events} events → {output_path}")
    return total_events


if __name__ == "__main__":
    cam_path = sys.argv[1] if len(sys.argv) > 1 else "cctv_footage"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "events_all.jsonl"
    process_all(cam_path, out_path)
