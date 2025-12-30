from pydantic import BaseModel


class FavouredWord(BaseModel):
    word: str
    weight: int = 0


class StoredMessage(BaseModel):
    content: str
    favoured_words: list[FavouredWord]
