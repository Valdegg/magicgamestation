# ngrok Setup Explained - Why You Need BOTH Tunnels

## 🤔 The Question: One Tunnel or Two?

**Short Answer: You need BOTH tunnels for remote access.**

## 📊 Visual Explanation

### ❌ ONE Tunnel (Frontend Only) - DOESN'T WORK

```
┌─────────────────────────────────────────────────────────────┐
│  YOUR COMPUTER                                              │
│                                                             │
│  ┌─────────────┐         ┌─────────────┐                  │
│  │  Backend    │         │  Frontend   │                  │
│  │  :9000      │◄────────┤  :5173      │                  │
│  └─────────────┘         └─────────────┘                  │
│                                │                            │
│                                │                            │
│                          ┌─────▼──────┐                    │
│                          │   ngrok    │                    │
│                          └─────┬──────┘                    │
└────────────────────────────────┼─────────────────────────────┘
                                 │
                    https://abc.ngrok-free.app
                                 │
┌────────────────────────────────▼─────────────────────────────┐
│  FRIEND'S BROWSER                                            │
│                                                              │
│  ┌──────────────────────────────────────────────┐          │
│  │  Loads: https://abc.ngrok-free.app           │          │
│  │  (Frontend works! ✅)                         │          │
│  │                                               │          │
│  │  Tries to connect to:                        │          │
│  │  http://localhost:9000  ❌ THEIR localhost!  │          │
│  │                                               │          │
│  │  Result: Connection failed! 💥               │          │
│  └──────────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────────────┘
```

**Problem:** The frontend HTML/JS loads, but it tries to connect to `localhost:9000` which is the friend's computer, not yours!

---

### ✅ TWO Tunnels (Frontend + Backend) - WORKS!

```
┌─────────────────────────────────────────────────────────────┐
│  YOUR COMPUTER                                              │
│                                                             │
│  ┌─────────────┐         ┌─────────────┐                  │
│  │  Backend    │         │  Frontend   │                  │
│  │  :9000      │         │  :5173      │                  │
│  └──────┬──────┘         └──────┬──────┘                  │
│         │                       │                          │
│   ┌─────▼──────┐          ┌─────▼──────┐                 │
│   │ ngrok #1   │          │ ngrok #2   │                 │
│   └─────┬──────┘          └─────┬──────┘                 │
└─────────┼─────────────────────────┼───────────────────────┘
          │                         │
    backend-url.ngrok         frontend-url.ngrok
          │                         │
          │                         │
┌─────────▼─────────────────────────▼───────────────────────┐
│  FRIEND'S BROWSER                                          │
│                                                            │
│  1. Visits: https://frontend-url.ngrok-free.app           │
│     └─► Loads frontend ✅                                 │
│                                                            │
│  2. Frontend connects to: https://backend-url.ngrok...    │
│     └─► API & WebSocket work! ✅                          │
│                                                            │
│  Result: Everything works perfectly! 🎉                   │
└────────────────────────────────────────────────────────────┘
```

**Success:** Both the frontend page AND the backend API are accessible from the internet!

---

## 🛠️ How to Set It Up

### Step 1: Start Your App
```bash
Terminal 1: ./start_backend.sh
Terminal 2: ./start_frontend.sh
```

### Step 2: Expose Backend
```bash
Terminal 3: ./start_ngrok_backend.sh
```

You'll see:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:9000
```

**Copy that URL!** ☝️

### Step 3: Configure Frontend
```bash
Terminal 4: ./configure_ngrok_urls.sh https://abc123.ngrok-free.app
```

This script automatically updates:
- `frontend/src/api/gameApi.ts` (REST API)
- `frontend/src/context/GameStateWebSocket.tsx` (WebSocket)

### Step 4: Restart Frontend
```bash
Terminal 2: Ctrl+C
            ./start_frontend.sh
```

### Step 5: Expose Frontend
```bash
Terminal 5: ./start_ngrok.sh
```

You'll see:
```
Forwarding  https://xyz789.ngrok-free.app -> http://localhost:5173
```

**Share this URL** with your friends! 🎉

---

## 🧹 Cleanup

When you're done playing:

```bash
# Restore localhost configuration
./restore_localhost.sh

# Stop all ngrok tunnels (Ctrl+C in their terminals)
```

---

## 💰 Cost

**FREE!** ngrok's free tier allows:
- ✅ 1 tunnel at a time per process
- ✅ But you can run MULTIPLE ngrok processes (one per terminal)
- ✅ Unlimited bandwidth
- ⚠️ URLs change each time (unless you pay for static domains)

---

## 🎮 Ready to Play!

Follow the steps above, share your frontend ngrok URL with friends, and enjoy Magic: The Gathering online! 🎴✨

