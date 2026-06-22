from abc import ABC, abstractmethod
from typing import Any, Callable


class RuleEngine(ABC):
    @abstractmethod
    def is_valid_move(self, player_id: str, cards: list, state: dict) -> bool:
        """
        Return True if the given player is allowed to play these cards
        given the current game state.
        """
        ...

    @abstractmethod
    def find_winner(self, state: dict) -> str | None:
        """
        Return the ID of the winner of the current trick/round,
        or None if it hasn't concluded yet.
        """
        ...

    @abstractmethod
    def score(self, state: dict) -> dict:
        """
        Return a dict mapping player_id → current score.
        Called after each trick/round to update totals.
        """
        ...

    @abstractmethod
    def get_valid_moves(self, player_id: str, state: dict) -> list:
        """Return a list of cards the player may legally play."""
        ...

    @abstractmethod
    def start_game(self, player_ids: list) -> dict:
        """Initialise and return the starting GameState dict."""
        ...

    @abstractmethod
    def apply_move(self, player_id: str, cards: list, state: dict) -> dict:
        """Apply a move and return the updated GameState dict."""
        ...



class GameState:

    def __init__(
        self,
        game_name:      str,
        phase:          str,
        current_player: str,
        hands:          dict,
        table:          list,
        scores:         dict,
        round_num:      int  = 1,
        metadata:       dict = None,
        message:        str  = "",
        game_over:      bool = False,
        winner:         str  = None,
        history:        list = None,
    ):
        self.game_name      = game_name
        self.phase          = phase
        self.current_player = current_player
        self.hands          = hands       # {player_id: [card dicts]}
        self.table          = table       # [card dicts]
        self.scores         = scores      # {player_id: int}
        self.round_num      = round_num
        self.metadata       = metadata or {}
        self.message        = message
        self.game_over      = game_over
        self.winner         = winner
        self.history        = history if history is not None else []  # full move log

    def log_event(self, player_id: str, action: str, detail: str = ""):
        import datetime
        self.history.append({
            "turn":      len(self.history) + 1,
            "player_id": player_id,
            "action":    action,        # e.g. "play_card", "bid", "declare"
            "detail":    detail,        # e.g. "♠A" or "bid 5"
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        })

    def to_dict(self) -> dict:
        return {
            "game_name":      self.game_name,
            "phase":          self.phase,
            "current_player": self.current_player,
            "hands":          self.hands,
            "table":          self.table,
            "scores":         self.scores,
            "round_num":      self.round_num,
            "metadata":       self.metadata,
            "message":        self.message,
            "game_over":      self.game_over,
            "winner":         self.winner,
            "history":        self.history,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GameState":
        """Restore a GameState from a dict (e.g. from Redis / session store)."""
        return cls(
            game_name      = d["game_name"],
            phase          = d["phase"],
            current_player = d["current_player"],
            hands          = d["hands"],
            table          = d["table"],
            scores         = d["scores"],
            round_num      = d.get("round_num", 1),
            metadata       = d.get("metadata", {}),
            message        = d.get("message", ""),
            game_over      = d.get("game_over", False),
            winner         = d.get("winner"),
            history        = d.get("history", []),
        )

    def snapshot(self) -> dict:
        """Alias for to_dict() — used in replay logs."""
        return self.to_dict()

    def __repr__(self):
        return (
            f"GameState(game={self.game_name}, phase={self.phase}, "
            f"turn={self.current_player}, round={self.round_num})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# EventBus — Observer pattern
# ─────────────────────────────────────────────────────────────────────────────

class EventBus:
    """
    Simple pub/sub (Observer pattern) event bus.

    Games call emit("card_played", data) without knowing who's listening.
    The API layer registers handlers with on("card_played", my_fn).

    Example:
        bus = EventBus()
        bus.on("round_ended", lambda d: print("Round ended!", d))
        bus.emit("round_ended", {"winner": "Alice"})
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def on(self, event: str, fn: Callable):
        """Register fn as a handler for event."""
        self._handlers.setdefault(event, []).append(fn)

    def off(self, event: str, fn: Callable = None):
        """
        Remove handler(s) for event.
        If fn is None, remove ALL handlers for that event.
        """
        if event not in self._handlers:
            return
        if fn is None:
            del self._handlers[event]
        else:
            self._handlers[event] = [
                h for h in self._handlers[event] if h is not fn
            ]

    def emit(self, event: str, data: Any = None):
        """Fire all handlers registered for event."""
        for handler in self._handlers.get(event, []):
            handler(data)

    def __repr__(self):
        return f"EventBus(events={list(self._handlers.keys())})"
