import re


def generate_assembly_code(name: str, prefix: str = "CFI") -> str:
    """
    Generate a short assembly code from the assembly name.

    Example:
    Orwetoveni Assembly -> CFI-ORW
    Harare Central Assembly -> CFI-HCA
    """
    if not name:
        raise ValueError("Assembly name is required")

    clean_name = re.sub(r"[^A-Za-z0-9\s]", "", name).strip()
    words = clean_name.split()

    ignored_words = {"assembly", "church", "branch", "centre", "center"}

    meaningful_words = [
        word for word in words if word.lower() not in ignored_words
    ]

    if not meaningful_words:
        meaningful_words = words

    if len(meaningful_words) == 1:
        code_part = meaningful_words[0][:3]
    else:
        code_part = "".join(word[0] for word in meaningful_words[:3])

    return f"{prefix}-{code_part.upper()}"