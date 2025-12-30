import re
import random
from gork.db import Valkey

INSUBSTANTIAL_WORDS: set[str] = {
    # hardly a comprehensive list...
    "for",
    "and",
    "nor",
    "but",
    "yet",
    "just",
    "the",
    "rather",
    "such",
    "after",
    "although",
    "though",
    "was",
    "will",
    "not",
    "this",
    "that",
    "have",
}

TONES: dict[str, set[str]] = {
    "happy": {"😀", "😃", "😄", "😁", "🙂", "☺️", "😺"},
    "sad": {"☹️", "😥", "😢", "😭", "🙁", "😦", "😿"},
    "surprising": {"🤯", "😲", "😯", "🙀", "😱", "😯"},
    "amusing": {"😆", "🤣", "😂", "😹", "💀", "😸"},
    "enraging": {"😡", "😠", "🤬", "😾"},
}

WORD_REGEX = re.compile(r"(\w[\w']*\w|\w)")

MAX_LOOKUP_COUNT = 10


async def determine_tone(guild_id: int, message: str, db: Valkey):
    words = set(get_substantial_words(message)[:MAX_LOOKUP_COUNT])
    scores = {}
    for tone in TONES:
        scores[tone] = 0
        # TODO: this is obviously tremendously inefficient
        key = f"guild:{guild_id}:words:{tone}"
        for word in words:
            word_score = await db.zscore(key, word)
            if word_score:
                scores[tone] += word_score

    max_score = max(scores.values())
    if max_score == 0:
        return random.choice(list(scores.keys()))
    else:
        return max(scores, key=scores.get)


def is_substantial_word(word: str):
    # isalpha -> catches numbers, contractions
    return word.isalpha() and len(word) >= 3 and word not in INSUBSTANTIAL_WORDS


def get_substantial_words(message: str) -> list[str]:
    substrs = WORD_REGEX.findall(message)
    return [substr.lower() for substr in substrs if is_substantial_word(substr)]
