# CardLib — Python OOP Project

A reusable card library with two playable games (Marriage & Callbreak), exposed via FastAPI.

## Quick Start

```bash
pip install -r requirements.txt
uvicorn server:app --reload
```

Then open **http://localhost:8000** in your browser.

## Project Structure

```
cardlib_project/
├── cardlib/              ← The reusable library
│   ├── card.py           ← Card, Suit (Layer 1)
│   ├── deck.py           ← Deck (Layer 1)
│   ├── hand.py           ← Hand (Layer 1)
│   ├── dealer.py         ← Dealer (Layer 2)
│   ├── mechanics.py      ← TurnManager, Table (Layer 2)
│   ├── engine.py         ← RuleEngine (ABC), GameState, EventBus (Layer 3)
│   └── __init__.py       ← Public exports
├── games/
│   ├── marriage.py       ← Marriage game (subclasses RuleEngine)
│   └── callbreak.py      ← Callbreak game (subclasses RuleEngine)
├── static/
│   └── index.html        ← Frontend (HTML/CSS/JS)
├── server.py             ← FastAPI application
├── requirements.txt
└── README.md
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/games` | GET | List available games |
| `/games/{game}/new` | POST | Start new session |
| `/games/{session}/state` | GET | Get current state |
| `/games/{session}/play` | POST | Submit a move |
| `/games/{session}/valid-moves?player_id=X` | GET | Get legal moves |
| `/games/{session}/restart` | POST | Restart game |

## Game Rules

### Marriage (3 players)
- Each player gets 21 cards
- Form melds: K+Q same suit = Marriage (+3 pts), 3-4 consecutive same suit = Sequence (+2 pts)
- Unmelded cards = −1 pt each
- First player to declare wins the round

### Callbreak (4 players)
- Each player gets 13 cards
- Spades (♠) are always trump
- Bid how many tricks you'll win (1-13)
- Must follow suit; if can't, must play spade
- Meet/exceed bid = +bid points; miss = −bid points
- 5 rounds total
