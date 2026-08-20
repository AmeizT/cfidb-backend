class PaddleOcrEngine:
    def __init__(self, lang="en", use_angle_cls=True):
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise ValueError(
                "PaddleOCR is not installed. Install paddleocr and paddlepaddle."
            ) from exc

        try:
            self.ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)
        except (TypeError, ValueError):
            self.ocr = PaddleOCR(
                use_textline_orientation=use_angle_cls,
                lang=lang,
            )

    def extract_text(self, image_path):
        result = self.run_ocr(image_path)
        entries = self.flatten_result(result)

        lines = []
        boxes = []
        detections = []
        confidences = []

        for entry in entries:
            parsed = self.parse_entry(entry)
            if not parsed:
                continue

            box, text, confidence = parsed
            boxes.append(box)
            lines.append(text)
            detections.append({
                "text": text,
                "box": box,
                "confidence": confidence,
            })

            if confidence is not None:
                confidences.append(float(confidence))

        raw_text = "\n".join(lines)
        confidence = (
            sum(confidences) / len(confidences)
            if confidences
            else 0
        )

        return {
            "raw_text": raw_text,
            "text_lines": lines,
            "bounding_boxes": boxes,
            "detections": detections,
            "confidence": round(confidence, 4),
        }

    def run_ocr(self, image_path):
        if hasattr(self.ocr, "predict"):
            return self.ocr.predict(image_path)

        return self.ocr.ocr(image_path, cls=True)

    def flatten_result(self, result):
        if not result:
            return []

        entries = []

        for page in result:
            if page is None:
                continue

            dict_result = self.result_to_dict(page)

            if dict_result:
                entries.extend(self.flatten_dict_result(dict_result))
            elif self.is_ocr_entry(page):
                entries.append(page)
            else:
                entries.extend(page)

        return entries

    def result_to_dict(self, value):
        if isinstance(value, dict):
            return value.get("res", value)

        if hasattr(value, "res"):
            return getattr(value, "res")

        if hasattr(value, "to_dict"):
            result = value.to_dict()
            return result.get("res", result)

        return None

    def flatten_dict_result(self, result):
        texts = self.get_result_value(result, "rec_texts")
        scores = self.get_result_value(result, "rec_scores")
        boxes = self.get_result_value(result, "rec_polys", "rec_boxes")

        if texts is None:
            texts = []

        if scores is None:
            scores = []

        if boxes is None:
            boxes = []

        entries = []

        for index, text in enumerate(texts):
            entries.append({
                "text": text,
                "confidence": self.get_index(scores, index),
                "box": self.make_json_safe(self.get_index(boxes, index)),
            })

        return entries

    def get_result_value(self, result, *keys):
        for key in keys:
            value = result.get(key)

            if value is not None:
                return value

        return None

    def get_index(self, values, index):
        if values is None:
            return None

        try:
            return values[index]
        except (IndexError, TypeError):
            return None

    def is_ocr_entry(self, value):
        return (
            isinstance(value, (list, tuple))
            and len(value) >= 2
            and isinstance(value[1], (list, tuple))
            and len(value[1]) >= 2
            and isinstance(value[1][0], str)
        )

    def parse_entry(self, entry):
        if isinstance(entry, dict):
            text = str(entry.get("text", "")).strip()

            if not text:
                return None

            return (
                entry.get("box"),
                text,
                entry.get("confidence"),
            )

        if not self.is_ocr_entry(entry):
            return None

        box = self.make_json_safe(entry[0])
        text = entry[1][0].strip()
        confidence = entry[1][1]

        if not text:
            return None

        return box, text, confidence

    def make_json_safe(self, value):
        if hasattr(value, "tolist"):
            return value.tolist()

        if isinstance(value, tuple):
            return [self.make_json_safe(item) for item in value]

        if isinstance(value, list):
            return [self.make_json_safe(item) for item in value]

        return value
