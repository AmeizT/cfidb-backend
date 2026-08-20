import re
import unicodedata
from difflib import SequenceMatcher


def normalize_financial_category_name(value):
    """Return a stable comparison key without changing the displayed name."""
    value = unicodedata.normalize("NFKD", str(value or "")).casefold().strip()
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"[^\w\s]", " ", value)
    tokens = re.findall(r"[a-z0-9]+", value)
    normalized_tokens = [_singularize(token) for token in tokens]
    return " ".join(normalized_tokens)


def _singularize(token):
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith("ses"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def financial_category_similarity(left, right):
    left_normalized = normalize_financial_category_name(left)
    right_normalized = normalize_financial_category_name(right)
    if not left_normalized or not right_normalized:
        return 0
    if left_normalized == right_normalized:
        return 1

    left_tokens = set(left_normalized.split())
    right_tokens = set(right_normalized.split())
    token_score = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    sequence_score = SequenceMatcher(None, left_normalized, right_normalized).ratio()
    return max(token_score, sequence_score)


def rank_financial_category_matches(query, items, *, limit=6, threshold=0.42):
    normalized_query = normalize_financial_category_name(query)
    ranked = []
    for item in items:
        normalized_name = item.normalized_name or normalize_financial_category_name(item.name)
        score = 1 if normalized_name == normalized_query else financial_category_similarity(query, item.name)
        if score >= threshold:
            ranked.append((score, item))
    ranked.sort(key=lambda result: (-result[0], result[1].name.casefold()))
    return [item for _, item in ranked[:limit]]
