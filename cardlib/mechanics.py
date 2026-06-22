from cardlib.card import Card


class TurnManager:
    def __init__(self, player_ids: list):
        if not player_ids:
            raise ValueError("Need at least one player")
        self._players  = list(player_ids)
        self._index    = 0          # index of the current player
        self._direction = 1         # +1 = forward, -1 = reverse
        self._skip_set: set = set() # players to skip this round

    @property
    def current(self):
        return self._players[self._index]

    def next(self):
        n = len(self._players)
        for _ in range(n):
            self._index = (self._index + self._direction) % n
            player = self._players[self._index]
            if player in self._skip_set:
                self._skip_set.discard(player)   # skip only once
                continue
            return player
        return self.current   # fallback (shouldn't reach here)

    def skip(self, player):
        if player not in self._players:
            raise ValueError(f"Unknown player: {player}")
        self._skip_set.add(player)

    def reverse(self):
        self._direction *= -1

    def reset(self, player_ids: list = None):
        if player_ids:
            self._players = list(player_ids)
        self._index     = 0
        self._direction = 1
        self._skip_set.clear()

    @property
    def players(self) -> list:
        return list(self._players)

    def to_dict(self) -> dict:
        return {
            "players":   self._players,
            "current":   self.current,
            "direction": self._direction,
        }

    def __repr__(self):
        arrow = "→" if self._direction == 1 else "←"
        return f"TurnManager({arrow} current={self.current})"


# ─────────────────────────────────────────────────────────────────────────────
# Table / Pile
# ─────────────────────────────────────────────────────────────────────────────

class Table:
    def __init__(self, name: str = "Table"):
        self.name = name
        self._pile: list[Card] = []

    def play(self, card: Card):
        if not isinstance(card, Card):
            raise TypeError(f"Expected Card, got {type(card)}")
        self._pile.append(card)

    def collect(self) -> list[Card]:
        taken = list(self._pile)
        self._pile.clear()
        return taken

    def top(self) -> Card | None:
        return self._pile[-1] if self._pile else None

    def is_empty(self) -> bool:
        return len(self._pile) == 0

    def cards(self) -> list[Card]:
        return list(self._pile)

    def __len__(self):
        return len(self._pile)

    def __repr__(self):
        return f"Table({self.name}: {self._pile})"

    def to_dict(self) -> dict:
        return {
            "name":  self.name,
            "cards": [c.to_dict() for c in self._pile],
        }
