from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    label: str
    confidence: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def diagonal(self) -> float:
        return float(np.hypot(self.x2 - self.x1, self.y2 - self.y1))

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


class YoloDetector:
    PERSON_CLASS = 0
    PHONE_CLASS = 67
    LAPTOP_CLASS = 63
    BOOK_CLASS = 73

    def __init__(self, model_name: str = "yolov8n.pt") -> None:
        self._model = None
        self._model_name = model_name
        self._ok = False
        self._load_model()

    def _load_model(self) -> None:
        try:
            from ultralytics import YOLO

            self._model = YOLO(self._model_name)
            self._ok = True
        except Exception:
            self._model = None
            self._ok = False

    @property
    def ok(self) -> bool:
        return self._ok

    def detect(self, frame: np.ndarray) -> dict[str, Any]:
        if not self._ok or self._model is None:
            return {
                "persons": [],
                "phones": [],
                "tablets": [],
                "phone_near_person": False,
                "tablet_near_person": False,
                "tablet_detected": False,
            }

        results = self._model(
            frame,
            verbose=False,
            imgsz=640,
            classes=[
                self.PERSON_CLASS,
                self.PHONE_CLASS,
                self.LAPTOP_CLASS,
                self.BOOK_CLASS,
            ],
        )[0]
        persons: list[BoundingBox] = []
        phones: list[BoundingBox] = []
        tablets: list[BoundingBox] = []

        if results.boxes is None:
            return {
                "persons": persons,
                "phones": phones,
                "tablets": tablets,
                "phone_near_person": False,
                "tablet_near_person": False,
                "tablet_detected": False,
            }

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            bbox = BoundingBox(x1, y1, x2, y2, label=str(cls_id), confidence=conf)

            if cls_id == self.PERSON_CLASS and conf >= 0.35:
                bbox.label = "person"
                persons.append(bbox)
            elif cls_id == self.PHONE_CLASS and conf >= 0.25:
                bbox.label = "phone"
                phones.append(bbox)
            elif cls_id in {self.LAPTOP_CLASS, self.BOOK_CLASS} and conf >= 0.30:
                bbox.label = "tablet_candidate"
                if self._looks_like_tablet(bbox):
                    tablets.append(bbox)

        phone_near_person = self._object_near_person(persons, phones)
        tablet_near_person = self._object_near_person(persons, tablets)
        return {
            "persons": persons,
            "phones": phones,
            "tablets": tablets,
            "phone_near_person": phone_near_person,
            "tablet_near_person": tablet_near_person,
            "tablet_detected": len(tablets) > 0,
        }

    def _looks_like_tablet(self, bbox: BoundingBox) -> bool:
        width = bbox.x2 - bbox.x1
        height = bbox.y2 - bbox.y1
        if width <= 0 or height <= 0:
            return False
        aspect = max(width, height) / min(width, height)
        return bbox.diagonal >= 120 and aspect <= 2.2

    def _object_near_person(
        self,
        persons: list[BoundingBox],
        objects: list[BoundingBox],
        distance_threshold: float = 260.0,
    ) -> bool:
        if not persons or not objects:
            return False
        for obj in objects:
            for person in persons:
                if self._iou(obj, person) > 0.02 or self._distance(obj, person) < distance_threshold:
                    return True
        return False

    def _phone_near_person(self, persons: list[BoundingBox], phones: list[BoundingBox]) -> bool:
        return self._object_near_person(persons, phones)

    def phone_near_hand_or_face(
        self,
        phones: list[BoundingBox],
        hand_bboxes: list[tuple[float, float, float, float]],
        face_bbox: tuple[float, float, float, float] | None,
    ) -> bool:
        if not phones:
            return False
        targets = list(hand_bboxes)
        if face_bbox is not None:
            targets.append(face_bbox)
        if not targets:
            return False

        for phone in phones:
            phone_box = (phone.x1, phone.y1, phone.x2, phone.y2)
            for target in targets:
                if self._box_distance(phone_box, target) < 120:
                    return True
        return False

    @staticmethod
    def _distance(a: BoundingBox, b: BoundingBox) -> float:
        ax, ay = a.center
        bx, by = b.center
        return float(np.hypot(ax - bx, ay - by))

    @staticmethod
    def _iou(a: BoundingBox, b: BoundingBox) -> float:
        x_left = max(a.x1, b.x1)
        y_top = max(a.y1, b.y1)
        x_right = min(a.x2, b.x2)
        y_bottom = min(a.y2, b.y2)
        if x_right <= x_left or y_bottom <= y_top:
            return 0.0
        inter = (x_right - x_left) * (y_bottom - y_top)
        union = a.area + b.area - inter
        if union <= 0:
            return 0.0
        return inter / union

    @staticmethod
    def _box_distance(
        a: tuple[float, float, float, float],
        b: tuple[float, float, float, float],
    ) -> float:
        ax = (a[0] + a[2]) / 2
        ay = (a[1] + a[3]) / 2
        bx = (b[0] + b[2]) / 2
        by = (b[1] + b[3]) / 2
        return float(np.hypot(ax - bx, ay - by))
