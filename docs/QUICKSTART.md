# Quick Start Guide

Get up and running with Magic Gamestation in minutes.

## ⚡ The Fastest Way to Play

### 1. Start the Server
We've bundled everything into one script. This starts the backend, frontend, and creates a public link for your friend.

```bash
./start_server.sh
```

### 2. Share the Link
Look for the **green URL** in the terminal output (e.g., `https://abc-123.ngrok-free.app`).
Copy this and send it to your opponent.

### 3. Create a Game
1. Open the link in your browser.
2. Enter your name in the Lobby.
3. Click **"Create New Game"**.
4. Your friend joins by entering their name and clicking **"Join Game"**.

### 4. Build a Deck (Optional)
Don't have a deck?
1. Click **"Create Deck"** in the Lobby.
2. Search for cards or paste a list (e.g., `4 Lightning Bolt`).
3. Click **"Fetch from Web"** if a card isn't found locally.
4. Save your deck.

---

## 🏠 Playing Locally

If you are developing or just testing on your own machine, use the `-local` flag:

```bash
./start_server.sh -local
```

Then visit `http://localhost:5173`. Note that this won't work for remote friends.

---

## 🎮 Controls & Gameplay

Everything is manual, just like playing with paper cards.

- **Drag & Drop**: Move cards between Hand, Battlefield, Graveyard, etc.
- **Tap/Untap**: Click a card to toggle tapped state.
- **Right-Click**: Open context menu for more actions (Flip, Counters, etc.).
- **Library**: Click to draw a card. Right-click to shuffle or search.
- **Life Total**: Click + / - on the dice to change life.

Happy gaming! 🎴

