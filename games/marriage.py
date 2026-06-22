"""
games/marriage.py
-----------------
Game 1 — Marriage (Nepali card game)

RULES (flexible 2-6 player version):
  - 2 to 6 players. Card count per player auto-adjusts to fit one 52-card deck.
  - On your turn: throw ONE card face-up onto the shared table, then draw
    one card from the deck (classic draw-and-discard flow), OR simply
    throw a card if the deck is empty.
  - Goal: form SEQUENCES (meld) of 3 or 4 cards of the SAME suit, consecutive rank.
  - Special melds:
      * "Marriage" = K + Q of the same suit (worth 3 points)
      * "Sequence" = 3 consecutive same-suit cards (worth 2 points)
  - Once a player believes their hand is fully melded, they may Declare
    on their turn INSTEAD of throwing a card.
  - Declaring ends the round immediately; every hand is scored.
  - Scoring: +3 per Marriage, +2 per Sequence, -1 per unmelded card.
  - Highest total score wins.

RANKS for sequences: A(low)=1, 2,3,4,5,6,7,8,9,10,J,Q,K=13, A(high)=14
In Marriage, Ace can be used as BOTH 1 (A-2-3) and 14 (Q-K-A).

PLAYER COUNT → CARDS DEALT (auto-computed so it always fits 52 cards,
leaving room to draw from the deck during play):
  2 players → 17 cards each (34 dealt, 18 left to draw from)
  3 players → 13 cards each (39 dealt, 13 left to draw from)
  4 players → 10 cards each (40 dealt, 12 left to draw from)
  5 players →  8 cards each (40 dealt, 12 left to draw from)
  6 players →  7 cards each (42 dealt, 10 left to draw from)
"""

from cardlib import Card, Deck, Hand, Dealer, TurnManager, RuleEngine, GameState, Suit
from cardlib.card import RANK_VALUES


# ─────────────────────────────────────────────────────────────────────────────
# Meld detection helpers
# ─────────────────────────────────────────────────────────────────────────────

RANK_ORDER    = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_HIGH_ACE = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

# Minimum players for the game to make sense; maximum so cards-per-player stays playable
MIN_PLAYERS = 2
MAX_PLAYERS = 6

# Cards dealt per player, indexed by player count.
# Chosen so dealt cards always leave a stock pile to draw from during play.
CARDS_EACH_BY_COUNT = {
    2: 17,
    3: 13,
    4: 10,
    5: 8,
    6: 7,
}


def _rank_index(rank: str, high_ace=False) -> int:
    order = RANK_HIGH_ACE if high_ace else RANK_ORDER
    return order.index(rank)


def is_marriage(cards: list[Card]) -> bool:
    """K + Q of the same suit = a Marriage meld."""
    if len(cards) != 2:
        return False
    ranks = {c.rank for c in cards}
    suits = {c.suit for c in cards}
    return ranks == {"K", "Q"} and len(suits) == 1


def is_sequence(cards: list[Card]) -> bool:
    """3 or 4 cards of the same suit with consecutive ranks (ace low or high)."""
    if len(cards) not in (3, 4):
        return False
    suits = {c.suit for c in cards}
    if len(suits) != 1:
        return False

    ranks = sorted([c.rank for c in cards], key=lambda r: _rank_index(r))
    indices = [_rank_index(r) for r in ranks]
    if all(indices[i+1] - indices[i] == 1 for i in range(len(indices)-1)):
        return True
    indices_hi = sorted([_rank_index(r, high_ace=True) for r in ranks])
    return all(indices_hi[i+1] - indices_hi[i] == 1 for i in range(len(indices_hi)-1))


def find_melds(cards: list[Card]) -> dict:
    """Find all melds in a hand. Returns {marriages, sequences, unmelded}."""
    remaining = list(cards)
    marriages = []
    sequences = []

    for suit in Suit:
        suit_cards = [c for c in remaining if c.suit == suit]
        ks = [c for c in suit_cards if c.rank == "K"]
        qs = [c for c in suit_cards if c.rank == "Q"]
        if ks and qs:
            pair = [ks[0], qs[0]]
            marriages.append(pair)
            remaining.remove(ks[0])
            remaining.remove(qs[0])

    for suit in Suit:
        suit_cards = sorted(
            [c for c in remaining if c.suit == suit],
            key=lambda c: _rank_index(c.rank)
        )
        used = set()
        for size in (4, 3):
            for i in range(len(suit_cards) - size + 1):
                group = suit_cards[i:i+size]
                if any(id(c) in used for c in group):
                    continue
                if is_sequence(group):
                    sequences.append(group)
                    for c in group:
                        used.add(id(c))
                        remaining.remove(c)

    return {
        "marriages": [[c.to_dict() for c in m] for m in marriages],
        "sequences": [[c.to_dict() for c in s] for s in sequences],
        "unmelded":  [c.to_dict() for c in remaining],
    }


def calculate_meld_score(meld_result: dict) -> int:
    score = 0
    score += len(meld_result["marriages"]) * 3
    score += len(meld_result["sequences"]) * 2
    score -= len(meld_result["unmelded"])
    return score


# ─────────────────────────────────────────────────────────────────────────────
# MarriageGame — RuleEngine subclass
# ─────────────────────────────────────────────────────────────────────────────

