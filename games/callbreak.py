"""
games/callbreak.py
------------------
Game 2 — Callbreak (Nepali/South Asian trick-taking game)

RULES:
  - 4 players, 13 cards each (standard 52-card deck)
  - Spades (♠) are ALWAYS trump — they beat any other suit
  - Before play: each player BIDS how many tricks they'll win (1–13)
  - Play: 4 tricks × 13 rounds (52 total cards)
  - Each trick: players must FOLLOW SUIT if they can; otherwise play any card
  - If you can't follow suit, you MUST play a Spade if you have one
  - Highest card of the led suit wins, UNLESS a Spade was played
  - If Spades played: highest Spade wins

SCORING:
  - Met or exceeded your bid → score = bid (e.g. bid 4, won 4+ → +4)
  - Failed to meet bid → score = -bid  (e.g. bid 4, won 3 → -4)
  - Bonus: winning more tricks than bid gives fractional bonus (simplified: just bid)

Game ends after 5 rounds. Highest total score wins.
"""

from cardlib import (
    Card, Deck, Hand, Dealer, TurnManager, Table,
    RuleEngine, GameState, Suit
)


TRUMP_SUIT = Suit.SPADES    # Spades are always trump in Callbreak


def card_wins_trick(candidate: Card, current_winner: Card, led_suit: Suit) -> bool:
    """
    Returns True if candidate beats current_winner given the led suit.

    Trump (Spades) beats non-trump.
    Within the same suit, higher value wins.
    """
    c_trump = (candidate.suit    == TRUMP_SUIT)
    w_trump = (current_winner.suit == TRUMP_SUIT)

    if c_trump and not w_trump:
        return True               # trump beats non-trump
    if not c_trump and w_trump:
        return False              # non-trump can't beat trump
    if c_trump and w_trump:
        return candidate.value > current_winner.value   # both trump: higher wins
    # Neither is trump
    if candidate.suit == led_suit and current_winner.suit != led_suit:
        return True               # followed suit beats off-suit
    if candidate.suit != led_suit and current_winner.suit == led_suit:
        return False
    if candidate.suit == current_winner.suit:
        return candidate.value > current_winner.value
    return False                  # both off-suit, non-comparable


def determine_trick_winner(trick: list[dict], led_suit: Suit) -> str:
    """
    Given a list of {"player": id, "card": card_dict} plays,
    return the player_id who won the trick.
    """
    winner_play = trick[0]
    winner_card = Card.from_dict(winner_play["card"])

    for play in trick[1:]:
        card = Card.from_dict(play["card"])
        if card_wins_trick(card, winner_card, led_suit):
            winner_play = play
            winner_card = card

    return winner_play["player"]


def get_legal_cards(hand_dicts: list[dict], led_suit: Suit | None) -> list[dict]:
    """
    Which cards may the player legally play?

    Rules:
      1. If leading (no led_suit yet): any card
      2. If can follow led suit: MUST play a card of that suit
      3. If cannot follow led suit but has Spades: MUST play a Spade
      4. Otherwise: any card
    """
    hand = [Card.from_dict(c) for c in hand_dicts]

    if led_suit is None:
        return hand_dicts   # leading: anything goes

    same_suit = [c for c in hand if c.suit == led_suit]
    if same_suit:
        return [c.to_dict() for c in same_suit]

    spades = [c for c in hand if c.suit == TRUMP_SUIT]
    if spades:
        return [c.to_dict() for c in spades]

    return hand_dicts   # void in both led suit and spades: any card


# ─────────────────────────────────────────────────────────────────────────────
# CallbreakGame — RuleEngine subclass
# ─────────────────────────────────────────────────────────────────────────────

