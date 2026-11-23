"""Bunny's friends: each character has its own name (= wake word), face and personality.
Saying a character's name wakes that character (and switches the face to it)."""

CHARACTERS = {
    "bunny": {
        "name": "Bunny",
        "wake": ["bunny", "bani", "banni", "bunni", "bonny", "buni", "bany", "baani"],
        "persona": "a cute, warm and playful little bunny",
        "pitch": 1.35, "rate": 1.02,
    },
    "pixel": {
        "name": "Pixel",
        "wake": ["pixel", "piksel", "pixal", "piksal", "piksl", "pixil", "pikcel"],
        "persona": "a tiny, curious robot made of light who is only two glowing eyes, playful and a little shy",
        "pitch": 1.6, "rate": 1.08,
    },
    "robo": {
        "name": "Robo",
        "wake": ["robo", "robot", "rowbo", "robu", "roboh", "robbo", "rubo"],
        "persona": "a cheerful little orange toy robot who loves gadgets, a bit cheeky and always excited to help",
        "pitch": 1.1, "rate": 1.05,
    },
}

ORDER = ["bunny", "pixel", "robo"]


def get(cid):
    return CHARACTERS.get(cid) or CHARACTERS["bunny"]


def all_wake():
    """[(character id, wake words)]"""
    return [(cid, CHARACTERS[cid]["wake"]) for cid in ORDER]


def public():
    return [{"id": cid, "name": CHARACTERS[cid]["name"], "pitch": CHARACTERS[cid]["pitch"],
             "rate": CHARACTERS[cid]["rate"]} for cid in ORDER]
