"""
server.py
---------
FastAPI server that wraps CardLib.

Key design principle:
  The server is STATELESS — all game state lives in the GameState dict
  stored in the `sessions` dictionary. Every response returns the full state.

The server only ever calls the RuleEngine abstract interface:
  - engine.start_game()
  - engine.is_valid_move()
  - engine.apply_move()
  - engine.get_valid_moves()
  - engine.find_winner()
  - engine.score()

It NEVER imports game-specific logic. That's polymorphism in action.

Run with:
  uvicorn server:app --reload
"""

import uuid
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Any

from cardlib import RuleEngine
from games.marriage  import MarriageGame
from games.callbreak import CallbreakGame

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CardLib API",
    description="Play Marriage and Callbreak via HTTP",
    version="1.0.0"
)

# In-memory session store: {session_id: {"engine": RuleEngine, "state": dict}}
sessions: dict[str, dict] = {}

# Registry of available games
GAME_REGISTRY: dict[str, type[RuleEngine]] = {
    "marriage":  MarriageGame,
    "callbreak": CallbreakGame,
}


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response models
# ─────────────────────────────────────────────────────────────────────────────

class NewGameRequest(BaseModel):
    player_ids: list[str]   # e.g. ["Alice", "Bob", "Carol"]


class MoveRequest(BaseModel):
    player_id: str
    cards: list[Any]        # list of card dicts, or [{"bid": 5}] for bidding


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def get_session(session_id: str) -> dict:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return sessions[session_id]


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/games")
def list_games():
    """List available games, including player-count limits for the frontend form."""
    return {
        "games": list(GAME_REGISTRY.keys()),
        "info": {
            "marriage": {
                "description": "2-6 players — throw cards on the table, meld sequences to win",
                "min_players": MarriageGame.MIN_PLAYERS,
                "max_players": MarriageGame.MAX_PLAYERS,
            },
            "callbreak": {
                "description": "4 players — bid tricks, spades trump",
                "min_players": CallbreakGame.NUM_PLAYERS,
                "max_players": CallbreakGame.NUM_PLAYERS,
            },
        }
    }


@app.post("/games/{game}/new")
def new_game(game: str, body: NewGameRequest):
    """
    Start a new game session.
    Returns a session_id you use for all subsequent calls.

    Example:
      POST /games/callbreak/new
      {"player_ids": ["Alice", "Bob", "Carol", "Dave"]}
    """
    if game not in GAME_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown game '{game}'. Choose from: {list(GAME_REGISTRY)}"
        )

    # Clean and validate player names before handing off to the engine
    names = [n.strip() for n in body.player_ids]
    if any(not n for n in names):
        raise HTTPException(status_code=400, detail="Player names cannot be empty")
    if len(set(names)) != len(names):
        raise HTTPException(status_code=400, detail="Player names must be unique")

    engine = GAME_REGISTRY[game]()    # instantiate the concrete RuleEngine
    try:
        state = engine.start_game(names)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    session_id = str(uuid.uuid4())
    sessions[session_id] = {"engine": engine, "state": state}

    return {"session_id": session_id, "state": state}


@app.get("/games/{session_id}/state")
def get_state(session_id: str):
    """Return the current GameState for this session."""
    session = get_session(session_id)
    return session["state"]


@app.post("/games/{session_id}/play")
def play_move(session_id: str, body: MoveRequest):
    """
    Submit a move.

    For bidding phase: cards = [{"bid": 5}]
    For playing phase: cards = [{"suit": "Spades", "rank": "A", ...}]

    Returns the updated GameState.
    """
    session = get_session(session_id)
    engine: RuleEngine = session["engine"]
    state  = session["state"]

    if state.get("game_over"):
        raise HTTPException(status_code=400, detail="Game is already over")

    if not engine.is_valid_move(body.player_id, body.cards, state):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid move by {body.player_id}"
        )

    try:
        new_state = engine.apply_move(body.player_id, body.cards, state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    session["state"] = new_state
    return new_state


@app.get("/games/{session_id}/valid-moves")
def valid_moves(session_id: str, player_id: str):
    """
    List valid moves for the given player right now.
    Query param: ?player_id=Alice
    """
    session = get_session(session_id)
    engine: RuleEngine = session["engine"]
    state  = session["state"]
    moves  = engine.get_valid_moves(player_id, state)
    return {"player_id": player_id, "valid_moves": moves}


@app.get("/games/{session_id}/history")
def get_history(session_id: str):
    """
    Return the full replay log for this session:
    every move, who made it, what it was, and when (timestamp).
    """
    session = get_session(session_id)
    state = session["state"]
    return {"session_id": session_id, "history": state.get("history", [])}


@app.get("/games/{session_id}/history/export")
def export_history(session_id: str):
    """
    Export the move history as a downloadable plain-text replay log.
    Each line: [turn] timestamp — player: action (detail)
    """
    session = get_session(session_id)
    state = session["state"]
    history = state.get("history", [])

    lines = [
        f"CardLib replay — {state.get('game_name')} — session {session_id}",
        "=" * 60,
    ]
    for entry in history:
        lines.append(
            f"[{entry['turn']:>3}] {entry['timestamp']}  "
            f"{entry['player_id']:<12} {entry['action']:<12} {entry['detail']}"
        )
    lines.append("=" * 60)
    lines.append(f"Final scores: {state.get('scores')}")
    if state.get("winner"):
        lines.append(f"Winner: {state['winner']}")

    text = "\n".join(lines)
    return Response(
        content=text,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="cardlib_replay_{session_id[:8]}.txt"'
        }
    )


@app.post("/games/{session_id}/restart")
def restart_game(session_id: str):
    """Reset the game keeping the same session_id and same players."""
    session = get_session(session_id)
    engine: RuleEngine = session["engine"]
    old_state = session["state"]
    players   = old_state["metadata"].get("players") or list(old_state["hands"].keys())

    new_state = engine.start_game(players)
    session["state"] = new_state
    return {"session_id": session_id, "state": new_state}


@app.delete("/games/{session_id}")
def delete_session(session_id: str):
    """Clean up a session."""
    get_session(session_id)
    del sessions[session_id]
    return {"deleted": session_id}