class CallbreakGame(RuleEngine):
    """
    Callbreak card game for 4 players.

    Phases:
      bidding → playing → trick_complete → scoring → ended
    """

    GAME_NAME   = "callbreak"
    NUM_PLAYERS = 4
    CARDS_EACH  = 13
    TOTAL_ROUNDS = 5

    def start_game(self, player_ids: list) -> dict:
        if len(player_ids) != self.NUM_PLAYERS:
            raise ValueError(f"Callbreak requires exactly {self.NUM_PLAYERS} players")

        deck = Deck()
        deck.shuffle()
        hands = {pid: Hand(pid) for pid in player_ids}
        dealer = Dealer(deck)
        dealer.distribute(list(hands.values()), self.CARDS_EACH)

        gs = GameState(
            game_name      = self.GAME_NAME,
            phase          = "bidding",
            current_player = player_ids[0],
            hands          = {pid: [c.to_dict() for c in h.cards()] for pid, h in hands.items()},
            table          = [],
            scores         = {pid: 0 for pid in player_ids},
            round_num      = 1,
            metadata       = {
                "players":       player_ids,
                "bids":          {},          # player_id → int
                "tricks_won":    {pid: 0 for pid in player_ids},
                "current_trick": [],          # [{"player": id, "card": dict}]
                "led_suit":      None,        # suit name string or None
                "games_played":  0,
                "round_scores":  [],          # list of per-round score dicts
                "trick_leader":  player_ids[0],
            },
            message = f"Bidding phase. {player_ids[0]}, enter your bid (1–13).",
        )
        gs.log_event(player_ids[0], "game_start",
                     f"{self.NUM_PLAYERS} players, {self.CARDS_EACH} cards each")
        return gs.to_dict()

    # ── RuleEngine interface ───────────────────────────────────────────────

    def is_valid_move(self, player_id: str, cards: list, state: dict) -> bool:
        if state["current_player"] != player_id:
            return False
        phase = state["phase"]

        if phase == "bidding":
            # cards is used as [bid_number] — e.g. [{"bid": 5}]
            if not cards or not isinstance(cards[0], dict):
                return False
            bid = cards[0].get("bid")
            return isinstance(bid, int) and 1 <= bid <= 13

        if phase == "playing":
            if not cards or len(cards) != 1:
                return False
            played = Card.from_dict(cards[0])
            hand_dicts = state["hands"][player_id]
            # Check card is actually in hand
            if cards[0] not in hand_dicts:
                return False
            led_suit_name = state["metadata"].get("led_suit")
            led_suit = Suit(led_suit_name) if led_suit_name else None
            legal = get_legal_cards(hand_dicts, led_suit)
            return cards[0] in legal

        return False

    def get_valid_moves(self, player_id: str, state: dict) -> list:
        phase = state["phase"]
        if state["current_player"] != player_id:
            return []

        if phase == "bidding":
            return [{"bid": i} for i in range(1, 14)]

        if phase == "playing":
            led_suit_name = state["metadata"].get("led_suit")
            led_suit = Suit(led_suit_name) if led_suit_name else None
            return get_legal_cards(state["hands"][player_id], led_suit)

        return []

    def apply_move(self, player_id: str, cards: list, state: dict) -> dict:
        if not self.is_valid_move(player_id, cards, state):
            raise ValueError(f"Invalid move by {player_id}: {cards}")

        gs = GameState.from_dict(state)
        players = gs.metadata["players"]
        phase   = gs.phase

        # ── Bidding phase ──────────────────────────────────────────────────
        if phase == "bidding":
            bid = cards[0]["bid"]
            gs.metadata["bids"][player_id] = bid
            gs.log_event(player_id, "bid", f"bid {bid}")
            all_bid = len(gs.metadata["bids"]) == self.NUM_PLAYERS
            if not all_bid:
                idx = players.index(player_id)
                gs.current_player = players[(idx + 1) % self.NUM_PLAYERS]
                gs.message = (
                    f"{player_id} bid {bid}. "
                    f"{gs.current_player}'s turn to bid."
                )
            else:
                gs.phase          = "playing"
                gs.current_player = gs.metadata["trick_leader"]
                bids_str = ", ".join(
                    f"{p}:{gs.metadata['bids'][p]}" for p in players
                )
                gs.message = f"All bids in! [{bids_str}]. Play begins!"
            return gs.to_dict()

        # ── Playing phase ──────────────────────────────────────────────────
        card_dict = cards[0]
        played    = Card.from_dict(card_dict)
        gs.log_event(player_id, "play_card", played.__repr__())

        # Remove from player's hand
        gs.hands[player_id] = [
            c for c in gs.hands[player_id] if c != card_dict
        ]

        trick = gs.metadata["current_trick"]
        # Set led suit on first play of trick
        if not trick:
            gs.metadata["led_suit"] = played.suit.value

        trick.append({"player": player_id, "card": card_dict})
        gs.metadata["current_trick"] = trick
        gs.table.append(card_dict)

        # Advance turn within trick
        idx = players.index(player_id)
        gs.current_player = players[(idx + 1) % self.NUM_PLAYERS]

        # Check if trick is complete (all 4 played)
        if len(trick) == self.NUM_PLAYERS:
            led_suit = Suit(gs.metadata["led_suit"])
            trick_winner = determine_trick_winner(trick, led_suit)
            gs.metadata["tricks_won"][trick_winner] += 1
            # Clear for next trick
            gs.metadata["current_trick"] = []
            gs.metadata["led_suit"]      = None
            gs.table                     = []
            gs.metadata["trick_leader"]  = trick_winner
            gs.current_player            = trick_winner
            gs.message = f"{trick_winner} wins the trick!"
            gs.log_event(trick_winner, "win_trick",
                         f"trick #{sum(gs.metadata['tricks_won'].values())}")

            # Check if the round is over (all 13 tricks played)
            total_tricks = sum(gs.metadata["tricks_won"].values())
            if total_tricks == self.CARDS_EACH:
                return self._end_round(gs)
        else:
            gs.message = f"{player_id} played {played}."

        return gs.to_dict()

    def _end_round(self, gs: GameState) -> dict:
        """Tally scores for the completed round."""
        bids       = gs.metadata["bids"]
        tricks_won = gs.metadata["tricks_won"]
        players    = gs.metadata["players"]

        round_delta = {}
        for pid in players:
            bid = bids[pid]
            won = tricks_won[pid]
            delta = bid if won >= bid else -bid
            round_delta[pid] = delta
            gs.scores[pid]  += delta

        gs.metadata["round_scores"].append(round_delta)
        gs.metadata["games_played"] += 1
        games_played = gs.metadata["games_played"]

        if games_played >= self.TOTAL_ROUNDS:
            winner = max(gs.scores, key=gs.scores.get)
            gs.phase     = "ended"
            gs.game_over = True
            gs.winner    = winner
            gs.message   = (
                f"Game over after {self.TOTAL_ROUNDS} rounds! "
                f"Winner: {winner} with {gs.scores[winner]} pts."
            )
            gs.log_event(winner, "game_end", f"final score {gs.scores[winner]}")
        else:
            # New round: redeal
            gs.round_num += 1
            gs.phase = "bidding"
            deck = Deck()
            deck.shuffle()
            hands = {pid: Hand(pid) for pid in players}
            dealer = Dealer(deck)
            dealer.distribute(list(hands.values()), self.CARDS_EACH)
            gs.hands = {pid: [c.to_dict() for c in h.cards()] for pid, h in hands.items()}
            first_player = players[0]
            gs.current_player = first_player
            gs.metadata["bids"]         = {}
            gs.metadata["tricks_won"]   = {pid: 0 for pid in players}
            gs.metadata["current_trick"]= []
            gs.metadata["led_suit"]     = None
            gs.metadata["trick_leader"] = first_player
            score_str = ", ".join(f"{p}:{gs.scores[p]}" for p in players)
            gs.message = (
                f"Round {games_played} done! Scores: [{score_str}]. "
                f"Round {gs.round_num} bidding begins."
            )
            gs.log_event("system", "round_end", f"round {games_played} scores [{score_str}]")

        return gs.to_dict()

    def find_winner(self, state: dict) -> str | None:
        if state.get("game_over"):
            return state.get("winner")
        return None

    def score(self, state: dict) -> dict:
        return state["scores"]
