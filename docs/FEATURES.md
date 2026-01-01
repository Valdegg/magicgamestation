# Feature List

Complete documentation of all features in Magic Gamestation Clone.

## Table of Contents

- [Multiplayer Gameplay](#multiplayer-gameplay)
- [Deck Builder](#deck-builder)
- [Card Management](#card-management)
- [User Interface](#user-interface)
- [Game Engine](#game-engine)
- [Backend Features](#backend-features)
- [Technical Features](#technical-features)

---

## Multiplayer Gameplay

### Real-Time Synchronization
- **WebSocket-based** real-time game state updates
- Instant synchronization of all game actions across players
- Automatic reconnection handling
- Game state persistence across page refreshes

### Game Lobby
- **Create new games** with custom names
- **Join existing games** by game ID
- **View active games** with player count and names
- **Delete games** with confirmation dialog
- **Player name persistence** via localStorage
- **Game list auto-refresh** every 3 seconds
- **Lobby chat** - real-time chat in lobby (separate from game chat)
- **Chat connection status** - shows connection state

### Game Session Management
- **URL-based game restoration** - share game links
- **Persistent player sessions** - reconnect to your games
- **Local storage integration** - saves player/game IDs
- **"Return to Lobby" in new tab** - keeps game alive
- **Multiple concurrent games** supported

### Player Management
- Player name input with localStorage persistence
- Unique player IDs (UUID)
- Player-specific game state
- Support for 2-player games (expandable)

---

## Deck Builder

### Card Search & Selection

#### Smart Autocomplete
- **Prefix matching search** - type "Ligh" to find "Lightning Bolt"
- **Real-time filtering** - results update as you type
- **Top 10 suggestions** displayed
- **Card count specification** - prefix search with numbers (e.g., "4 Lightning Bolt")
- **Default 1 copy** when no number specified
- **Scryfall autocomplete** - fetches suggestions from Scryfall API for cards not in local database

#### Visual Card Preview
- **Card image thumbnails** in autocomplete dropdown
- **Hover hints** showing "Add X copies"
- **Set-aware images** - shows the actual card you'll get
- **Fallback handling** for missing images

#### Keyboard Shortcuts
- **Enter key** - adds top suggestion to deck
- **Auto-fetch fallback** - Enter fetches from web if no local match
- **Escape** - closes suggestions (standard behavior)

### Deck List Editor

#### Text Area Input
- **Standard deck format** - "4 Lightning Bolt" or "20 Mountain"
- **Line-by-line parsing** - one card per line
- **Flexible format** - supports with/without counts
- **Visual preview grid** - see all cards as you build
- **Card count display** - shows total cards in deck

#### Visual Preview Grid
- **Thumbnail grid layout** - all deck cards displayed
- **Responsive grid** - adjusts to screen size (6-10 columns)
- **Card hover effects** - scales on hover
- **Card tooltips** - shows card name on hover
- **Scrollable preview** - max height 200px
- **Real-time updates** - previews update as you type

### Card Fetching

#### Scryfall Integration
- **"Fetch from Web" button** - always visible in search
- **Automatic download** - fetches card data and image
- **Always oldest printing** - prefers Alpha/LEA when available
- **Database updates** - adds to local cards.json
- **Loading indicator** - shows "⏳ Fetching..."
- **Success feedback** - automatically adds to deck

#### Oldest Printing Priority
- Uses Scryfall search API with `order=released&dir=asc`
- Fetches Limited Edition Alpha (LEA) when available
- Falls back to earliest available printing
- Includes set name and code in metadata
- Downloads high-quality card images

### Deck Management

#### Save Functionality
- **Save as .txt file** - standard deck list format
- **Server-side storage** - saves to `decks/` directory
- **Format preservation** - maintains "4 CardName" format
- **Success confirmation** - shows saved filename and card count
- **Deck name validation** - requires deck name
- **Card validation** - requires at least one card

#### Deck Format
```
4 Lightning Bolt
4 Counterspell
20 Mountain

SIDEBOARD:
2 Wrath of God
1 Disenchant
```

#### Sideboard Support
- **Sideboard section** - add "SIDEBOARD:" separator in deck list
- **Visual separation** - sideboard cards shown separately in preview with vertical spacing
- **JSON format** - saved decks include optional `sideboard` field
- **Backwards compatible** - decks without sideboard work as before
- **In-game sideboarding** - modal to move cards between library and sideboard during games

---

## Card Management

### Card Database

#### Local Database (cards.json)
- **JSON-based storage** - `frontend/public/data/cards.json`
- **Card metadata** - name, set, type, mana cost, CMC, colors, oracle text
- **Unique IDs** - format: `card_name_SETCODE`
- **Normalized names** - lowercase with underscores
- **Image paths** - links to downloaded images

#### Card Properties
```json
{
  "id": "lightning_bolt_LEA",
  "name": "Lightning Bolt",
  "set": "LEA",
  "set_name": "Limited Edition Alpha",
  "image": "/card_images/Lightning_Bolt.jpg",
  "type": "Instant",
  "mana_cost": "{R}",
  "cmc": 1,
  "oracle_text": "Lightning Bolt deals 3 damage to any target.",
  "colors": ["R"]
}
```

### Image Management

#### Card Images
- **Directory**: `frontend/card_images/`
- **Format**: JPEG
- **Naming**: `Card_Name.jpg` (normalized)
- **Source**: Scryfall large/normal size
- **On-demand download** - fetched when needed
- **Persistent storage** - images cached locally

#### Image Display
- **Autocomplete thumbnails** - 8x11px previews
- **Deck preview grid** - responsive aspect ratio (2.5:3.5)
- **Fallback handling** - shows card back on error
- **Lazy loading** - efficient image loading

### Card Search Utilities

#### Name Normalization
```typescript
// For filenames: "Lightning Bolt" → "Lightning_Bolt"
// For IDs: "Lightning Bolt" → "lightning_bolt"
```

#### Fuzzy Matching
- Case-insensitive search
- Prefix matching ("Ligh" matches "Lightning Bolt")
- Handles special characters
- Supports multi-word names

---

## User Interface

### Design Theme

#### Fantasy Aesthetic
- **Dark theme** - brown/crimson gradient backgrounds
- **Golden accents** - `#d4b36b` color scheme
- **Card-style borders** - gradient borders on containers
- **Ornate typography** - fantasy-style fonts
- **Mana symbols** - decorative WUBRG icons

#### Mana Symbols
- ⚪ White (W) - Sun with rays
- 🔵 Blue (U) - Water droplet
- ⚫ Black (B) - Skull
- 🔴 Red (R) - Flame
- 🟢 Green (G) - Tree/forest

### Responsive Design

#### Scrolling Behavior
- **Page-level scrolling** - entire app scrollable
- **Modal scrolling** - deck builder independently scrollable
- **Fixed headers** - deck name stays visible
- **Fixed footers** - action buttons always accessible
- **Overflow handling** - content never cut off

#### Layout Structure
```
<outer-container: min-h-screen overflow-y-auto>
  <absolute-wrapper: overflow-y-auto>
    <content-card: max-w-4xl>
      <header: fixed>
      <scrollable-content: flex-1>
      <footer: fixed>
```

### Component Features

#### Lobby Component
- **Centered layout** - max-width 4xl container
- **Conditional name field** - hides when deck modal open
- **Active games list** - scrollable with max height
- **Action buttons** - create game, create deck
- **Delete confirmation** - prevents accidental deletion

#### Deck Builder Modal
- **Full-screen overlay** - max-height 90vh
- **Three sections**:
  1. Fixed header with title
  2. Scrollable content (deck name, search, textarea, preview)
  3. Fixed footer with Save/Cancel buttons
- **Tip text** - usage instructions
- **Error messages** - validation feedback

#### Animations
- **Framer Motion** integration
- **Fade-in effects** - initial={{ opacity: 0 }}
- **Slide transitions** - modal entrance/exit
- **Hover effects** - scale on hover (1.05x)
- **Button press** - scale on tap (0.95x)
- **Smooth suggestions** - dropdown animations

---

## Game Engine

### Core Architecture

#### Card State Management
- **Card properties**: id, name, owner, tapped, face_down, data
- **State methods**: tap(), untap(), flip_face_down(), flip_face_up()
- **Metadata storage**: flexible dict for any card data
- **JSON serialization**: to_dict() / from_dict()

#### Zone Management
- **Standard zones**: Library, Hand, Battlefield, Graveyard, Exile, Command, Stack, Sideboard
- **Zone operations**: add, remove, find, shuffle, top, bottom
- **Ordered lists**: maintains card order
- **Zone-specific behavior**: e.g., Library.shuffle()
- **Sideboard zone** - separate zone for sideboard cards during gameplay

#### Player Management
- **Player properties**: id, name, life_total, zones
- **Player methods**: draw(), shuffle_library(), change_life(), set_life()
- **Multi-zone search**: find_card() searches all zones
- **State export**: get_all_cards() for UI sync

#### Game Management
- **Game state**: players, active_player, turn_number
- **Turn progression**: next_turn() advances turns
- **Card movement**: move_card() between zones/players
- **Global search**: find_card() across all players
- **Full serialization**: complete game state export/import

### Game Actions (Manual)

#### Card Actions
- Move card between zones (including sideboard)
- Tap/untap cards
- Flip face-up/face-down
- Change controller
- Shuffle library
- Draw cards
- Attach cards (Auras, Equipment)
- Add/remove counters
- Create tokens
- Position cards on battlefield (x, y coordinates)

#### Player Actions
- Change life total
- Set life to specific value
- Search library
- Mill cards
- Exile cards
- Return cards to hand

#### Game Actions
- Start game
- Next turn / Set phase manually
- Phase tracking (Untap, Upkeep, Draw, Main, Combat, End, Cleanup)
- Reset game
- Export/import state
- Multiplayer sync
- Create dice tokens (d6, d20)
- Set targeting arrows between cards/players
- Lobby chat messaging

### In-Game Features

#### Library Management
- **Search Library Modal** - search and filter library cards
- **Drag cards** to hand, graveyard, or battlefield
- **Click actions** - quick buttons to move cards
- **Visual card grid** - see all library cards at once

#### Sideboard Management
- **Sideboard Modal** - dedicated interface for sideboarding
- **Sideboard row** - horizontal scrollable row at top
- **Library grid** - searchable grid below
- **Move cards** - click buttons or drag to move between library and sideboard
- **No hover zoom** - optimized for quick card selection

#### Dice Tokens
- **Create dice** - d6 and d20 dice tokens
- **Roll dice** - click to roll and show value
- **Position on battlefield** - place dice anywhere
- **Remove dice** - right-click to remove
- **Per-player dice** - each player has their own dice

#### Targeting System
- **Targeting arrows** - visual arrows between cards
- **Card-to-card targeting** - show spell targeting
- **Player targeting** - target players directly
- **Clear targeting** - remove all arrows

#### Card Attachments
- **Attach cards** - attach Auras/Equipment to creatures
- **Visual stacking** - attached cards appear offset
- **Unattach** - remove attachments
- **Multiple attachments** - stack multiple attachments

#### Counters System
- **Add counters** - any counter type (e.g., +1/+1, -1/-1, loyalty)
- **Custom counter names** - specify counter type
- **Increment/decrement** - adjust counter values
- **Visual display** - counters shown on cards

#### Token Creation
- **Create tokens** - custom name, power, toughness
- **Token properties** - stored in card data
- **Visual distinction** - tokens marked as such
- **Full functionality** - tokens work like regular cards

#### Phase Tracking
- **Phase buttons** - click to advance phases
- **Phase display** - shows current phase
- **Manual control** - set any phase directly
- **Turn progression** - automatic turn advancement

#### Chat System
- **Lobby chat** - chat in the game lobby
- **Game chat** - in-game chat during matches
- **Real-time messaging** - WebSocket-based
- **Connection status** - shows chat connection state
- **Message history** - persists during session

---

## Backend Features

### FastAPI Server

#### HTTP Endpoints
```python
GET    /api/games           # List all games
POST   /api/games           # Create game
POST   /api/games/{id}/join # Join game
DELETE /api/games/{id}      # Delete game
POST   /api/decks           # Save deck (with optional sideboard)
POST   /api/cards/fetch     # Fetch card from Scryfall
POST   /api/game/{id}/load-deck # Load deck into game
```

#### Request/Response Models (Pydantic)
- `CreateGameRequest` - game name, player name
- `JoinGameRequest` - player name
- `SaveDeckRequest` - deck name, cards list, optional sideboard list
- `FetchCardRequest` - card name
- `LoadDeckRequest` - deck name, optional player ID
- `ApiResponse` - success, data, error

### WebSocket Server

#### Connection Management
- **Per-game connections** - `/ws/{game_id}/{player_id}`
- **ConnectionManager** - tracks active connections
- **Broadcast to game** - sends updates to all players in game
- **Automatic cleanup** - removes disconnected players

#### Message Types
- **game_state** - full game state update
- **action** - player action notification
- **error** - error messages
- **connection** - connection status

### Redis Integration

#### Game State Persistence
- **Key pattern**: `game:{game_id}`
- **JSON storage** - serialized game state
- **Metadata storage**: `game:{game_id}:meta`
- **Game list**: `games` set with all game IDs
- **Automatic expiry** - optional TTL
- **Atomic operations** - safe concurrent access

#### Data Structure
```python
{
  "game_id": "uuid",
  "name": "Game Name",
  "players": [...],
  "turn_number": 1,
  "active_player_id": "uuid",
  "created_at": "timestamp"
}
```

### Card Fetcher Module

#### Scryfall API Integration
```python
def fetch_card_data(card_name: str) -> Tuple[bool, Dict, str]:
    # 1. Search Scryfall with exact name match
    # 2. Order by release date (oldest first)
    # 3. Get first result (Alpha/LEA preferred)
    # 4. Download card image
    # 5. Update local database
    # 6. Return metadata
```

#### Features
- Always fetches oldest printing
- Downloads high-quality images
- Updates cards.json atomically
- Error handling and retry logic
- Progress feedback

---

## Technical Features

### State Management

#### Frontend State
- **React Context API** - GameStateContext, CardDatabaseContext
- **Local state** - useState for component state
- **Memoization** - useMemo for expensive computations
- **Effect hooks** - useEffect for side effects
- **WebSocket state** - real-time game state sync

#### State Synchronization
- **WebSocket messages** - JSON serialized state
- **Optimistic updates** - immediate UI feedback
- **Reconciliation** - server state is source of truth
- **Error recovery** - automatic reconnection

### Data Flow

```
User Action → Frontend Component
           → WebSocket Message
           → Backend Handler
           → Game Engine Update
           → Redis Persistence
           → Broadcast to All Players
           → Frontend State Update
           → UI Re-render
```

### Error Handling

#### Frontend
- Try-catch blocks for API calls
- Loading states during async operations
- Error messages in UI
- Fallback UI for missing data
- Image error handling

#### Backend
- Pydantic validation
- HTTP error codes (400, 404, 500)
- WebSocket error messages
- Logging for debugging
- Graceful degradation

### Performance Optimizations

#### Frontend
- **Component memoization** - React.memo for expensive components
- **Debounced search** - reduces API calls
- **Lazy image loading** - loads images as needed
- **Virtual scrolling** - efficient large lists (potential)
- **Code splitting** - smaller bundle sizes

#### Backend
- **Redis caching** - fast state access
- **Connection pooling** - efficient database connections
- **Async/await** - non-blocking operations
- **WebSocket multiplexing** - single connection per client
- **JSON compression** - smaller payloads (potential)

### Security Considerations

#### Current Implementation
- No authentication (local/trusted networks)
- No input sanitization (trusted users)
- No rate limiting (development mode)
- No HTTPS (local development)

#### Production Recommendations
- Add user authentication
- Implement CORS properly
- Add rate limiting
- Use HTTPS/WSS
- Sanitize all inputs
- Add CSRF protection

---

## Feature Roadmap

### Completed ✅
- [x] Real-time multiplayer gameplay
- [x] WebSocket synchronization
- [x] Deck builder with autocomplete
- [x] Card search and filtering
- [x] Scryfall integration
- [x] Oldest printing preference
- [x] Visual card preview
- [x] Enter key selection
- [x] Custom copy counts
- [x] Scrollable UI
- [x] Game lobby
- [x] Persistent sessions
- [x] Redis game state
- [x] Sideboard support (deck building & in-game)
- [x] Lobby chat
- [x] Game chat
- [x] Dice tokens (d6, d20)
- [x] Targeting arrows
- [x] Card attachments
- [x] Counters system
- [x] Token creation
- [x] Phase tracking
- [x] Library search modal
- [x] Sideboard modal

### Potential Enhancements 🚀
- [ ] Tap/untap animations
- [ ] Deck import from file
- [ ] Multiple deck slots per player
- [ ] Game history/replay
- [ ] Undo/redo actions
- [ ] Card search/filter in hand/library
- [ ] Deck statistics (mana curve, color distribution)

### Known Limitations ⚠️
- No rules enforcement (by design)
- No automatic stack resolution
- No combat math calculation
- Limited to 2 players currently
- No card legality checking
- No deck size validation

---

## Usage Examples

### Creating a Deck

1. Enter your name in the lobby
2. Click "Create Deck"
3. Type "4 Light" and press Enter (adds 4 Lightning Bolt)
4. Type "20 Mountain" and press Enter
5. See visual preview of your deck
6. Click "Save Deck"

### Fetching a Missing Card

1. In deck builder, search for "Sol Ring"
2. If not in local database, click "Fetch from Web"
3. System fetches Alpha version from Scryfall
4. Card automatically added to deck
5. Image downloaded to local storage
6. Card available in future searches

### Joining a Game

1. Enter your name
2. See list of active games
3. Click "Join Game" on available game
4. Redirected to game view
5. WebSocket connects automatically
6. Game state synchronized in real-time

---

**Total Features**: 100+ individual features across the stack!

