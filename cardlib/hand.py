from cardlib.card import Card


class Hand:
    def __init__(self, owner: str = "Player"):
        self.owner = owner          # human-readable label
        self._cards: list[Card] = []

    def add(self, cards):
    
        if isinstance(cards, Card):
            cards = [cards]
        for card in cards:
            if not isinstance(card, Card):
                raise TypeError(f"Expected Card, got {type(card)}")
            self._cards.append(card)

    def remove(self, card: Card) -> Card:
        if card not in self._cards:
            raise ValueError(f"{card} is not in {self.owner}'s hand")
        self._cards.remove(card)
        return card

    def sort(self):
        self._cards.sort()

    def count(self) -> int:
        return len(self._cards)
    def cards(self) -> list[Card]:
        return list(self._cards)     

    def clear(self):
        self._cards.clear()

    def __contains__(self, card: Card):
        return card in self._cards

    def __len__(self):
        return len(self._cards)

    def __repr__(self):
        return f"Hand({self.owner}: {self._cards})"

    def to_dict(self):
        return {
            "owner": self.owner,
            "cards": [c.to_dict() for c in self._cards],
            "count": self.count()
        }
