import re
from collections.abc import Mapping
from difflib import SequenceMatcher
from statistics import median


class OcrReportParser:
    """
    Supports:
    - Key/value text: "Invoice Number: 0022"
    - OCR detections with PaddleOCR bounding boxes
    - Collapsed spreadsheet OCR lines with mixed labels and values
    - Separate/reversed OCR lines where labels and values are split
    - Basic table-style OCR text
    """

    NON_DATA_LABELS = {
        "assembly",
        "report",
        "createdby",
        "createddate",
        "preparedby",
        "timestamp",
    }

    NUMERIC_FIELDS = {"price", "amount", "quantity"}
    DATE_FIELDS = {
        "invoice_date",
        "date",
        "receipt_date",
        "purchase_date",
    }

    def __init__(self, field_mapper, non_data_labels=None):
        self.field_mapper = field_mapper

        self.non_data_labels = {
            self.field_mapper.normalize(value)
            for value in (non_data_labels or self.NON_DATA_LABELS)
        }

    def parse(self, raw_text="", text_lines=None, detections=None):
        source = (
            detections
            if detections is not None
            else text_lines
            if text_lines is not None
            else raw_text
        )
        lines, used_layout, positioned_items = self.prepare_lines(source)

        table_rows = self.parse_layout_table_rows(positioned_items)

        collapsed_table_rows = []

        if not table_rows:
            collapsed_table_rows = self.parse_collapsed_table_rows(lines)

        if not table_rows and not collapsed_table_rows:
            table_rows = self.parse_table_rows(lines)

        stacked_table_rows = []

        if not table_rows and not collapsed_table_rows:
            stacked_table_rows = self.parse_stacked_table_rows(lines)

        if table_rows:
            rows = table_rows
        elif collapsed_table_rows:
            rows = collapsed_table_rows
        elif stacked_table_rows:
            rows = stacked_table_rows
        else:
            inline_row = self.parse_key_value_row(lines)
            stacked_row = self.parse_stacked_key_value_row(lines)

            # Explicit label/value matches are more reliable than fallback
            # stacked-line matches, so they should win on duplicate fields.
            row = {**stacked_row, **inline_row}
            rows = [row] if row else []

        rows = [
            self.clean_row(self.field_mapper.map_row(row))
            for row in rows
        ]

        warnings = []

        if not rows:
            warnings.append(
                "No recognizable fields or table rows were found in the OCR text. "
                "Upload a clear image that includes the report labels and values."
            )
        elif not used_layout and self.has_stacked_labels(lines):
            warnings.append(
                "Some values were reconstructed from separate OCR lines. "
                "Review the extracted values before saving."
            )

        return {
            "rows": rows,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # OCR layout handling
    # ------------------------------------------------------------------

    def prepare_lines(self, source):
        positioned_items = self.extract_positioned_items(source)

        if positioned_items:
            return self.build_visual_lines(positioned_items), True, positioned_items

        if isinstance(source, str):
            raw_lines = source.splitlines()
        else:
            raw_lines = [
                self.extract_text_value(item)
                for item in (source or [])
            ]

        lines = [
            str(line).strip()
            for line in raw_lines
            if str(line).strip()
        ]

        return lines, False, []

    def extract_positioned_items(self, source):
        """
        Accepts either:

        1. Dicts:
           {"text": "Price", "bbox": [[x, y], ...]}

        2. Native PaddleOCR detections:
           [
               [[x, y], [x, y], [x, y], [x, y]],
               ("Price", confidence)
           ]
        """
        if not isinstance(source, (list, tuple)):
            return []

        items = []

        for item in source:
            text = None
            bbox = None

            if isinstance(item, Mapping):
                text = item.get("text")
                bbox = (
                    item.get("bbox")
                    or item.get("box")
                    or item.get("points")
                )

            elif (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and self.is_bbox(item[0])
                and isinstance(item[1], (list, tuple))
                and item[1]
                and isinstance(item[1][0], str)
            ):
                bbox = item[0]
                text = item[1][0]

            if text is None or not self.is_bbox(bbox):
                continue

            points = [
                (float(point[0]), float(point[1]))
                for point in bbox # type: ignore
            ]

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]

            items.append({
                "text": str(text).strip(),
                "left": min(xs),
                "right": max(xs),
                "top": min(ys),
                "bottom": max(ys),
                "center_x": (min(xs) + max(xs)) / 2,
                "center_y": (min(ys) + max(ys)) / 2,
                "width": max(1.0, max(xs) - min(xs)),
                "height": max(1.0, max(ys) - min(ys)),
            })

        return [item for item in items if item["text"]]

    def extract_text_value(self, item):
        if isinstance(item, Mapping):
            return item.get("text", "")

        if (
            isinstance(item, (list, tuple))
            and len(item) >= 2
            and isinstance(item[1], (list, tuple))
            and item[1]
            and isinstance(item[1][0], str)
        ):
            return item[1][0]

        return item

    def is_bbox(self, value):
        return (
            isinstance(value, (list, tuple))
            and len(value) >= 2
            and all(
                isinstance(point, (list, tuple))
                and len(point) >= 2
                and isinstance(point[0], (int, float))
                and isinstance(point[1], (int, float))
                for point in value
            )
        )

    def build_visual_lines(self, items):
        """
        Groups OCR words into approximate visual rows, then reads every
        row left-to-right.

        Example:
        Name + office + Chair
        becomes:
        Name office Chair
        """
        if not items:
            return []

        rows = self.group_positioned_rows(items)
        visual_lines = []

        for row in rows:
            text = " ".join(
                item["text"]
                for item in sorted(
                    row["items"],
                    key=lambda value: value["left"],
                )
            ).strip()

            if text:
                visual_lines.append(text)

        return visual_lines

    def group_positioned_rows(self, items):
        if not items:
            return []

        heights = [item["height"] for item in items]

        # A relaxed tolerance helps with handwritten text where words on
        # the same logical row may not align perfectly.
        line_tolerance = max(18.0, median(heights) * 1.8)

        rows = []

        for item in sorted(
            items,
            key=lambda value: (value["center_y"], value["left"]),
        ):
            matching_rows = [
                row
                for row in rows
                if abs(item["center_y"] - row["center_y"]) <= line_tolerance
            ]

            if not matching_rows:
                rows.append({
                    "center_y": item["center_y"],
                    "items": [item],
                })
                continue

            row = min(
                matching_rows,
                key=lambda value: abs(
                    item["center_y"] - value["center_y"]
                ),
            )

            row["items"].append(item)
            row["center_y"] = sum(
                value["center_y"]
                for value in row["items"]
            ) / len(row["items"])

        return sorted(rows, key=lambda value: value["center_y"])

    def parse_layout_table_rows(self, items):
        rows = self.group_positioned_rows(items)

        for row_index, row in enumerate(rows):
            header_cells = []

            for item in sorted(row["items"], key=lambda value: value["left"]):
                field = self.field_for_label_line(item["text"])

                if field:
                    header_cells.append({**item, "field": field})

            if len(header_cells) < 2:
                continue

            data_rows = []

            for value_row in rows[row_index + 1:]:
                value_cells = sorted(
                    value_row["items"],
                    key=lambda value: value["left"],
                )

                mapped_values = [
                    self.field_for_label_line(item["text"])
                    for item in value_cells
                ]

                if sum(1 for field in mapped_values if field) >= 2:
                    break

                parsed_row = self.map_layout_values_to_headers(
                    header_cells,
                    value_cells,
                )

                if parsed_row:
                    data_rows.append(parsed_row)

            if data_rows:
                return data_rows

        return []

    def map_layout_values_to_headers(self, header_cells, value_cells):
        if not header_cells or not value_cells:
            return {}

        row = {}
        header_cells = sorted(header_cells, key=lambda value: value["left"])
        value_cells = sorted(value_cells, key=lambda value: value["left"])

        if len(value_cells) == len(header_cells):
            pairs = zip(header_cells, value_cells)
        else:
            pairs = (
                (
                    min(
                        header_cells,
                        key=lambda header: abs(
                            value["center_x"] - header["center_x"]
                        ),
                    ),
                    value,
                )
                for value in value_cells
            )

        for header, value in pairs:
            field = header["field"]
            text = value["text"].strip()

            if not text:
                continue

            if field in row:
                row[field] = f"{row[field]} {text}"
            else:
                row[field] = text

        return row

    # ------------------------------------------------------------------
    # Standard key/value parsing
    # ------------------------------------------------------------------

    def parse_key_value_row(self, lines):
        row = {}

        for line in lines:
            parsed = self.parse_key_value_line(line)

            if not parsed:
                continue

            field, value = parsed
            row[field] = value

        return row

    def parse_key_value_rows(self, lines):
        row = self.parse_key_value_row(lines)
        return [row] if row else []

    def parse_key_value_line(self, line):
        for splitter in (":", "="):
            if splitter not in line:
                continue

            key, value = line.split(splitter, 1)
            field = self.field_mapper.map_field(key)

            if field and value.strip():
                return field, value.strip()

        dash_match = re.match(
            r"^\s*([A-Za-z][A-Za-z0-9 #_/]+?)\s+-\s+(.+)$",
            line,
        )

        if dash_match:
            field = self.field_mapper.map_field(dash_match.group(1))

            if field:
                return field, dash_match.group(2).strip()

        return self.parse_label_prefix(line)

    def parse_label_prefix(self, line):
        labels = []

        for canonical_field, aliases in self.field_mapper.field_map.items():
            labels.append((canonical_field, canonical_field))

            for alias in aliases:
                labels.append((canonical_field, alias))

        # Ensure "invoice date" is tested before "date".
        labels.sort(key=lambda item: len(item[1]), reverse=True)

        for canonical_field, label in labels:
            match = re.match(
                self.label_pattern(label),
                line,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            value = match.group(1).strip()

            if value:
                return canonical_field, value

        return None

    def label_pattern(self, label):
        parts = re.split(r"\s+", str(label).strip())
        escaped_parts = [
            re.escape(part)
            for part in parts
            if part
        ]

        return (
            r"^\s*"
            + r"\s+".join(escaped_parts)
            + r"(?:\s*[:=-]\s*|\s+)(.+?)\s*$"
        )

    # ------------------------------------------------------------------
    # Fallback for OCR that collapses a spreadsheet into one text line
    # ------------------------------------------------------------------

    def parse_collapsed_table_rows(self, lines):
        if len(lines) > 2 and not any("|" in str(line) for line in lines):
            return []

        text = " ".join(str(line).strip() for line in lines if str(line).strip())

        if not text:
            return []

        tokens = self.tokenize_collapsed_text(text)
        labels = self.find_embedded_labels(tokens)

        if len(labels) < 3:
            return []

        label_fields = {label["field"] for label in labels}

        if not ({"invoice_date", "invoice_number"} & label_fields):
            return []

        row = {}
        used_indices = self.label_token_indices(labels)

        value_indices = [
            index
            for index in range(len(tokens))
            if index not in used_indices
        ]

        self.extract_typed_collapsed_values(row, tokens, value_indices, used_indices)
        self.extract_text_collapsed_values(row, tokens, labels, used_indices)
        self.extract_remaining_numeric_collapsed_values(
            row,
            tokens,
            value_indices,
            used_indices,
        )

        return [row] if row else []

    def tokenize_collapsed_text(self, text):
        return [
            token
            for token in re.split(r"[\s|]+", text)
            if token
        ]

    def find_embedded_labels(self, tokens):
        labels = []
        index = 0
        max_label_words = max(
            len(str(label).split())
            for labels in self.field_mapper.field_map.values()
            for label in labels
        )

        while index < len(tokens):
            match = None

            for size in range(max_label_words, 0, -1):
                candidate_tokens = tokens[index:index + size]

                if len(candidate_tokens) != size:
                    continue

                candidate = " ".join(candidate_tokens)
                field = self.field_for_embedded_label(candidate, size)

                if not field:
                    continue

                match = {
                    "field": field,
                    "start": index,
                    "end": index + size,
                }
                break

            if match:
                labels.append(match)
                index = match["end"]
            else:
                index += 1

        return self.dedupe_embedded_labels(labels)

    def field_for_embedded_label(self, value, token_count):
        normalized = self.field_mapper.normalize(value)
        exact_field = self.field_mapper.aliases.get(normalized)

        if exact_field:
            return exact_field

        if token_count < 2:
            return None

        best_field = None
        best_score = 0

        for field, labels in self.field_mapper.field_map.items():
            candidates = [field, *labels]

            for label in candidates:
                if len(str(label).split()) != token_count:
                    continue

                score = self.similarity(
                    normalized,
                    self.field_mapper.normalize(label),
                )

                if score > best_score:
                    best_field = field
                    best_score = score

        return best_field if best_score >= 0.82 else None

    def dedupe_embedded_labels(self, labels):
        deduped = []
        seen_positions = set()

        for label in labels:
            position = (label["start"], label["end"])

            if position in seen_positions:
                continue

            seen_positions.add(position)
            deduped.append(label)

        return deduped

    def label_token_indices(self, labels):
        indices = set()

        for label in labels:
            indices.update(range(label["start"], label["end"]))

        return indices

    def extract_typed_collapsed_values(self, row, tokens, value_indices, used_indices):
        value_text = self.join_tokens(tokens, value_indices)

        date_match = re.search(
            r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
            value_text,
        )

        if date_match:
            row["invoice_date"] = date_match.group(0)
            self.mark_matching_tokens(tokens, value_indices, date_match.group(0), used_indices)

        invoice_match = re.search(
            r"\b[A-Z]{2,}[-/]?\d+[A-Z0-9/-]*\b",
            value_text,
            flags=re.IGNORECASE,
        )

        if invoice_match:
            invoice_number = invoice_match.group(0)

            if not self.looks_like_date(invoice_number):
                row["invoice_number"] = invoice_number
                self.mark_matching_tokens(tokens, value_indices, invoice_number, used_indices)

    def extract_text_collapsed_values(self, row, tokens, labels, used_indices):
        label_by_field = {
            label["field"]: label
            for label in labels
            if label["field"] not in row
        }

        for field in ("name", "description", "category", "supplier"):
            label = label_by_field.get(field)

            if not label:
                continue

            value = self.collapsed_value_before_label(tokens, labels, label, used_indices)

            if not value:
                value = self.collapsed_value_after_label(tokens, labels, label, used_indices)

            if value and self.value_score(field, value) > 0:
                row[field] = value
                self.mark_text_tokens(tokens, value, used_indices)

    def extract_remaining_numeric_collapsed_values(self, row, tokens, value_indices, used_indices):
        numeric_tokens = [
            (index, tokens[index])
            for index in value_indices
            if index not in used_indices
            and re.fullmatch(r"\d+(?:\.\d+)?", tokens[index].replace(",", ""))
        ]

        if "quantity" not in row and numeric_tokens:
            index, quantity = numeric_tokens[0]
            row["quantity"] = quantity
            used_indices.add(index)
            numeric_tokens = numeric_tokens[1:]

        if "price" not in row and numeric_tokens:
            index, price = numeric_tokens[-1]
            row["price"] = price
            used_indices.add(index)

    def collapsed_value_before_label(self, tokens, labels, label, used_indices):
        previous_label = self.previous_label(labels, label)
        start = previous_label["end"] if previous_label else 0
        indices = [
            index
            for index in range(start, label["start"])
            if index not in used_indices
        ]

        return self.join_tokens(tokens, indices)

    def collapsed_value_after_label(self, tokens, labels, label, used_indices):
        next_label = self.next_label(labels, label)
        end = next_label["start"] if next_label else len(tokens)
        indices = [
            index
            for index in range(label["end"], end)
            if index not in used_indices
        ]

        return self.join_tokens(tokens, indices)

    def previous_label(self, labels, label):
        previous_labels = [
            item for item in labels if item["end"] <= label["start"]
        ]

        return previous_labels[-1] if previous_labels else None

    def next_label(self, labels, label):
        next_labels = [
            item for item in labels if item["start"] >= label["end"]
        ]

        return next_labels[0] if next_labels else None

    def join_tokens(self, tokens, indices):
        return " ".join(tokens[index] for index in indices).strip()

    def mark_matching_tokens(self, tokens, candidate_indices, value, used_indices):
        value_tokens = self.tokenize_collapsed_text(value)

        if not value_tokens:
            return

        for offset in range(len(candidate_indices)):
            window_indices = candidate_indices[offset:offset + len(value_tokens)]

            if len(window_indices) != len(value_tokens):
                continue

            window_tokens = [tokens[index] for index in window_indices]

            if self.field_mapper.normalize(" ".join(window_tokens)) == self.field_mapper.normalize(value):
                used_indices.update(window_indices)
                return

    def mark_text_tokens(self, tokens, value, used_indices):
        value_tokens = self.tokenize_collapsed_text(value)

        for offset in range(len(tokens)):
            window_tokens = tokens[offset:offset + len(value_tokens)]

            if self.field_mapper.normalize(" ".join(window_tokens)) == self.field_mapper.normalize(value):
                used_indices.update(range(offset, offset + len(value_tokens)))
                return

    def similarity(self, left, right):
        return SequenceMatcher(None, left, right).ratio()

    # ------------------------------------------------------------------
    # Fallback for split or reversed OCR output
    # ------------------------------------------------------------------

    def parse_stacked_key_value_row(self, lines):
        row = {}

        for index, line in enumerate(lines):
            field = self.exact_field_for_line(line)

            if not field:
                continue

            value = self.find_stacked_value(lines, index, field)

            if value:
                row[field] = value

        return row

    def parse_stacked_table_rows(self, lines):
        """
        Handles OCR text ordered as:

        Invoice Date
        Invoice Number
        Name
        ...
        2026-03-10
        INV-001
        Bar Fridge
        ...

        PaddleOCR can emit this when it reads a horizontal table column by
        column or header block first, then value block.
        """
        for start_index in range(len(lines)):
            fields = []
            index = start_index

            while index < len(lines):
                field = self.field_for_label_line(lines[index])

                if not field:
                    break

                fields.append(field)
                index += 1

            if len(fields) < 2:
                continue

            values = []
            value_index = index

            while (
                value_index < len(lines)
                and len(values) < len(fields)
            ):
                value = str(lines[value_index]).strip()

                if not value:
                    value_index += 1
                    continue

                if self.exact_field_for_line(value):
                    break

                values.append(value)
                value_index += 1

            if len(values) < 2:
                continue

            values += [""] * max(0, len(fields) - len(values))
            return [dict(zip(fields, values[:len(fields)]))]

        return []

    def exact_field_for_line(self, line):
        normalized = self.field_mapper.normalize(line)
        return self.field_mapper.aliases.get(normalized)

    def field_for_label_line(self, line):
        normalized = self.field_mapper.normalize(line)

        if normalized in self.non_data_labels:
            return None

        return (
            self.exact_field_for_line(line)
            or self.field_mapper.map_field(line)
        )

    def has_stacked_labels(self, lines):
        return any(
            self.exact_field_for_line(line)
            for line in lines
        )

    def find_stacked_value(self, lines, index, field):
        candidates = []

        before = self.collect_value_run(lines, index - 1, step=-1)
        after = self.collect_value_run(lines, index + 1, step=1)

        if before:
            # Closest value before the label.
            candidates.append((before[-1], "before"))

            # Text fields may contain multiple OCR fragments, such as
            # "office" + "Chair".
            if field not in (
                self.NUMERIC_FIELDS
                | self.DATE_FIELDS
                | {"invoice_number"}
            ):
                candidates.append((" ".join(before), "before"))

        if after:
            # Closest value after the label.
            candidates.append((after[0], "after"))

            if field not in (
                self.NUMERIC_FIELDS
                | self.DATE_FIELDS
                | {"invoice_number"}
            ):
                candidates.append((" ".join(after), "after"))

        best_value = ""
        best_score = 0

        for value, direction in candidates:
            score = self.value_score(field, value)

            # Your current OCR output places most values before their labels.
            # This only resolves score ties; validators remain the main check.
            if direction == "before":
                score += 2

            if score > best_score:
                best_value = value
                best_score = score

        return best_value if best_score > 0 else ""

    def collect_value_run(self, lines, start, step):
        values = []
        index = start

        while 0 <= index < len(lines) and len(values) < 3:
            value = str(lines[index]).strip()

            if not value or self.is_label_line(value):
                break

            if step < 0:
                values.insert(0, value)
            else:
                values.append(value)

            index += step

        return values

    def is_label_line(self, line):
        normalized = self.field_mapper.normalize(line)

        return bool(
            self.exact_field_for_line(line)
            or normalized in self.non_data_labels
        )

    def value_score(self, field, value):
        value = value.strip()
        normalized = self.field_mapper.normalize(value)

        if not value or normalized in self.non_data_labels:
            return -100

        if field in self.DATE_FIELDS:
            return 100 if self.looks_like_date(value) else -100

        if field == "invoice_number":
            if self.looks_like_date(value):
                return -100

            return 90 if re.search(r"\d", value) else -20

        if field == "quantity":
            return 100 if re.fullmatch(r"\s*\d+\s*", value) else -100

        if field in {"price", "amount"}:
            return 100 if self.looks_like_money(value) else -100

        if re.search(r"[A-Za-z]", value):
            return 40 + min(10, len(value.split()))

        return -50

    def looks_like_date(self, value):
        return bool(
            re.search(
                r"\b(?:"
                r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
                r"|"
                r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
                r")\b",
                value,
            )
        )

    def looks_like_money(self, value):
        return bool(
            re.fullmatch(
                r"\s*"
                r"(?:[A-Za-z]{3}\s*)?"
                r"[^\d]*"
                r"\d[\d,\s]*(?:\.\d{1,2})?"
                r"\s*",
                value,
            )
        )

    # ------------------------------------------------------------------
    # Basic table parsing
    # ------------------------------------------------------------------

    def parse_table_rows(self, lines):
        for index, line in enumerate(lines):
            header_parts = self.split_table_line(line)

            mapped_fields = [
                self.field_mapper.map_field(part)
                for part in header_parts
            ]

            if sum(1 for field in mapped_fields if field) < 2:
                continue

            fields = [
                field or self.field_mapper.normalize(
                    header_parts[field_index]
                )
                for field_index, field in enumerate(mapped_fields)
            ]

            rows = []

            for value_line in lines[index + 1:]:
                if (
                    self.parse_key_value_line(value_line)
                    or self.is_label_line(value_line)
                ):
                    break

                values = self.split_table_line(value_line)

                if len(values) < 2:
                    if rows:
                        break
                    continue

                values += [""] * max(0, len(fields) - len(values))

                rows.append(
                    dict(zip(fields, values[:len(fields)]))
                )

            if rows:
                return rows

        return []

    def split_table_line(self, line):
        if "|" in line:
            return [
                part.strip()
                for part in line.split("|")
                if part.strip()
            ]

        if "\t" in line:
            return [
                part.strip()
                for part in line.split("\t")
                if part.strip()
            ]

        return [
            part.strip()
            for part in re.split(r"\s{2,}", line)
            if part.strip()
        ]

    # ------------------------------------------------------------------
    # Value cleanup
    # ------------------------------------------------------------------

    def clean_row(self, row):
        cleaned = {}

        for field, value in row.items():
            value = re.sub(r"\s+", " ", str(value)).strip()

            if field in {"price", "amount"}:
                value = re.sub(
                    r"[^0-9.\-]",
                    "",
                    value.replace(",", ""),
                )

            if field == "quantity":
                value = re.sub(r"[^0-9\-]", "", value)

            if value:
                cleaned[field] = value

        return cleaned
