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
from card_database import load_card_database, create_deck_for_player, clear_deck_cache
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
    if game_id in games:
        game = games[game_id]
        # Ensure chat_messages exists (for games loaded before this feature was added)
        if not hasattr(game, 'chat_messages'):
            game.chat_messages = []
        return game
    if redis_client:
        try:
            data = redis_client.get(f"{REDIS_PREFIX}{game_id}")
            if data:
                game = Game.from_dict(json.loads(data))
                # Ensure chat_messages exists (for games saved before this feature was added)
                if not hasattr(game, 'chat_messages'):
                    game.chat_messages = []
                games[game_id] = game
                return game
        except Exception as e:
            print(f"Redis Load Error: {e}")
    return None

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, List[tuple[WebSocket, str]]] = {}
        self.lobby_connections: List[WebSocket] = []  # List of WebSocket connections in lobby

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

    async def connect_lobby(self, ws: WebSocket):
        await ws.accept()
        self.lobby_connections.append(ws)

    def disconnect_lobby(self, ws: WebSocket):
        if ws in self.lobby_connections:
            self.lobby_connections.remove(ws)

    async def broadcast_lobby(self, message: dict):
        disconnected = []
        for ws in self.lobby_connections:
            try:
                await ws.send_json(message)
            except:
                disconnected.append(ws)
        # Remove disconnected connections
        for ws in disconnected:
            self.disconnect_lobby(ws)

manager = ConnectionManager()

# Global lobby chat messages (persisted in Redis if available)
lobby_chat_messages: List[Dict[str, Any]] = []
LOBBY_CHAT_KEY = "mtg_lobby_chat"

def load_lobby_chat():
    """Load lobby chat messages from Redis"""
    global lobby_chat_messages
    if redis_client:
        try:
            data = redis_client.get(LOBBY_CHAT_KEY)
            if data:
                lobby_chat_messages = json.loads(data)
                # Keep only last 100 messages
                if len(lobby_chat_messages) > 100:
                    lobby_chat_messages = lobby_chat_messages[-100:]
        except Exception as e:
            print(f"Redis Load Error (lobby chat): {e}")
    return lobby_chat_messages

def save_lobby_chat():
    """Save lobby chat messages to Redis"""
    if redis_client:
        try:
            redis_client.set(LOBBY_CHAT_KEY, json.dumps(lobby_chat_messages))
        except Exception as e:
            print(f"Redis Save Error (lobby chat): {e}")

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

class LoadDeckRequest(BaseModel):
    deckName: str
    playerId: Optional[str] = None

