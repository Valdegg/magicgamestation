# ngrok Setup Guide for Magic Gamestation

This guide explains how remote play works using ngrok and how to use the automated setup script.

## 🚀 The Easy Way

We have automated the entire process of setting up tunnels and configuring the app.

Simply run:

```bash
./start_remote_play.sh
```

This script will:
1. Start the Backend server (port 9000)
2. Start the Frontend server (port 5173)
3. Create a temporary ngrok configuration file
4. Start **two tunnels** simultaneously (one for backend, one for frontend)
5. Automatically detect the public URLs
6. Configure the frontend to talk to the public backend URL
7. Print the shareable URL for you to send to friends

**Requirements:**
- `ngrok` installed and authenticated
- `jq` installed (optional, but recommended for reliable URL detection)

## 🔧 How It Works (Under the Hood)

### The Problem
When you run a web app locally, it runs on `localhost`. If you just share your frontend via a tunnel, the frontend code running on your friend's browser will try to call API endpoints at `http://localhost:9000`. 

But for your friend, `localhost:9000` is **their** computer, not yours! So the game breaks.

### The Solution
To fix this, we need to:
1. Expose the **Frontend** via a tunnel (so they can load the page)
2. Expose the **Backend** via a tunnel (so the page can talk to the API)
3. Tell the Frontend to use the **Public Backend URL** instead of localhost

### Manual Process (If the script fails)

If `start_remote_play.sh` doesn't work for you, you can do it manually:

1. **Start Backend**
   ```bash
   ./start_backend.sh
   ```

2. **Start Frontend**
   ```bash
   ./start_frontend.sh
   ```

3. **Create ngrok config file (`ngrok.yml`)**
   ```yaml
   version: "2"
   tunnels:
     backend:
       proto: http
       addr: 9000
     frontend:
       proto: http
       addr: 5173
   ```

4. **Start ngrok**
   ```bash
   ngrok start --all --config=ngrok.yml
   ```

5. **Copy the Backend URL** from the ngrok output (e.g., `https://api-123.ngrok-free.app`)

6. **Configure Frontend**
   You need to set the environment variable `VITE_API_URL` before building/running the frontend, or update the code.
   
   The automated script handles this by setting environment variables `VITE_API_URL` and `VITE_WS_URL` which the frontend code reads.

## 🐛 Troubleshooting

### "ngrok not found"
Install ngrok:
```bash
# macOS
brew install ngrok

# Or download from
# https://ngrok.com/download
```

### ngrok authentication required
```bash
# Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken
ngrok authtoken YOUR_TOKEN_HERE
```

### "jq not found"
The script uses `jq` to parse ngrok's JSON API to find the public URLs.
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq
```

Without `jq`, the script attempts to use `grep`/`cut`, which is less reliable.

## 🔒 Security Notes

**⚠️ Warning:** The current setup allows all origins (`*`) for CORS to make development easy. This means any website can technically talk to your game backend while it's running.

Since this is a game with no sensitive user data (just card game state), this is generally acceptable for casual play with friends. Do not use this configuration for production deployment with real user data.
