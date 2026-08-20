from __future__ import annotations

import random
import re
from datetime import date
from hashlib import sha256
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache


HELLOAO_BASE_URL = "https://bible.helloao.org/api"
REQUEST_TIMEOUT_SECONDS = 6

VERSE_POOL = [
    {"book": "PSA", "chapter": 23, "start": 1, "end": 1},
    {"book": "PSA", "chapter": 46, "start": 1, "end": 1},
    {"book": "PRO", "chapter": 3, "start": 5, "end": 6},
    {"book": "ISA", "chapter": 40, "start": 31, "end": 31},
    {"book": "JER", "chapter": 29, "start": 11, "end": 11},
    {"book": "MAT", "chapter": 5, "start": 14, "end": 16},
    {"book": "MAT", "chapter": 11, "start": 28, "end": 30},
    {"book": "ROM", "chapter": 8, "start": 28, "end": 28},
    {"book": "PHP", "chapter": 4, "start": 6, "end": 7},
]


def select_reference(day: date) -> dict[str, int | str]:
    """
    Produce the same shuffled order for everyone during a given year.
    With 365 pool entries, no verse repeats during that year.
    """
    salt = getattr(settings, "VERSE_OF_DAY_SALT", "cfi-database-v1")
    seed_source = f"{salt}:{day.year}".encode("utf-8")
    seed = int.from_bytes(sha256(seed_source).digest()[:8], "big")

    references = list(VERSE_POOL)
    random.Random(seed).shuffle(references)

    day_index = day.timetuple().tm_yday - 1
    return references[day_index % len(references)]


def flatten_fragment(fragment: Any) -> str:
    if isinstance(fragment, str):
        return fragment

    if not isinstance(fragment, dict):
        return ""

    # Formatted text, including poetry and words of Jesus.
    if isinstance(fragment.get("text"), str):
        return fragment["text"]

    # Inline line break.
    if fragment.get("lineBreak") is True:
        return " "

    # Ignore footnote references and inline headings in the card.
    return ""


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def build_reference_label(
    book_name: str,
    chapter: int,
    start: int,
    end: int,
) -> str:
    verses = str(start) if start == end else f"{start}-{end}"
    return f"{book_name} {chapter}:{verses}"


def get_verse_of_the_day(day: date) -> dict[str, Any] | None:
    translation_id = getattr(settings, "BIBLE_TRANSLATION_ID", "BSB")
    cache_key = f"dashboard:verse-of-day:{translation_id}:{day.isoformat()}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    selected = select_reference(day)

    book_id = str(selected["book"])
    chapter_number = int(selected["chapter"])
    start_verse = int(selected["start"])
    end_verse = int(selected["end"])

    try:
        response = requests.get(
            (
                f"{HELLOAO_BASE_URL}/{translation_id}/"
                f"{book_id}/{chapter_number}.json"
            ),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        chapter_data = response.json()

        matching_verses = [
            item
            for item in chapter_data["chapter"]["content"]
            if (
                item.get("type") == "verse"
                and start_verse <= int(item["number"]) <= end_verse
            )
        ]

        verse_parts: list[str] = []

        for verse in matching_verses:
            text = "".join(
                flatten_fragment(fragment)
                for fragment in verse.get("content", [])
            )
            text = normalize_text(text)

            if text:
                verse_parts.append(text)

        verse_text = normalize_text(" ".join(verse_parts))

        if not verse_text:
            raise ValueError("HelloAO returned no text for the selected passage.")

        book_name = (
            chapter_data.get("book", {}).get("commonName")
            or chapter_data.get("book", {}).get("name")
            or book_id
        )

        translation = chapter_data.get("translation", {})

        payload = {
            "date": day.isoformat(),
            "text": verse_text,
            "reference": build_reference_label(
                book_name=book_name,
                chapter=chapter_number,
                start=start_verse,
                end=end_verse,
            ),
            "book_id": book_id,
            "chapter": chapter_number,
            "start_verse": start_verse,
            "end_verse": end_verse,
            "translation": {
                "id": translation.get("id", translation_id),
                "name": translation.get("englishName")
                or translation.get("name")
                or translation_id,
                "short_name": translation.get("shortName", translation_id),
                "license_url": translation.get("licenseUrl"),
            },
        }

        # The date is part of the key, so keeping it for two days is safe.
        cache.set(cache_key, payload, timeout=60 * 60 * 48)
        cache.set(
            f"dashboard:verse-of-day:last-good:{translation_id}",
            payload,
            timeout=60 * 60 * 24 * 14,
        )

        return payload

    except (
        requests.RequestException,
        KeyError,
        TypeError,
        ValueError,
    ):
        # Prevent an external API outage from breaking the dashboard.
        return cache.get(
            f"dashboard:verse-of-day:last-good:{translation_id}"
        )