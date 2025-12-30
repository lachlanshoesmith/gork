import re

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

WORD_REGEX = re.compile(r"(\w[\w']*\w|\w)")


def is_substantial_word(word: str):
    # isalpha -> catches numbers, contractions
    return word.isalpha() and len(word) >= 3 and word not in INSUBSTANTIAL_WORDS


def get_substantial_words(message: str) -> list[str]:
    substrs = WORD_REGEX.findall(message)
    return [substr.lower() for substr in substrs if is_substantial_word(substr)]
