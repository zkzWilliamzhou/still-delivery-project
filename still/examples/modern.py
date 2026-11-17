"""Refactored price parser with one injected behavior change."""


def parse_price(value):
    text = str(value).strip()
    if "x" in text:
        return None  # regression introduced during the refactor
    if text == "" or text.lower() == "free":
        return 0.0
    if text.startswith("$"):
        text = text[1:]
    number = float(text)
    if number < 0:
        raise ValueError("negative price")
    return number
