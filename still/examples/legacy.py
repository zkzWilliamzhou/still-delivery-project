"""Original price parser used by the quickstart example."""


def parse_price(value):
    text = str(value).strip()
    if text == "" or text.lower() == "free":
        return 0.0
    if text.startswith("$"):
        text = text[1:]
    number = float(text)
    if number < 0:
        raise ValueError("negative price")
    return number
