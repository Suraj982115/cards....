
from enum import Enum

class Suit(Enum):
    """The four suits. Using Enum keeps them type-safe (no typos like 'heart')."""
    HEARTS   = "Hearts"
    DIAMONDS = "Diamonds"
    CLUBS    = "Clubs"
    SPADES   = "Spades"

RANK_VALUES = {
    "A": 14, "2": 2, "3": 3, "4": 4,  "5": 5,
    "6": 6,  "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 11, "Q": 12, "K": 13
}

SUIT_ORDER = {
    Suit.CLUBS: 0, Suit.DIAMONDS: 1, Suit.HEARTS: 2, Suit.SPADES: 3
}


class Card:
    
    def __init__(self, suit: Suit, rank: str):
        if suit not in Suit:
            raise ValueError(f"Invalid suit: {suit}")
        if rank not in RANK_VALUES:
            raise ValueError(f"Invalid rank: {rank}")

        self.suit  = suit
        self.rank  = rank
        self.value = RANK_VALUES[rank]

    def __eq__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return self.suit == other.suit and self.rank == other.rank

    def __lt__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        if self.suit != other.suit:
            return SUIT_ORDER[self.suit] < SUIT_ORDER[other.suit]
        return self.value < other.value

    def __hash__(self):
        return hash((self.suit, self.rank))

    def __repr__(self):
        symbols = {
            Suit.HEARTS:   "♥",
            Suit.DIAMONDS: "♦",
            Suit.CLUBS:    "♣",
            Suit.SPADES:   "♠",
        }
        return f"{symbols[self.suit]}{self.rank}"

    def to_dict(self):
        return {
            "suit":  self.suit.value,
            "rank":  self.rank,
            "value": self.value,
            "display": repr(self)
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Card":
        suit_map = {s.value: s for s in Suit}
        return cls(suit_map[d["suit"]], d["rank"])
