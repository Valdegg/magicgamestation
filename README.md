# Magic Gamestation

A web-based Magic: The Gathering multiplayer game client inspired by the classic Magic Workstation. Play with your custom decks in real-time with friends - no rules enforcement, just pure gameplay.

## Quick Start

```bash
# Install dependencies
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# Start server (remote play with ngrok)
./start_server.sh

# Or start locally
./start_server.sh -local
```

Visit the URL shown in your terminal and start playing!

## Features

- 🎮 **Real-time multiplayer** via WebSocket
- 🃏 **Deck builder** with card search, autocomplete, and visual preview
- 📦 **Sideboard support** - build decks with sideboards and sideboard during games
- 🎲 **Full game engine** - zones, phases, life totals, dice tokens, targeting arrows
- 💬 **Chat system** - lobby chat and in-game chat
- 🎨 **Beautiful UI** - fantasy-themed design with card artwork
- 📥 **Auto-fetch cards** - downloads missing cards from Scryfall (prefers Alpha/LEA)

## How It Works

1. **Enter your name** in the lobby
2. **Create or load a deck** - search cards, specify quantities, save your deck
3. **Create/join a game** - share the URL with a friend
4. **Play!** - drag cards, tap/untap, track life, advance phases manually

## Design Philosophy

**No rules enforcement** - players manually perform all actions, just like classic Magic Workstation. The engine only tracks game state.

## Documentation

- [FEATURES.md](docs/FEATURES.md) - Complete feature documentation
- [QUICKSTART.md](QUICKSTART.md) - Detailed setup guide
- [NGROK_SETUP.md](docs/NGROK_SETUP.md) - Remote play setup

## Tech Stack

- **Backend**: Python, FastAPI, WebSocket, Redis
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **APIs**: Scryfall (card data)

---

**Magic: The Gathering** is a trademark of Wizards of the Coast LLC. This project is not affiliated with, endorsed, sponsored, or specifically approved by Wizards of the Coast LLC.