@app.post("/api/game/{game_id}/load-deck")
async def load_deck_endpoint(game_id: str, req: LoadDeckRequest):
    """Load a deck for a player in a game."""
    print(f"📂 Loading deck via REST API for game: {game_id}, requested playerId: {req.playerId}, deckName: {req.deckName}", flush=True)
    game = load_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if not req.deckName:
        raise HTTPException(status_code=400, detail="deckName is required")
    
    print(f"📂 Available players in game: {list(game.players.keys())}", flush=True)
    
    # If playerId is provided, load deck for that player, otherwise use first player
    if req.playerId and req.playerId in game.players:
        player = game.players[req.playerId]
        player_id = req.playerId
        print(f"📂 Using provided playerId: {player_id}", flush=True)
    elif len(game.players) > 0:
        # Use first player if no playerId specified
        player = list(game.players.values())[0]
        player_id = player.id
        print(f"⚠️ No playerId provided, using first player: {player_id}", flush=True)
    else:
        raise HTTPException(status_code=400, detail="No players in game")
    
    print(f"📂 Loading deck '{req.deckName}' for player {player_id} ({player.name})", flush=True)
    player.zones[ZoneType.LIBRARY].cards.clear()
    # Use cached card database instead of reloading it
    count = create_deck_for_player(req.deckName, player, database=card_database)
    print(f"✅ Loaded {count} cards into library for player {player_id}", flush=True)
    
    # Save game state
    save_game(game_id, game)
    
    # Broadcast update to all connected clients
    await manager.broadcast(game_id, {
        "type": "game_state_update",
        "state": game.to_dict()
    })
    
    return {"success": True, "cardsLoaded": count}

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
    
    # Clear deck cache for this deck so it reloads with new data
    clear_deck_cache(req.name)
    
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
    print(f"🔍 Fetching card: {request.cardName}", flush=True)
    
    # Run synchronous fetch/download in a thread pool
    def process_fetch():
        print(f"   🔄 process_fetch started for: '{request.cardName}'", flush=True)
        success, metadata, error = card_fetcher.fetch_card_data(request.cardName)
        if not success:
            print(f"   ❌ fetch_card_data failed: {error}", flush=True)
            return False, None, error
            
        image_url = metadata.get("scryfall_image_url")
        if not image_url:
            print(f"   ❌ No image URL in metadata", flush=True)
            return False, None, "No image URL found"
            
        # Download image
        filename = os.path.basename(metadata["image"])
        print(f"   📥 Starting image download...", flush=True)
        if not card_fetcher.download_image(image_url, filename):
            print(f"   ❌ Image download failed", flush=True)
            return False, None, "Failed to download image"
            
        # Update JSON database
        print(f"   💾 Starting database update...", flush=True)
        if not card_fetcher.update_cards_json(metadata):
            print(f"   ❌ Database update failed", flush=True)
            return False, None, "Failed to update database"
            
        print(f"   ✅ process_fetch completed successfully", flush=True)
        return True, metadata, None

    loop = asyncio.get_event_loop()
    success, metadata, error = await loop.run_in_executor(None, process_fetch)
    
    if not success:
        print(f"❌ Card fetch failed: {error}", flush=True)
        raise HTTPException(status_code=400, detail=error)
    
    # Update in-memory database
    if metadata:
        if "scryfall_image_url" in metadata:
            del metadata["scryfall_image_url"]
        card_database[metadata["id"]] = metadata
        print(f"✅ Added {metadata['name']} to in-memory database", flush=True)
    
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
    
    # Ensure chat_messages exists before sending state
    if not hasattr(game, 'chat_messages'):
        game.chat_messages = []
        print(f"⚠️ Initialized chat_messages for game {gid}", flush=True)
        
    await manager.connect(ws, gid, pid)
    try:
        game_dict = game.to_dict()
        chat_msgs = game_dict.get('chat_messages', [])
        print(f"📤 Sending initial game state - chat_messages: {len(chat_msgs)} messages, hasattr: {hasattr(game, 'chat_messages')}", flush=True)
        if len(chat_msgs) > 0:
            print(f"   First message: {chat_msgs[0]}", flush=True)
        await ws.send_json({"type": "game_state_update", "state": game_dict})
        while True:
            data = await ws.receive_json()
            action = data.get("action")
            d = data.get("data", {})
            print(f"📩 Received action: {action}, data: {d}", flush=True)
            
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
            elif action == "mulligan":
                # Put all hand cards back to library, shuffle, draw 7
                hand_zone = player.zones[ZoneType.HAND]
                library_zone = player.zones[ZoneType.LIBRARY]
                # Move all hand cards to library
                while hand_zone.cards:
                    card = hand_zone.cards.pop()
                    library_zone.add_to_bottom(card)
                # Shuffle
                player.shuffle_library()
                # Draw 7
                player.draw(7)
                print(f"🔄 Mulligan: {player.name} drew new 7")
                success = True
            elif action == "load_deck":
                 print(f"📂 Loading deck '{d['deckName']}' for player {pid}")
                 player.zones[ZoneType.LIBRARY].cards.clear()
                 # Use cached card database instead of reloading it
                 count = create_deck_for_player(d["deckName"], player, database=card_database)
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
            elif action == "chat":
                print(f"🔵 CHAT HANDLER ENTERED - message: {d.get('message')}", flush=True)
                # Extract message and validate
                message = d.get("message", "").strip()
                print(f"🔵 After strip - message: '{message}', len: {len(message) if message else 0}", flush=True)
                if message and len(message) <= 500:  # Limit to 500 chars
                    print(f"🔵 Message validation passed", flush=True)
                    # Ensure chat_messages exists (for games loaded before this feature was added)
                    if not hasattr(game, 'chat_messages'):
                        game.chat_messages = []
                    
                    player_name = player.name if player else "Unknown Player"
                    timestamp = json.dumps({"$date": int(time.time() * 1000)})

                    # Store chat message in game state for persistence
                    chat_msg = {
                        "playerId": pid,
                        "playerName": player_name,
                        "message": message,
                        "timestamp": timestamp
                    }
                    game.chat_messages.append(chat_msg)
                    # Keep only last 100 messages to avoid bloat
                    if len(game.chat_messages) > 100:
                        game.chat_messages = game.chat_messages[-100:]
                    save_game(gid, game)
                    print(f"💬 Saved chat message - total messages: {len(game.chat_messages)}", flush=True)
                    print(f"💬 Game object has chat_messages attr: {hasattr(game, 'chat_messages')}", flush=True)
                    print(f"💬 Chat messages content: {game.chat_messages}", flush=True)

                    # Broadcast chat message to all players (for real-time display)
                    await manager.broadcast(gid, {
                        "type": "chat_message",
                        **chat_msg
                    })
                    # Also broadcast full state update so chat_messages list is synced
                    game_dict = game.to_dict()
                    print(f"📤 Broadcasting game state after chat - chat_messages in dict: {len(game_dict.get('chat_messages', []))} messages", flush=True)
                    print(f"📤 Full game_dict keys: {list(game_dict.keys())}", flush=True)
                    await manager.broadcast(gid, {
                        "type": "game_state_update",
                        "state": game_dict
                    })
                    success = True
                else:
                    print(f"⚠️ Chat message validation failed - message: '{message}', len: {len(message) if message else 0}", flush=True)
            elif action == "next_phase":
                print(f"⏩ next_phase requested by player {pid}")
                print(f"   Current phase: {game.current_phase}")
                game.next_phase()
                print(f"   New phase: {game.current_phase}")
                success = True
            elif action == "set_phase":
                phase_name = d.get("phase")
                print(f"⏩ set_phase requested by player {pid} to phase: {phase_name}")
                print(f"   Current phase: {game.current_phase}")
                if game.set_phase(phase_name):
                    print(f"   New phase: {game.current_phase}")
                    success = True
                else:
                    print(f"   ⚠️ Invalid phase: {phase_name}")
                    success = False
            elif action == "next_turn":
                print(f"⏭️ next_turn requested by player {pid}")
                print(f"   Current active_player_id: {game.active_player_id}")
                print(f"   Current phase: {game.current_phase}")
                game.next_turn()
                print(f"   New active_player_id: {game.active_player_id}")
                print(f"   New phase: {game.current_phase}")
                success = True
            elif action == "create_die":
                # Create die and auto-roll
                x = d.get("x", 0)
                y = d.get("y", 0)
                die_type = d.get("dieType", "d20")
                die_id = game.create_die(x, y, pid, die_type)
                if die_id:
                    # Auto-roll on create
                    value = game.roll_die(die_id)
                    save_game(gid, game)
                    await manager.broadcast(gid, {
                        "type": "die_created_and_rolled",
                        "dieId": die_id,
                        "x": x,
                        "y": y,
                        "value": value,
                        "ownerPlayerId": pid,
                        "dieType": die_type
                    })
                    success = True
            elif action == "roll_die":
                die_id = d.get("dieId")
                if die_id:
                    value = game.roll_die(die_id)
                    if value is not None:
                        save_game(gid, game)
                        await manager.broadcast(gid, {
                            "type": "die_rolled",
                            "dieId": die_id,
                            "value": value
                        })
                        success = True
            elif action == "move_die":
                die_id = d.get("dieId")
                x = d.get("x", 0)
                y = d.get("y", 0)
                if die_id and game.move_die(die_id, x, y):
                    save_game(gid, game)
                    await manager.broadcast(gid, {
                        "type": "die_moved",
                        "dieId": die_id,
                        "x": x,
                        "y": y
                    })
                    success = True
            elif action == "remove_die":
                die_id = d.get("dieId")
                if die_id and game.remove_die(die_id):
                    save_game(gid, game)
                    await manager.broadcast(gid, {
                        "type": "die_removed",
                        "dieId": die_id
                    })
                    success = True
            elif action == "set_targeting_arrow":
                card_id = d.get("cardId")
                target_card_id = d.get("targetCardId")
                target_player_id = d.get("targetPlayerId")
                print(f"🎯 set_targeting_arrow: cardId={card_id}, targetCardId={target_card_id}, targetPlayerId={target_player_id}")
                if card_id:
                    game.set_targeting_arrow(card_id, pid, target_card_id, target_player_id)
                    print(f"   ✅ Arrow set. Total arrows: {len(game.targeting_arrows)}")
                    success = True
            elif action == "clear_targeting_arrows":
                print(f"🧹 clear_targeting_arrows for player {pid}")
                game.clear_targeting_arrows(pid)
                success = True
            
            if success:
                save_game(gid, game)
                await manager.broadcast(gid, {"type": "game_state_update", "state": game.to_dict()})
            
    except WebSocketDisconnect:
        manager.disconnect(ws, gid)

