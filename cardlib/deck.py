import random
from cardlib.card import Card, Suit, RANK_VALUES


class Deck:
    def __init__(self):
        self._cards: list[Card] = []
        self.reset()  # populate on creation

    def reset(self):
        self._cards = [
            Card(suit, rank)
            for suit in Suit
            for rank in RANK_VALUES
        ]

    def shuffle(self):
        random.shuffle(self._cards)
        return self

    def draw(self, n: int = 1) -> list[Card]:
        if n < 1:
            raise ValueError("Must draw at least 1 card")
        if n > len(self._cards):
            raise ValueError(
                f"Cannot draw {n} cards; only {len(self._cards)} remain"
            )
        drawn = self._cards[:n]
        self._cards = self._cards[n:]
        return drawn

    def remaining(self) -> int:
        return len(self._cards)

    def __len__(self):
        return len(self._cards)

    def __repr__(self):
        return f"Deck({len(self._cards)} cards remaining)"
