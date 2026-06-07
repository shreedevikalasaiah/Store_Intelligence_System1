"""
tracker.py — Re-ID and visitor session management.

# PROMPT: Write a retail visitor tracking module that:
# - assigns unique visitor IDs per camera using ByteTrack
# - detects re-entry when same visitor returns after EXIT
# - determines entry/exit direction from Y-position movement
# - detects staff by uniform color (HSV blue/red range)
# - tracks dwell time accumulation per visitor
# CHANGES MADE: Added camera-prefix namespacing to prevent cross-camera
# ID collisions, tuned direction threshold to 25px for retail camera height,
# added torso-crop for staff detection instead of full-body crop.
"""
import cv2
import numpy as np


class VisitorTracker:
    """Manages visitor sessions, direction detection, and re-entry logic."""

    def __init__(self, camera_id: str, zone_id: str, is_entry: bool = False):
        self.camera_id   = camera_id
        self.zone_id     = zone_id
        self.is_entry    = is_entry
        self.sessions    = {}   # visitor_id -> {seq, dwell, last_dwell_emit, positions}
        self.exited      = set()
        self.cam_prefix  = camera_id[:8]

    def get_visitor_id(self, tracker_id: int) -> str:
        return f"VIS_{self.cam_prefix}_{tracker_id:05x}"

    def determine_direction(self, tracker_id: int, cy: float) -> str | None:
        """
        Track centroid Y positions. Moving down (increasing Y) = ENTRY.
        Moving up (decreasing Y) = EXIT. Returns None if undetermined.
        """
        vid = self.get_visitor_id(tracker_id)
        if vid not in self.sessions:
            return None

        positions = self.sessions[vid].get('positions', [])
        positions.append(cy)
        self.sessions[vid]['positions'] = positions

        if len(positions) >= 10:
            first_avg = sum(positions[:5]) / 5
            last_avg  = sum(positions[-5:]) / 5
            delta = last_avg - first_avg
            if delta > 25:
                return 'ENTRY'
            elif delta < -25:
                return 'EXIT'
        return None

    def is_staff(self, frame: np.ndarray, bbox) -> bool:
        """
        Detect staff by dominant uniform color in torso region.
        Checks HSV blue (100-130) and red (0-10, 170-180) ranges.
        Returns True if >25% of torso pixels match uniform range.
        """
        x1, y1, x2, y2 = map(int, bbox)
        h = y2 - y1
        torso_y1 = y1 + h // 3
        torso_y2 = y1 + 2 * h // 3
        crop = frame[torso_y1:torso_y2, x1:x2]
        if crop.size == 0:
            return False

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        blue = cv2.inRange(hsv, np.array([100, 50, 50]), np.array([130, 255, 255]))
        red1 = cv2.inRange(hsv, np.array([0, 50, 50]),   np.array([10, 255, 255]))
        red2 = cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))

        total = crop.shape[0] * crop.shape[1]
        if total == 0:
            return False

        blue_ratio = blue.sum() / (total * 255)
        red_ratio   = (red1 + red2).sum() / (total * 255)
        return blue_ratio > 0.25 or red_ratio > 0.25

    def process_detection(self, tracker_id: int, cy: float,
                          fps: float, skip: int) -> tuple[str, str, int]:
        """
        Returns (visitor_id, event_type, dwell_ms).
        Handles ENTRY/EXIT/REENTRY/ZONE_ENTER/ZONE_DWELL logic.
        """
        visitor_id = self.get_visitor_id(tracker_id)

        if visitor_id not in self.sessions:
            self.sessions[visitor_id] = {
                'seq': 0, 'dwell': 0,
                'last_dwell_emit': 0, 'positions': [cy]
            }
            if self.is_entry:
                etype = 'REENTRY' if visitor_id in self.exited else 'ENTRY'
            elif 'EXIT' in self.camera_id:
                etype = 'EXIT'
                self.exited.add(visitor_id)
            else:
                etype = 'ZONE_ENTER'
        else:
            self.sessions[visitor_id]['dwell'] += int(skip * 1000 / fps)
            dwell     = self.sessions[visitor_id]['dwell']
            last_emit = self.sessions[visitor_id]['last_dwell_emit']
            if dwell - last_emit >= 30000:
                self.sessions[visitor_id]['last_dwell_emit'] = dwell
                etype = 'ZONE_DWELL'
            else:
                return visitor_id, 'SKIP', 0

        self.sessions[visitor_id]['seq'] += 1
        return visitor_id, etype, self.sessions[visitor_id]['dwell']

    def get_seq(self, visitor_id: str) -> int:
        return self.sessions.get(visitor_id, {}).get('seq', 1)