# --- Lobby WebSocket ---
@app.websocket("/ws/lobby")
async def lobby_websocket_endpoint(ws: WebSocket):
    global lobby_chat_messages  # Declare as global
    
    await manager.connect_lobby(ws)
    print(f"✅ Lobby WebSocket connected, total connections: {len(manager.lobby_connections)}", flush=True)
    
    # Start keepalive task
    async def keepalive():
        while True:
            try:
                await asyncio.sleep(30)  # Send ping every 30 seconds
                await ws.send_json({"type": "ping"})
            except:
                break
    
    keepalive_task = asyncio.create_task(keepalive())
    
    try:
        # Send existing chat messages on connect
        try:
            messages = load_lobby_chat()
            await ws.send_json({
                "type": "lobby_chat_history",
                "messages": messages
            })
            print(f"📤 Sent lobby chat history: {len(messages)} messages", flush=True)
        except Exception as e:
            print(f"⚠️ Error sending lobby chat history: {e}", flush=True)
            import traceback
            traceback.print_exc()
        
        while True:
            try:
                data = await ws.receive_json()
                
                # Handle ping/pong for keepalive
                if data.get("type") == "pong":
                    continue
                
                action = data.get("action")
                d = data.get("data", {})
                
                if action == "lobby_chat":
                    message = d.get("message", "").strip()
                    player_name = d.get("playerName", "Anonymous")
                    
                    if message and len(message) <= 500:
                        chat_msg = {
                            "playerName": player_name,
                            "message": message,
                            "timestamp": json.dumps({"$date": int(time.time() * 1000)})
                        }
                        lobby_chat_messages.append(chat_msg)
                        # Keep only last 100 messages
                        if len(lobby_chat_messages) > 100:
                            lobby_chat_messages = lobby_chat_messages[-100:]
                        save_lobby_chat()
                        
                        print(f"💬 Lobby chat message from {player_name}: {message[:50]}...", flush=True)
                        
                        # Broadcast to all lobby connections
                        await manager.broadcast_lobby({
                            "type": "lobby_chat_message",
                            **chat_msg
                        })
            except WebSocketDisconnect:
                # Client disconnected, break out of loop
                break
            except json.JSONDecodeError as e:
                print(f"⚠️ Invalid JSON received in lobby WebSocket: {e}", flush=True)
            except Exception as e:
                # Check if it's a disconnect error
                if "disconnect" in str(e).lower() or "receive" in str(e).lower():
                    break
                print(f"⚠️ Error processing lobby WebSocket message: {e}", flush=True)
                import traceback
                traceback.print_exc()
    except WebSocketDisconnect:
        pass  # Already handled above
    except Exception as e:
        print(f"❌ Lobby WebSocket error: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        print(f"🔌 Lobby WebSocket disconnected, cleaning up", flush=True)
        keepalive_task.cancel()
        manager.disconnect_lobby(ws)

# --- Startup ---
print("🚀 Backend server starting - VERSION WITH CHAT_MESSAGES", flush=True)
card_database = load_card_database()
init_redis()
load_lobby_chat()  # Load lobby chat messages on startup
if redis_client:
    for gid in redis_client.smembers("mtg_active_games"): load_game(gid)

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=9000)
