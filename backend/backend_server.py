"""
Backend Server for Magic Workstation (FastAPI)
Handles game state via WebSocket and persistence via Redis.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import uuid4
import uvicorn, redis, json, asyncio, os, re, time

from card_engine import Game, Player, ZoneType
from card_database import load_card_database, create_deck_for_player
import card_fetcher

# --- Configuration ---
app = FastAPI(title="Magic Workstation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- State & Persistence ---
games: Dict[str, Game] = {}
redis_client: Optional[redis.Redis] = None
REDIS_PREFIX = "mtg_game:"

def init_redis():
    global redis_client
    try:
        # Check if Redis is actually running first
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        print("✓ Redis connected")
    except Exception as e:
        print(f"⚠ Redis unavailable: {e}")
        print("⚠ Running in memory-only mode (state will be lost on restart)")
        redis_client = None

def save_game(game_id: str, game: Game):
    if redis_client:
        try:
            redis_client.set(f"{REDIS_PREFIX}{game_id}", json.dumps(game.to_dict()))
            redis_client.sadd("mtg_active_games", game_id)
        except Exception as e:
            print(f"Redis Save Error: {e}")

def load_game(game_id: str) -> Optional[Game]:
    if game_id in games: return games[game_id]
    if redis_client:
        try:
            data = redis_client.get(f"{REDIS_PREFIX}{game_id}")
            if data:
                game = Game.from_dict(json.loads(data))
                games[game_id] = game
                return game
        except Exception as e:
            print(f"Redis Load Error: {e}")
    return None

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, List[tuple[WebSocket, str]]] = {}

    async def connect(self, ws: WebSocket, game_id: str, player_id: str):
        await ws.accept()
        if game_id not in self.active: self.active[game_id] = []
        self.active[game_id].append((ws, player_id))

    def disconnect(self, ws: WebSocket, game_id: str):
        if game_id in self.active:
            self.active[game_id] = [c for c in self.active[game_id] if c[0] != ws]
            if not self.active[game_id]: del self.active[game_id]

    async def broadcast(self, game_id: str, message: dict):
        if game_id not in self.active: return
        for ws, _ in self.active[game_id]:
            try: await ws.send_json(message)
            except: pass

manager = ConnectionManager()

# --- Models ---
class CreateGameRequest(BaseModel):
    playerName: str = "Player 1"
    gameName: Optional[str] = None
    opponentName: str = "Player 2"
    deckName: Optional[str] = None
    opponentDeckName: Optional[str] = None
    startingLife: int = 20

class JoinGameRequest(BaseModel):
    playerName: str

class SaveDeckRequest(BaseModel):
    name: str
    cards: List[str]

class FetchCardRequest(BaseModel):
    cardName: str

# --- API Endpoints ---
@app.get("/api/games")
async def list_games():
    """List active games."""
    game_list = []
    if redis_client:
        active_ids = redis_client.smembers("mtg_active_games")
        for gid in active_ids:
            meta = redis_client.get(f"{REDIS_PREFIX}meta:{gid}")
            if meta: game_list.append(json.loads(meta))
    return {"success": True, "games": game_list}

@app.post("/api/games")
async def create_lobby_game(req: CreateGameRequest): # Using CreateGameRequest/CreateLobbyGameRequest unified logic
    """Create a new game."""
    game = Game()
    gid = str(uuid4())
    p1 = Player(req.playerName, req.startingLife)
    game.add_player(p1)
    
    games[gid] = game
    save_game(gid, game)
    if redis_client:
        name_to_use = req.gameName if req.gameName and req.gameName.strip() else f"{req.playerName}'s Game"
        meta = {"name": name_to_use, "player_count": 1, "player_names": [req.playerName], "game_id": gid}
        redis_client.set(f"{REDIS_PREFIX}meta:{gid}", json.dumps(meta))
    
    return {"success": True, "gameId": gid, "playerId": p1.id, "state": game.to_dict()}

@app.post("/api/games/{gid}/join")
async def join_game(gid: str, req: JoinGameRequest):
    game = load_game(gid)
    if not game: raise HTTPException(404, "Game not found")
    if len(game.players) >= 2: raise HTTPException(400, "Game full")
    
    p2 = Player(req.playerName)
    game.add_player(p2)
    save_game(gid, game)
    
    # Update metadata
    if redis_client:
        meta = json.loads(redis_client.get(f"{REDIS_PREFIX}meta:{gid}") or "{}")
        meta["player_count"] = 2
        meta["player_names"].append(req.playerName)
        redis_client.set(f"{REDIS_PREFIX}meta:{gid}", json.dumps(meta))

    await manager.broadcast(gid, {"type": "game_state", "state": game.to_dict()})
    return {"success": True, "playerId": p2.id, "state": game.to_dict()}

@app.get("/api/game/{game_id}/state")
async def get_game_state(game_id: str):
    print(f"🔍 Fetching state for game: {game_id}")
    game = load_game(game_id)
    if not game:
        print(f"❌ Game not found: {game_id}")
        raise HTTPException(status_code=404, detail="Game not found")
    print(f"✅ Found game state for: {game_id}")
    return {"success": True, "state": game.to_dict()}

@app.delete("/api/games/{game_id}")
async def delete_game(game_id: str):
    print(f"🗑️ Deleting game: {game_id}")
    
    # Remove from memory
    if game_id in games:
        del games[game_id]
        
    # Remove from Redis
    if redis_client:
        redis_client.delete(f"{REDIS_PREFIX}{game_id}")
        redis_client.delete(f"{REDIS_PREFIX}meta:{game_id}")
        redis_client.srem("mtg_active_games", game_id)
        
    return {"success": True}

@app.post("/api/decks")
async def save_deck(req: SaveDeckRequest):
    """Save deck and background fetch missing cards."""
    filename = re.sub(r'[^a-z0-9_]', '_', req.name.lower()) + ".json"
    deck_path = os.path.join("../frontend/public/decks", filename)
    os.makedirs(os.path.dirname(deck_path), exist_ok=True)
    
    # Normalize card names to simple IDs
    card_ids = [re.sub(r'[^a-z0-9]', '_', c.lower().replace("'", "")) for c in req.cards]
    
    with open(deck_path, 'w') as f:
        json.dump({"name": req.name, "main": card_ids}, f, indent=2)
    
    # Update Index
    index_path = os.path.join("../frontend/public/decks", "index.json")
    try:
        with open(index_path, 'r+') as f:
            data = json.load(f)
            if req.name not in data.get("decks", []):
                data.setdefault("decks", []).append(req.name)
                f.seek(0)
                json.dump(data, f, indent=2)
    except: pass
    
    asyncio.create_task(asyncio.to_thread(fetch_missing_cards, req.cards))
    return {
        "success": True,
        "deck_name": req.name,
        "card_count": len(card_ids),
        "filename": filename
    }

@app.post("/api/cards/fetch")
async def fetch_new_card(request: FetchCardRequest):
    """
    Fetch a new card from Scryfall, save its image, and add to database.
    """
    print(f"🔍 Fetching card: {request.cardName}")
    
    # Run synchronous fetch/download in a thread pool
    def process_fetch():
        success, metadata, error = card_fetcher.fetch_card_data(request.cardName)
        if not success:
            return False, None, error
            
        image_url = metadata.get("scryfall_image_url")
        if not image_url:
            return False, None, "No image URL found"
            
        # Download image
        filename = os.path.basename(metadata["image"])
        if not card_fetcher.download_image(image_url, filename):
            return False, None, "Failed to download image"
            
        # Update JSON database
        if not card_fetcher.update_cards_json(metadata):
            return False, None, "Failed to update database"
            
        return True, metadata, None

    loop = asyncio.get_event_loop()
    success, metadata, error = await loop.run_in_executor(None, process_fetch)
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    # Update in-memory database
    if metadata:
        if "scryfall_image_url" in metadata:
            del metadata["scryfall_image_url"]
        card_database[metadata["id"]] = metadata
        print(f"✅ Added {metadata['name']} to in-memory database")
    
    return {
        "success": True,
        "card": metadata
    }

def fetch_missing_cards(cards: List[str]):
    db = load_card_database()
    # Check for missing cards using simple normalized IDs
    missing = []
    for c in cards:
        # Normalize name to ID: "Lightning Bolt" -> "lightning_bolt"
        normalized_id = re.sub(r'[^a-z0-9]', '_', c.lower().replace("'", ""))
        normalized_id = re.sub(r'_+', '_', normalized_id).strip('_')
        
        if normalized_id not in db:
            missing.append(c)
            
    for name in missing:
        success, meta, _ = card_fetcher.fetch_card_data(name)
        if success and meta:
            card_fetcher.download_image(meta.pop('scryfall_image_url'), os.path.basename(meta['image']))
            card_fetcher.update_cards_json(meta)
            time.sleep(0.1)

# --- WebSocket ---
@app.websocket("/ws/{gid}/{pid}")
async def websocket_endpoint(ws: WebSocket, gid: str, pid: str):
    game = load_game(gid)
    if not game or pid not in game.players:
        await ws.close(1008)
        return
        
    await manager.connect(ws, gid, pid)
    try:
        await ws.send_json({"type": "game_state_update", "state": game.to_dict()})
        while True:
            data = await ws.receive_json()
            action = data.get("action")
            d = data.get("data", {})
            
            # Action Dispatch
            success = False
            player = game.players.get(pid)
            
            if action == "draw":
                player.draw(d.get("count", 1))
                success = True
            elif action == "move_card":
                success = game.move_card(d.get("cardId"), d.get("toPlayerId", pid), ZoneType(d.get("toZone")), d.get("index"))
                if success and d.get("toZone") == "battlefield" and "x" in d:
                    c = game.find_card(d["cardId"])[0]
                    c.data['x'], c.data['y'] = d["x"], d["y"]
            elif action == "tap_card": success = game.toggle_tap_card(d.get("cardId"))
            elif action == "untap_all": 
                game.untap_all_permanents()
                success = True
            elif action == "change_life":
                player.change_life(d.get("delta", 0))
                success = True
            elif action == "shuffle":
                player.shuffle_library()
                success = True
            elif action == "load_deck":
                 print(f"📂 Loading deck '{d['deckName']}' for player {pid}")
                 player.zones[ZoneType.LIBRARY].cards.clear()
                 count = create_deck_for_player(d["deckName"], player)
                 print(f"✅ Loaded {count} cards into library")
                 success = True
            elif action == "attach_card":
                success = game.attach_card(d.get("cardId"), d.get("targetCardId"))
            elif action == "unattach_card":
                success = game.unattach_card(d.get("cardId"))
            elif action == "add_counter":
                card_result = game.find_card(d.get("cardId"))
                if card_result:
                    card = card_result[0]
                    # Normalize counter type key
                    ctype = d.get("counterType", "counter").replace("/", "")
                    key = f"counters_{ctype}"
                    current = card.data.get(key, 0)
                    card.data[key] = max(0, current + d.get("delta", 1))
                    success = True
            elif action == "create_token":
                player = game.players.get(pid)
                if player:
                    token_name = d.get("name", "Token")
                    # Import Card here to avoid circular or just use game's context if possible?
                    # We need to import Card at top level or here. It's already imported.
                    from card_engine import Card
                    token = Card(token_name, pid, {
                        "is_token": True,
                        "power": d.get("power", "1"),
                        "toughness": d.get("toughness", "1")
                    })
                    player.zones[ZoneType.BATTLEFIELD].add(token)
                    success = True
            
            if success:
                save_game(gid, game)
                await manager.broadcast(gid, {"type": "game_state_update", "state": game.to_dict()})
            
    except WebSocketDisconnect:
        manager.disconnect(ws, gid)

# --- Startup ---
card_database = load_card_database()
init_redis()
if redis_client:
    for gid in redis_client.smembers("mtg_active_games"): load_game(gid)

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=9000)
