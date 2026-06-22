"""
cardlib/__init__.py
-------------------
Public API of the CardLib package.

Importing from cardlib gives you everything you need:
    from cardlib import Card, Deck, Hand, Dealer, TurnManager, Table, RuleEngine
"""

from cardlib.card      import Card, Suit, RANK_VALUES
from cardlib.deck      import Deck
from cardlib.hand      import Hand
from cardlib.dealer    import Dealer
from cardlib.mechanics import TurnManager, Table
from cardlib.engine    import RuleEngine, GameState, EventBus

__all__ = [
    "Card", "Suit", "RANK_VALUES",
    "Deck", "Hand", "Dealer",
    "TurnManager", "Table",
    "RuleEngine", "GameState", "EventBus",
]
