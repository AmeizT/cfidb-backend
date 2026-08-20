import re
from difflib import SequenceMatcher


EXPENDITURE_FIELD_MAP = {
    "invoice_date": [
        "invoice date",
        "voice date",
        "date",
        "receipt date",
        "purchase date",
    ],
    "invoice_number": [
        "invoice number",
        "invoice no",
        "invoice #",
        "receipt number",
        "receipt no",
        "reference",
    ],
    "name": [
        "name",
        "expense",
        "expense name",
        "item",
        "item name",
        "purchase",
    ],
    "description": [
        "description",
        "details",
        "notes",
        "purpose",
    ],
    "category": [
        "category",
        "expense type",
        "type",
    ],
    "supplier": [
        "supplier",
        "vendor",
        "merchant",
        "paid to",
    ],
    "quantity": [
        "quantity",
        "qty",
        "count",
    ],
    "price": [
        "price",
        "amount",
        "cost",
        "total",
        "value",
    ],
}


class FieldMapper:
    def __init__(self, field_map):
        self.field_map = field_map
        self.aliases = self.build_aliases(field_map)

    def build_aliases(self, field_map):
        aliases = {}

        for canonical_field, labels in field_map.items():
            aliases[self.normalize(canonical_field)] = canonical_field

            for label in labels:
                aliases[self.normalize(label)] = canonical_field

        return aliases

    def normalize(self, value):
        return re.sub(r"[^a-z0-9]+", "", str(value).lower())

    def map_field(self, label):
        normalized = self.normalize(label)
        exact_match = self.aliases.get(normalized)

        if exact_match:
            return exact_match

        if len(normalized) < 4:
            return None

        best_alias = None
        best_score = 0

        for alias in self.aliases:
            score = SequenceMatcher(None, normalized, alias).ratio()

            if score > best_score:
                best_alias = alias
                best_score = score

        if best_alias and best_score >= 0.78:
            return self.aliases[best_alias]

        return None

    def map_row(self, row):
        mapped = {}

        for key, value in row.items():
            field = self.map_field(key) or key
            mapped[field] = value

        return mapped

    def find_label_in_text(self, text):
        normalized_text = self.normalize(text)

        matches = []
        for alias, canonical_field in self.aliases.items():
            if normalized_text.startswith(alias):
                matches.append((alias, canonical_field))

        if not matches:
            return None

        return max(matches, key=lambda item: len(item[0]))
