import random
from cardlib.deck import Deck
from cardlib.hand import Hand
from cardlib.card import Card


class Dealer:
    def __init__(self, deck: Deck):
        if not isinstance(deck, Deck):
            raise TypeError("Dealer requires a Deck instance")
        self._deck = deck
        self._burned: list[Card] = []

    def distribute(self, hands: list[Hand], n: int):
        total_needed = n * len(hands)
        if self._deck.remaining() < total_needed:
            raise ValueError(
                f"Need {total_needed} cards but only "
                f"{self._deck.remaining()} remain"
            )
        for _ in range(n):
            for hand in hands:
                card = self._deck.draw(1)[0]
                hand.add(card)

    def cut(self):
        n = self._deck.remaining()
        if n < 2:
            return
        cut_point = random.randint(1, n - 1)
        all_cards = self._deck.draw(n)
        top    = all_cards[:cut_point]
        bottom = all_cards[cut_point:]
        # Put bottom half first (it goes to the top after cut)
        for card in bottom + top:
            self._deck._cards.append(card)

    def burn(self, n: int = 1):
        if n > self._deck.remaining():
            raise ValueError("Not enough cards to burn")
        self._burned.extend(self._deck.draw(n))

    def peek(self) -> Card | None:
        if self._deck.remaining() == 0:
            return None
        return self._deck._cards[0]

    @property
    def burned_cards(self) -> list[Card]:
        return list(self._burned)

    def __repr__(self):
        return f"Dealer(deck={self._deck.remaining()} cards)"
