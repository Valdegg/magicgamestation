# Magic Workstation Clone

A fully-featured web-based Magic: The Gathering multiplayer game client inspired by the classic Magic Workstation (MWS). Play with your custom decks in real-time with friends, no rules enforcement - just like the original!

## Overview

This is a **complete multiplayer web application** featuring:
- 🎮 **Real-time multiplayer gameplay** via WebSocket
- 🃏 **Advanced deck builder** with card search, autocomplete, and visual preview
- 🎨 **Beautiful fantasy-themed UI** with mana symbols and card artwork
- 📦 **Automatic card fetching** from Scryfall (always oldest printing/Alpha when available)
- 💾 **Persistent game state** with Redis backend
- 🚫 **No rules enforcement** - manual gameplay like classic MWS

The system consists of:
- **Backend**: FastAPI + Redis + WebSocket server
- **Frontend**: React + TypeScript + Tailwind CSS
- **Card Engine**: Pure Python rules-agnostic game state manager

## ✨ Key Features

### 🎮 Multiplayer Gameplay
- Real-time game state synchronization via WebSocket
- Create and join games with unique game IDs
- Persistent player sessions (localStorage + Redis)
- "Return to Lobby" opens in new tab (keep game alive)
- Multiple games running simultaneously

### 🃏 Deck Building
- **Smart card search** with prefix matching autocomplete
- **Visual card preview** showing card images in suggestions
- **Specify card counts** (e.g., "4 Lightning Bolt" or "20 Mountain")
- **Enter key selection** - press Enter to add top suggestion
- **Fetch from Scryfall** - automatically downloads missing cards
- **Always oldest printing** - fetches Alpha/LEA versions when available
- **Visual deck preview** - see all cards in a grid as you build
- **Save as .txt files** - standard deck list format

### 🎨 User Interface
- Beautiful fantasy-themed styling with golden accents
- Mana symbol decorations (WUBRG)
- Scrollable modals and responsive design
- Card image integration with fallback handling
- Real-time visual feedback

### 🎲 Game Engine
- Rules-agnostic card state management
- Standard MTG zones: Library, Hand, Battlefield, Graveyard, Exile, Command
- Manual actions: tap/untap, flip face-down, move between zones
- Life total tracking
- Turn progression
- Full JSON serialization for network sync

### 📦 Technical Features
- FastAPI backend with WebSocket support
- Redis for persistent game state
- React frontend with TypeScript
- Scryfall API integration
- Card database management
- Framer Motion animations

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- **Redis server** (Required)
- **ngrok** (Required for remote play)

### Installation

1. **Clone the repository**
```bash
git clone <repo-url>
cd magicworkstation
```

2. **Install Backend Dependencies**
```bash
pip install -r backend/requirements.txt
```

3. **Install Frontend Dependencies**
```bash
cd frontend
npm install
cd ..
```

### 🎮 Start Server (Remote Play - Recommended)

This is the standard way to run the app. It starts the backend, frontend, and creates public ngrok tunnels so you can play with friends over the internet.

```bash
./start_server.sh
```

Follow the on-screen instructions to share the URL with your friend.

### 🏠 Start Local Server (Offline/Dev)

If you only want to play locally on your machine or for development, use the `-local` flag:

```bash
./start_server.sh -local
```

Visit `http://localhost:5173` in your browser.

## 🎯 How to Use

1. **Enter your name** in the lobby
2. **Create a custom deck** or use an existing one
   - Search for cards (supports prefix matching)
   - Specify quantities: "4 Lightning Bolt"
   - Press Enter to add the top suggestion
   - Click "Fetch from Web" for cards not in local database
3. **Create a new game** or join an existing one
4. **Play!** - All actions are manual:
   - Drag cards between zones
   - Click to tap/untap
   - Right-click for additional options
   - Manually track life totals
   - Advance turns when ready

## 📖 Documentation

- [FEATURES.md](docs/FEATURES.md) - Complete feature list
- [NGROK_SETUP.md](docs/NGROK_SETUP.md) - Details on how remote play works

## 🏗️ Project Structure

```
magicworkstation/
├── backend/                   # Backend Code
│   ├── backend_server.py      # FastAPI WebSocket server
│   ├── card_engine.py         # Core game engine (rules-agnostic)
│   └── card_fetcher.py        # Scryfall API integration
├── frontend/                  # Frontend Code
│   ├── src/
│   │   ├── App.tsx            # Main app component
│   │   ├── components/        # React components
│   │   ├── context/           # State management
│   │   └── utils/
│   ├── public/
│   │   └── data/
│   │       └── cards.json     # Local card database
│   └── card_images/           # Downloaded card images
├── docs/                      # Documentation
├── decks/                     # Saved deck files (.txt)
├── start_server.sh            # Main launcher (Remote & Local)
├── backend/start_backend.sh   # Helper script
└── frontend/start_frontend.sh # Helper script
```

## 🎯 Design Philosophy

This project follows the classic Magic Workstation philosophy:

✅ **No Rules Enforcement** - Players manually perform all actions  
✅ **Pure State Management** - The engine just tracks the game state  
✅ **Manual Gameplay** - Trust players to follow the rules  
✅ **Flexible & Fast** - No validation overhead, play at your own pace  

### What This Does NOT Do

❌ Enforce Magic rules or card legality  
❌ Automatically resolve the stack  
❌ Calculate damage or life changes  
❌ Prevent illegal moves  
❌ Validate turn structure  

**This is by design!** Just like the original MWS, players have full control.

## 🛠️ Tech Stack

- **Backend**: Python 3.9+, FastAPI, WebSocket, Redis, Pydantic
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Framer Motion
- **APIs**: Scryfall (card data & images)
- **Database**: Redis (game state), JSON (card metadata)

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📜 License

Educational/personal use. Magic: The Gathering is © Wizards of the Coast.

## 🙏 Acknowledgments

- Inspired by the classic **Magic Workstation** by Magi-Soft
- Card data from **Scryfall API**
- Built with love for the MTG community

---

**Start playing now!** Run `./start_server.sh` and play with a friend! 🎴✨