class MarriageGame(RuleEngine):
    """
    Marriage card game for 2-6 players.

    Phases:
      playing → ended

    On each turn a player either:
      - "throw"   : place one card face-up on the table, then draw a replacement
      - "declare" : end the round and trigger scoring (instead of throwing)
    """

    GAME_NAME   = "marriage"
    MIN_PLAYERS = MIN_PLAYERS
    MAX_PLAYERS = MAX_PLAYERS

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start_game(self, player_ids: list) -> dict:
        """Deal cards (count depends on player count) and return initial state."""
        n = len(player_ids)
        if not (self.MIN_PLAYERS <= n <= self.MAX_PLAYERS):
            raise ValueError(
                f"Marriage requires {self.MIN_PLAYERS}-{self.MAX_PLAYERS} players, got {n}"
            )
        if len(set(player_ids)) != n:
            raise ValueError("Player names must be unique")

        cards_each = CARDS_EACH_BY_COUNT[n]

        deck = Deck()
        deck.shuffle()
        hands = {pid: Hand(pid) for pid in player_ids}
        dealer = Dealer(deck)
        dealer.distribute(list(hands.values()), cards_each)
        # whatever remains in the deck becomes the draw stock pile

        scores = {pid: 0 for pid in player_ids}
        gs = GameState(
            game_name      = self.GAME_NAME,
            phase          = "playing",
            current_player = player_ids[0],
            hands          = {pid: [c.to_dict() for c in h.cards()] for pid, h in hands.items()},
            table          = [],   # cards thrown so far this round (shared table)
            scores         = scores,
            round_num      = 1,
            metadata       = {
                "players":     player_ids,
                "declared_by": None,
                "melds":       {},
                "stock":       [c.to_dict() for c in deck._cards],  # remaining draw pile
                "cards_each":  cards_each,
            },
            message = (
                f"{n}-player Marriage. {cards_each} cards dealt each. "
                f"{player_ids[0]} goes first — throw a card or declare."
            ),
        )
        gs.log_event(player_ids[0], "game_start",
                     f"{n} players, {cards_each} cards each")
        return gs.to_dict()

    # ── RuleEngine interface ───────────────────────────────────────────────

    def is_valid_move(self, player_id: str, cards: list, state: dict) -> bool:
        """
        A move is one of:
          cards = [{"action": "throw", "card": {...}}]   — throw a card to the table
          cards = [{"action": "declare"}]                — declare and end the round
        Valid only if it's your turn, phase is playing, and nobody has declared.
        """
        if state["phase"] != "playing":
            return False
        if state["current_player"] != player_id:
            return False
        if state["metadata"].get("declared_by"):
            return False
        if not cards or not isinstance(cards[0], dict):
            return False

        action = cards[0].get("action")
        if action == "declare":
            return True
        if action == "throw":
            card = cards[0].get("card")
            if not card:
                return False
            return card in state["hands"][player_id]
        return False

    def get_valid_moves(self, player_id: str, state: dict) -> list:
        """Every card in hand can be thrown, plus the option to declare."""
        if state["phase"] != "playing" or state["current_player"] != player_id:
            return []
        if state["metadata"].get("declared_by"):
            return []
        moves = [{"action": "throw", "card": c} for c in state["hands"][player_id]]
        moves.append({"action": "declare"})
        return moves

    def apply_move(self, player_id: str, cards: list, state: dict) -> dict:
        if not self.is_valid_move(player_id, cards, state):
            raise ValueError(f"Invalid move by {player_id}")

        gs = GameState.from_dict(state)
        action = cards[0]["action"]
        players = gs.metadata["players"]

        if action == "declare":
            return self._handle_declare(gs, player_id)

        # action == "throw"
        thrown = cards[0]["card"]
        gs.hands[player_id] = [c for c in gs.hands[player_id] if c != thrown]
        gs.table.append(thrown)
        gs.log_event(player_id, "throw_card", f"{thrown.get('display', thrown)}")

        # Draw a replacement card from stock, if any remain
        stock = gs.metadata.get("stock", [])
        drew_display = None
        if stock:
            drawn_card = stock.pop(0)
            gs.hands[player_id].append(drawn_card)
            gs.metadata["stock"] = stock
            drew_display = drawn_card.get("display", drawn_card)
            gs.log_event(player_id, "draw_card", drew_display)

        # Advance turn (round-robin)
        idx = players.index(player_id)
        next_player = players[(idx + 1) % len(players)]
        gs.current_player = next_player

        if drew_display:
            gs.message = f"{player_id} threw {thrown.get('display')} and drew a new card. {next_player}'s turn."
        else:
            gs.message = f"{player_id} threw {thrown.get('display')} (stock empty). {next_player}'s turn."

        return gs.to_dict()

    def _handle_declare(self, gs: GameState, player_id: str) -> dict:
        """Score every hand, find the winner, end the round."""
        melds = {}
        for pid, card_dicts in gs.hands.items():
            hand_cards = [Card.from_dict(c) for c in card_dicts]
            melds[pid] = find_melds(hand_cards)

        new_scores = dict(gs.scores)
        for pid, meld in melds.items():
            new_scores[pid] += calculate_meld_score(meld)

        winner = max(new_scores, key=new_scores.get)

        gs.phase     = "ended"
        gs.scores    = new_scores
        gs.winner    = winner
        gs.game_over = True
        gs.metadata["declared_by"] = player_id
        gs.metadata["melds"]       = melds
        gs.message = f"{player_id} declared! Winner: {winner} with {new_scores[winner]} pts"
        gs.log_event(player_id, "declare", f"winner: {winner} ({new_scores[winner]} pts)")
        return gs.to_dict()

    def find_winner(self, state: dict) -> str | None:
        if state.get("game_over"):
            return state.get("winner")
        return None

    def score(self, state: dict) -> dict:
        return state["scores"]
