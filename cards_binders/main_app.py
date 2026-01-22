#!/usr/bin/env python3
"""
MTG Cards Unified Web Application

Combines three main sections:
1. Collection Manager - Manage your card collection
2. Wishlist Manager - Manage your card wishlist
3. Market Scanner - View deals and scan the market for wishlist items

All running on a single port with navigation between sections.
"""

import os
import sys
import argparse
import re
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# Create main FastAPI app
app = FastAPI(
    title="MTG Cards Manager",
    description="Unified MTG Card Management System",
    version="1.0.0"
)

# Configuration
DEFAULT_PORT = 5010
IMAGE_DIR = "card_images"
IMAGE_DIR_SETS = "card_images_sets"

# Ensure image directories exist
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR_SETS, exist_ok=True)

# Mount static files
if os.path.exists(IMAGE_DIR):
    app.mount("/card_images", StaticFiles(directory=IMAGE_DIR), name="card_images")
if os.path.exists(IMAGE_DIR_SETS):
    # Custom route handler for images with semicolons (URL-encoded)
    # This must be defined BEFORE the StaticFiles mount to take precedence
    @app.get("/card_images_sets/{filename:path}")
    async def serve_card_image_sets(filename: str):
        """Serve card images with URL-encoded filenames (handles semicolons)."""
        from urllib.parse import unquote
        from fastapi.responses import FileResponse
        import os
        
        # Try decoded filename first (for URL-encoded paths)
        decoded_filename = unquote(filename)
        filepath = os.path.join(IMAGE_DIR_SETS, decoded_filename)
        
        # Security check
        abs_filepath = os.path.abspath(filepath)
        abs_dir = os.path.abspath(IMAGE_DIR_SETS)
        if not abs_filepath.startswith(abs_dir):
            return JSONResponse(content={'error': 'Invalid file path'}, status_code=400)
        
        # Try decoded filename
        if os.path.exists(filepath) and os.path.isfile(filepath):
            return FileResponse(filepath, media_type="image/jpeg")
        
        # Fallback: try original filename (for non-encoded paths)
        original_filepath = os.path.join(IMAGE_DIR_SETS, filename)
        if os.path.exists(original_filepath) and os.path.isfile(original_filepath):
            return FileResponse(original_filepath, media_type="image/jpeg")
        
        return JSONResponse(content={'error': 'File not found'}, status_code=404)
if os.path.exists('web_static'):
    app.mount("/static", StaticFiles(directory="web_static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Navigation HTML component
NAVIGATION_HTML = """
<nav class="main-navigation">
    <div class="nav-container">
        <a href="/" class="nav-logo">📖 Spellbook</a>
        <div class="nav-links">
            <a href="/" class="nav-link">Home</a>
            <a href="/collection" class="nav-link">Collection</a>
            <a href="/wishlist" class="nav-link">Wishlist</a>
            <a href="/market" class="nav-link">Market Scanner</a>
            <a href="/games" class="nav-link">Duel</a>
        </div>
        <div class="nav-auth" id="navAuthSection">
            <div id="navAuthButtons" style="display: none;">
                <button onclick="showLoginModal()" class="nav-auth-btn nav-auth-login">Login</button>
                <button onclick="showRegisterModal()" class="nav-auth-btn nav-auth-register">Register</button>
            </div>
            <div id="navUserInfo" style="display: none;">
                <span id="navUsernameDisplay" class="nav-username"></span>
                <button onclick="logout()" class="nav-auth-btn nav-auth-logout">Logout</button>
            </div>
        </div>
    </div>
</nav>
"""

NAVIGATION_CSS = """
<style>
.main-navigation {
    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
    border-bottom: 2px solid #d4af37;
    padding: 0;
    position: sticky;
    top: 0;
    z-index: 1000;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.nav-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 15px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.nav-logo {
    font-size: 1.5em;
    font-weight: bold;
    color: #d4af37;
    text-decoration: none;
    font-family: 'Cinzel', serif;
    transition: color 0.2s;
}

.nav-logo:hover {
    color: #f4d03f;
}

.nav-links {
    display: flex;
    gap: 20px;
    align-items: center;
}

.nav-link {
    color: #e0e0e0;
    text-decoration: none;
    font-weight: 500;
    padding: 8px 16px;
    border-radius: 6px;
    transition: all 0.2s;
    font-size: 0.95em;
}

.nav-link:hover {
    background: rgba(212, 175, 55, 0.1);
    color: #d4af37;
}

.nav-link.active {
    background: rgba(212, 175, 55, 0.2);
    color: #d4af37;
    border-bottom: 2px solid #d4af37;
}

.nav-auth {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-left: 20px;
}

.nav-auth-btn {
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9em;
    transition: all 0.2s;
}

.nav-auth-login {
    background: linear-gradient(135deg, #d4af37 0%, #b8941f 100%);
    color: #1a1a1a;
}

.nav-auth-login:hover {
    background: linear-gradient(135deg, #f4d03f 0%, #d4af37 100%);
    transform: scale(1.02);
}

.nav-auth-register {
    background: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555;
}

.nav-auth-register:hover {
    background: #4a4a4a;
    border-color: #d4af37;
}

.nav-auth-logout {
    background: #c53030;
    color: white;
}

.nav-auth-logout:hover {
    background: #e53e3e;
}

.nav-username {
    color: #d4af37;
    font-weight: 500;
    margin-right: 10px;
}

@media (max-width: 768px) {
    .nav-container {
        flex-direction: column;
        gap: 15px;
    }
    
    .nav-links {
        flex-wrap: wrap;
        justify-content: center;
        gap: 10px;
    }
    
    .nav-link {
        padding: 6px 12px;
        font-size: 0.85em;
    }
    
    .nav-auth {
        margin-left: 0;
    }
    
    .nav-auth-btn {
        padding: 6px 12px;
        font-size: 0.85em;
    }
}
</style>
"""

# Auth modal HTML (injected before </body>)
AUTH_MODAL_HTML = """
<!-- Global Login/Register Modal -->
<div id="authModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; justify-content: center; align-items: center;">
    <div style="background: #1a202c; padding: 30px; border-radius: 8px; max-width: 400px; width: 90%; border: 2px solid #d4af37;">
        <h2 id="authModalTitle" style="color: #d4af37; margin-top: 0; font-family: 'Cinzel', serif;">Login</h2>
        <form id="authForm" onsubmit="handleAuth(event)">
            <div style="margin-bottom: 15px;">
                <label style="display: block; color: #e0e0e0; margin-bottom: 5px;">Username</label>
                <input type="text" id="authUsername" required style="width: 100%; padding: 10px; border: 1px solid #4a5568; background: #2d3748; color: white; border-radius: 4px; box-sizing: border-box;">
            </div>
            <div style="margin-bottom: 15px;">
                <label style="display: block; color: #e0e0e0; margin-bottom: 5px;">Password</label>
                <input type="password" id="authPassword" required style="width: 100%; padding: 10px; border: 1px solid #4a5568; background: #2d3748; color: white; border-radius: 4px; box-sizing: border-box;">
            </div>
            <div id="authError" style="color: #fc8181; margin-bottom: 15px; display: none;"></div>
            <div style="display: flex; gap: 10px;">
                <button type="submit" style="flex: 1; padding: 10px; background: linear-gradient(135deg, #d4af37 0%, #b8941f 100%); color: #1a1a1a; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">Submit</button>
                <button type="button" onclick="closeAuthModal()" style="flex: 1; padding: 10px; background: #4a5568; color: white; border: none; border-radius: 4px; cursor: pointer;">Cancel</button>
            </div>
        </form>
        <p id="authSwitchText" style="text-align: center; margin-top: 15px; color: #a0aec0;">
            Don't have an account? <a href="#" onclick="switchAuthMode()" style="color: #d4af37;">Register</a>
        </p>
    </div>
</div>
"""

# Auth JavaScript (injected before </body>)
AUTH_JS = """
<script>
// Global auth state
let isLoginMode = true;
let isCheckingAuth = false;

// Check authentication status on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
});

async function checkAuthStatus() {
    if (isCheckingAuth) return;
    isCheckingAuth = true;
    
    try {
        const response = await fetch('/api/auth/me', { credentials: 'include' });
        const data = await response.json();
        
        const authButtons = document.getElementById('navAuthButtons');
        const userInfo = document.getElementById('navUserInfo');
        const usernameDisplay = document.getElementById('navUsernameDisplay');
        
        if (data.authenticated && data.username) {
            // User is logged in
            if (authButtons) authButtons.style.display = 'none';
            if (userInfo) userInfo.style.display = 'flex';
            if (usernameDisplay) usernameDisplay.textContent = data.username;
            // Sync username to localStorage for Games/Duel feature
            localStorage.setItem('mtg_user_name', data.username);
        } else {
            // User is not logged in
            if (authButtons) authButtons.style.display = 'flex';
            if (userInfo) userInfo.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        // Show login buttons on error
        const authButtons = document.getElementById('navAuthButtons');
        if (authButtons) authButtons.style.display = 'flex';
    } finally {
        isCheckingAuth = false;
    }
}

function showLoginModal() {
    isLoginMode = true;
    document.getElementById('authModalTitle').textContent = 'Login';
    document.getElementById('authModal').style.display = 'flex';
    document.getElementById('authError').style.display = 'none';
    document.getElementById('authUsername').value = '';
    document.getElementById('authPassword').value = '';
    document.getElementById('authSwitchText').innerHTML = "Don't have an account? <a href='#' onclick='switchAuthMode()' style='color: #d4af37;'>Register</a>";
}

function showRegisterModal() {
    isLoginMode = false;
    document.getElementById('authModalTitle').textContent = 'Register';
    document.getElementById('authModal').style.display = 'flex';
    document.getElementById('authError').style.display = 'none';
    document.getElementById('authUsername').value = '';
    document.getElementById('authPassword').value = '';
    document.getElementById('authSwitchText').innerHTML = "Already have an account? <a href='#' onclick='switchAuthMode()' style='color: #d4af37;'>Login</a>";
}

function switchAuthMode() {
    if (isLoginMode) {
        showRegisterModal();
    } else {
        showLoginModal();
    }
}

function closeAuthModal() {
    document.getElementById('authModal').style.display = 'none';
}

async function handleAuth(event) {
    event.preventDefault();
    
    const username = document.getElementById('authUsername').value;
    const password = document.getElementById('authPassword').value;
    const errorDiv = document.getElementById('authError');
    
    try {
        const endpoint = isLoginMode ? 'login' : 'register';
        
        const response = await fetch(`/api/auth/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Sync username to localStorage for Games/Duel feature
            localStorage.setItem('mtg_user_name', username);
            closeAuthModal();
            // Refresh the page to update UI state
            window.location.reload();
        } else {
            errorDiv.textContent = data.detail || 'Authentication failed';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Auth error:', error);
        errorDiv.textContent = 'An error occurred. Please try again.';
        errorDiv.style.display = 'block';
    }
}

async function logout() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
        // Clear synced username from localStorage
        localStorage.removeItem('mtg_user_name');
        // Refresh the page to update UI state
        window.location.reload();
    } catch (error) {
        console.error('Logout error:', error);
    }
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    const modal = document.getElementById('authModal');
    if (event.target === modal) {
        closeAuthModal();
    }
});
</script>
"""


def inject_navigation(html_content: str, current_section: str = "") -> str:
    """Inject navigation into HTML content."""
    if not html_content or not isinstance(html_content, str):
        return html_content
    
    # Update navigation links with active state
    nav_html = NAVIGATION_HTML
    nav_html = nav_html.replace('href="/" class="nav-link"', f'href="/" class="nav-link{" active" if current_section == "home" else ""}"')
    nav_html = nav_html.replace('href="/market" class="nav-link"', f'href="/market" class="nav-link{" active" if current_section == "market" else ""}"')
    nav_html = nav_html.replace('href="/wishlist" class="nav-link"', f'href="/wishlist" class="nav-link{" active" if current_section == "wishlist" else ""}"')
    nav_html = nav_html.replace('href="/collection" class="nav-link"', f'href="/collection" class="nav-link{" active" if current_section == "collection" else ""}"')
    nav_html = nav_html.replace('href="/games" class="nav-link"', f'href="/games" class="nav-link{" active" if current_section == "games" else ""}"')
    
    # Try to inject after <body> tag
    if "<body" in html_content:
        # Find the body tag and inject after it
        body_idx = html_content.find("<body")
        if body_idx != -1:
            # Find the closing > of body tag
            body_end = html_content.find(">", body_idx) + 1
            html_content = html_content[:body_end] + nav_html + "\n" + html_content[body_end:]
    elif "<body>" in html_content:
        html_content = html_content.replace("<body>", "<body>" + nav_html, 1)
    
    # Inject CSS in head
    if "</head>" in html_content:
        html_content = html_content.replace("</head>", NAVIGATION_CSS + "\n</head>", 1)
    elif "<head>" in html_content and "</head>" not in html_content:
        html_content = html_content.replace("<head>", "<head>" + NAVIGATION_CSS, 1)
    
    # Inject auth modal and JavaScript before </body>
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", AUTH_MODAL_HTML + AUTH_JS + "\n</body>", 1)
    
    return html_content


@app.get("/", response_class=HTMLResponse)
async def home_page():
    """Home page with links to all sections."""
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MTG Cards Manager - Home</title>
        <link href="https://fonts.googleapis.com/css2?family=MedievalSharp&family=Uncial+Antiqua&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
        {NAVIGATION_CSS}
        <style>
            :root {{
                --parchment: #f4e4bc;
                --parchment-dark: #d4c4a0;
                --ink: #1a0f00;
                --gold: #c9a227;
                --gold-light: #e8d48b;
                --blood: #8b1a1a;
                --forest: #1a472a;
                --midnight: #0f0a1a;
                --mystic: #2a1a3a;
            }}
            
            * {{
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Crimson Text', Georgia, serif;
                background: var(--midnight);
                background-image: 
                    radial-gradient(ellipse at 20% 30%, rgba(75, 0, 130, 0.15) 0%, transparent 50%),
                    radial-gradient(ellipse at 80% 70%, rgba(139, 26, 26, 0.1) 0%, transparent 50%),
                    radial-gradient(ellipse at 50% 50%, rgba(42, 26, 58, 0.8) 0%, transparent 70%),
                    repeating-linear-gradient(
                        0deg,
                        transparent,
                        transparent 2px,
                        rgba(201, 162, 39, 0.03) 2px,
                        rgba(201, 162, 39, 0.03) 4px
                    ),
                    linear-gradient(180deg, #0a0510 0%, #1a0f20 50%, #0f0a15 100%);
                background-attachment: fixed;
                min-height: 100vh;
                margin: 0;
                padding: 0;
                color: var(--parchment);
            }}
            
            .home-container {{
                max-width: 1100px;
                margin: 0 auto;
                padding: 50px 20px 80px;
            }}
            
            .home-header {{
                text-align: center;
                margin-bottom: 50px;
                position: relative;
            }}
            
            .home-header p.tagline {{
                font-size: 1.15em;
                color: var(--parchment-dark);
                margin: 0 auto;
                max-width: 600px;
                line-height: 1.6;
            }}
            
            .home-header::after {{
                content: "";
                display: block;
                width: 300px;
                height: 2px;
                background: linear-gradient(90deg, transparent, var(--gold), transparent);
                margin: 30px auto 0;
            }}
            
            .sections-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 25px;
                margin-top: 40px;
            }}
            
            @media (max-width: 768px) {{
                .sections-grid {{
                    grid-template-columns: 1fr;
                }}
                .home-header h1 {{
                    font-size: 2.2em;
                }}
            }}
            
            .section-card {{
                position: relative;
                background: linear-gradient(145deg, #1e1e2a 0%, #141420 100%);
                border: 1px solid rgba(201, 162, 39, 0.3);
                border-radius: 12px;
                padding: 0;
                text-align: center;
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                cursor: pointer;
                text-decoration: none;
                color: var(--parchment);
                display: block;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            }}
            
            .section-card::before {{
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: var(--card-accent, var(--gold));
                opacity: 0.8;
            }}
            
            .card-inner {{
                position: relative;
                z-index: 1;
                padding: 24px 20px 20px;
            }}
            
            .section-card:hover {{
                transform: translateY(-6px);
                border-color: var(--card-accent, var(--gold));
                box-shadow: 
                    0 12px 30px rgba(0, 0, 0, 0.5),
                    0 0 20px var(--card-glow, rgba(201, 162, 39, 0.2));
            }}
            
            .section-card h2 {{
                font-family: 'MedievalSharp', 'Uncial Antiqua', cursive;
                color: var(--gold);
                font-size: 1.5em;
                margin: 0 0 10px 0;
            }}
            
            .section-card p {{
                color: #a0a0a0;
                line-height: 1.5;
                margin: 0 0 16px 0;
                font-size: 0.95em;
            }}
            
            .section-icon {{
                width: 52px;
                height: 52px;
                margin: 0 auto 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 12px;
                font-size: 1.5em;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            
            /* Card accent colors */
            .section-card.card-amber {{
                --card-accent: #d4a634;
                --card-glow: rgba(212, 166, 52, 0.3);
            }}
            .section-card.card-crimson {{
                --card-accent: #c44040;
                --card-glow: rgba(196, 64, 64, 0.3);
            }}
            .section-card.card-azure {{
                --card-accent: #4080c4;
                --card-glow: rgba(64, 128, 196, 0.3);
            }}
            .section-card.card-emerald {{
                --card-accent: #40a050;
                --card-glow: rgba(64, 160, 80, 0.3);
            }}
            
            .section-link {{
                display: inline-block;
                padding: 10px 20px;
                background: transparent;
                color: var(--gold);
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 0.9em;
                transition: all 0.3s;
                border: 1px solid var(--gold);
                font-family: 'Crimson Text', serif;
            }}
            
            .section-link:hover {{
                background: var(--gold);
                color: #1a1a1a;
            }}
            
            /* Floating particles animation */
            @keyframes float {{
                0%, 100% {{ transform: translateY(0) rotate(0deg); opacity: 0; }}
                10% {{ opacity: 0.8; }}
                90% {{ opacity: 0.8; }}
                100% {{ transform: translateY(-100vh) rotate(720deg); opacity: 0; }}
            }}
            
            .particles {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                overflow: hidden;
                z-index: 0;
            }}
            
            .particle {{
                position: absolute;
                width: 4px;
                height: 4px;
                background: var(--gold);
                border-radius: 50%;
                bottom: -10px;
                animation: float linear infinite;
                box-shadow: 0 0 6px var(--gold);
            }}
        </style>
    </head>
    <body>
        <div class="particles">
            <div class="particle" style="left: 10%; animation-duration: 15s; animation-delay: 0s;"></div>
            <div class="particle" style="left: 25%; animation-duration: 20s; animation-delay: 2s;"></div>
            <div class="particle" style="left: 40%; animation-duration: 18s; animation-delay: 4s;"></div>
            <div class="particle" style="left: 55%; animation-duration: 22s; animation-delay: 1s;"></div>
            <div class="particle" style="left: 70%; animation-duration: 17s; animation-delay: 3s;"></div>
            <div class="particle" style="left: 85%; animation-duration: 19s; animation-delay: 5s;"></div>
        </div>
        {NAVIGATION_HTML.replace('href="/" class="nav-link"', 'href="/" class="nav-link active"')}
        <div class="home-container">
            <div class="home-header">
                <p class="tagline">Track your Magic: The Gathering cards, manage your wishlist, find the best deals, and play against friends — all in one place.</p>
            </div>
            
            <div class="sections-grid">
                <a href="/collection" class="section-card card-amber">
                    <div class="card-inner">
                        <div class="section-icon">📚</div>
                        <h2>Collection</h2>
                        <p>Your card binder. Track what you own, what you paid, condition, and current market value.</p>
                        <span class="section-link">Open Collection</span>
                    </div>
                </a>
                
                <a href="/games" class="section-card card-crimson">
                    <div class="card-inner">
                        <div class="section-icon">⚔️</div>
                        <h2>Duel</h2>
                        <p>Play Magic online with friends. Build decks, cast spells, and battle in real-time.</p>
                        <span class="section-link">Start Duel</span>
                    </div>
                </a>
                
                <a href="/wishlist" class="section-card card-azure">
                    <div class="card-inner">
                        <div class="section-icon">📋</div>
                        <h2>Wishlist</h2>
                        <p>Cards you want to buy. Keep notes on preferred sets, editions, and priorities.</p>
                        <span class="section-link">View Wishlist</span>
                    </div>
                </a>
                
                <a href="/market" class="section-card card-emerald">
                    <div class="card-inner">
                        <div class="section-icon">📊</div>
                        <h2>Market Scanner</h2>
                        <p>Find deals on your wishlist cards. Compares prices across Cardmarket sellers.</p>
                        <span class="section-link">Scan Prices</span>
                    </div>
                </a>
            </div>
        </div>
        {AUTH_MODAL_HTML}
        {AUTH_JS}
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# Import route handlers from each module
# We need to import the functions directly from the modules
# Ensure we're importing from the current directory, not from trash or other locations
import importlib
import sys
import os

# Add current directory to path first to ensure we import from here
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

import web_ui
import wishlist_ui
import collection_ui
import auth

# Get route handlers from each module
market_index = web_ui.index
market_collection = web_ui.collection_market_scan
api_results = web_ui.api_results
api_deals = web_ui.api_deals
api_filter_options = web_ui.api_filter_options

wishlist_index = wishlist_ui.wishlist_page
get_wishlist = wishlist_ui.get_wishlist
get_sets = wishlist_ui.get_sets
get_card_printings = wishlist_ui.get_card_printings
get_wishlist_cards = wishlist_ui.get_wishlist_cards
add_wishlist_item = wishlist_ui.add_wishlist_item
update_wishlist_item = wishlist_ui.update_wishlist_item
archive_wishlist_item = wishlist_ui.archive_wishlist_item
move_wishlist_to_collection = wishlist_ui.move_wishlist_to_collection
wishlist_autocomplete = wishlist_ui.autocomplete_card_name
wishlist_fetch_image = wishlist_ui.fetch_card_image
# Wishlist auth endpoints
wishlist_register = wishlist_ui.register
wishlist_login = wishlist_ui.login
wishlist_logout = wishlist_ui.logout
wishlist_get_current_user_info = wishlist_ui.get_current_user_info

collection_index = collection_ui.collection_page
get_collection = collection_ui.get_collection
collection_get_sets = collection_ui.get_sets
collection_get_card_printings = collection_ui.get_card_printings
get_collection_cards = collection_ui.get_collection_cards
add_collection_item = collection_ui.add_collection_item
update_collection_item = collection_ui.update_collection_item
archive_collection_item = collection_ui.archive_collection_item
collection_autocomplete = collection_ui.autocomplete_card_name
collection_fetch_image = collection_ui.fetch_card_image
get_archived_stats = collection_ui.get_archived_stats

# ==================== GLOBAL AUTH ENDPOINTS ====================
# These endpoints are accessible from any page (Home, Collection, Wishlist, etc.)

@app.post("/api/auth/register")
async def global_auth_register(request: Request):
    """Global registration endpoint."""
    return await wishlist_register(request)

@app.post("/api/auth/login")
async def global_auth_login(request: Request):
    """Global login endpoint."""
    return await wishlist_login(request)

@app.post("/api/auth/logout")
async def global_auth_logout():
    """Global logout endpoint."""
    return await wishlist_logout()

@app.get("/api/auth/me")
async def global_auth_me(request: Request):
    """Get current user info from any page."""
    return await wishlist_get_current_user_info(request)

# ==================== END GLOBAL AUTH ENDPOINTS ====================

# Market Scanner routes
@app.get("/market", response_class=HTMLResponse)
async def market_route(request: Request):
    """Market scanner page with navigation."""
    try:
        response = await market_index()
        
        # Extract HTML content from response
        if isinstance(response, HTMLResponse):
            # For HTMLResponse, body is bytes
            html = response.body.decode('utf-8') if response.body else ""
        elif hasattr(response, 'body'):
            html = response.body.decode('utf-8') if isinstance(response.body, bytes) else str(response.body)
        else:
            html = str(response)
        
        if not html or html.strip() == "":
            return HTMLResponse(content="<h1>Error: Empty response from market scanner</h1>", status_code=500)
        
        # Update API paths in HTML to use /market prefix
        # Replace all occurrences of /api/ with /market/api/ (but not if already /market/api/)
        # This handles: "/api/, '/api/, `/api/, fetch("/api/, fetch('/api/, fetch(`/api/
        # Count occurrences before replacement for debugging
        api_count_before = html.count('/api/')
        html = re.sub(r'(?<!market)/api/', '/market/api/', html)
        api_count_after = html.count('/api/')
        market_api_count = html.count('/market/api/')
        
        print(f"Market route: Replaced {api_count_before} /api/ occurrences, {market_api_count} /market/api/ now present", flush=True)
        
        # Inject JavaScript to set source_type based on URL path - MUST be in <head> to run early
        source_type_script = """
    <script>
    // Set source_type based on URL path - run immediately
    (function() {
        const path = window.location.pathname;
        const sourceType = path.includes('/collection') ? 'collection' : 'wishlist';
        
        // Set as global variable for frontend to use
        window.MARKET_SCANNER_SOURCE_TYPE = sourceType;
        
        // Intercept API calls IMMEDIATELY - must happen before any fetch calls
        if (!window._market_scanner_fetch_intercepted) {
            window._market_scanner_fetch_intercepted = true;
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                const url = args[0];
                if (typeof url === 'string' && (
                    url.includes('/market/api/deals') || url.includes('/market/api/results') ||
                    url.includes('/api/results') || url.includes('/api/deals')
                )) {
                    // Add source_type if not already present
                    if (!url.includes('source_type=') && !url.includes('sourceType=')) {
                        const separator = url.includes('?') ? '&' : '?';
                        args[0] = url + separator + 'source_type=' + sourceType;
                        console.log('📊 Intercepted API call, added source_type=' + sourceType + ' to:', url);
                    }
                }
                return originalFetch.apply(this, args);
            };
        }
        
        console.log('📊 Market Scanner: source_type set to', sourceType);
    })();
    
    // Image fetch deduplication and retry prevention
    (function() {
        const imageFetchCache = new Map(); // Track pending requests
        const failedImages = new Set(); // Track images that failed to prevent infinite retries
        
        // Override fetchMissingCardImage if it exists
        window.fetchMissingCardImage = async function(imgElement, cardName, expansion) {
            const cacheKey = `${cardName}|${expansion || ''}`;
            
            // Prevent infinite retries
            if (failedImages.has(cacheKey)) {
                return; // Already failed, don't retry
            }
            
            // Prevent duplicate simultaneous requests
            if (imageFetchCache.has(cacheKey)) {
                const cachedPromise = imageFetchCache.get(cacheKey);
                try {
                    const data = await cachedPromise;
                    if (data.success && data.image_path) {
                        imgElement.src = data.image_path;
                    }
                } catch (e) {
                    // Ignore errors from cached promise
                }
                return;
            }
            
            // Show placeholder
            const placeholderText = encodeURIComponent(cardName.substring(0,8));
            imgElement.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 140%22%3E%3Crect fill=%22%23111%22 width=%22100%22 height=%22140%22/%3E%3Ctext fill=%22%23333%22 x=%2250%22 y=%2270%22 text-anchor=%22middle%22 font-size=%2212%22%3E' + placeholderText + '%3C/text%3E%3C/svg%3E';
            
            // Create and cache the fetch promise
            const fetchPromise = (async () => {
                try {
                    const params = new URLSearchParams({ name: cardName });
                    if (expansion) params.append('set', expansion);
                    
                    const response = await fetch(`/market/api/fetch-card-image?${params}`);
                    const data = await response.json();
                    
                    if (data.success && data.image_path) {
                        imgElement.src = data.image_path;
                        return data;
                    } else {
                        failedImages.add(cacheKey); // Mark as failed
                        return data;
                    }
                } catch (error) {
                    failedImages.add(cacheKey); // Mark as failed
                    console.error('Failed to fetch card image:', cardName, error);
                    throw error;
                } finally {
                    // Remove from cache after 5 seconds
                    setTimeout(() => imageFetchCache.delete(cacheKey), 5000);
                }
            })();
            
            imageFetchCache.set(cacheKey, fetchPromise);
            await fetchPromise;
        };
    })();
    </script>
"""
        # Inject in <head> section to run early, before any other scripts
        if '<head>' in html:
            # Find the <head> tag and inject right after it
            html = html.replace('<head>', '<head>' + source_type_script)
        elif '</head>' in html:
            html = html.replace('</head>', source_type_script + '\n</head>')
        else:
            # If no head tag, prepend to body
            html = source_type_script + html
        
        return HTMLResponse(content=inject_navigation(html, "market"))
    except Exception as e:
        import traceback
        error_msg = f"<h1>Error loading market scanner</h1><pre>{traceback.format_exc()}</pre>"
        print(f"Error in market_route: {e}", flush=True)
        traceback.print_exc()
        return HTMLResponse(content=error_msg, status_code=500)

@app.get("/market/collection", response_class=HTMLResponse)
async def market_collection_route(request: Request):
    """Collection market scanner page with navigation."""
    try:
        response = await market_collection()
        
        # Extract HTML content from response
        if isinstance(response, HTMLResponse):
            html = response.body.decode('utf-8') if response.body else ""
        elif hasattr(response, 'body'):
            html = response.body.decode('utf-8') if isinstance(response.body, bytes) else str(response.body)
        else:
            html = str(response)
        
        if not html or html.strip() == "":
            return HTMLResponse(content="<h1>Error: Empty response from collection market scanner</h1>", status_code=500)
        
        # Update API paths in HTML to use /market prefix
        api_count_before = html.count('/api/')
        html = re.sub(r'(?<!market)/api/', '/market/api/', html)
        market_api_count = html.count('/market/api/')
        
        print(f"Collection market route: Replaced {api_count_before} /api/ occurrences, {market_api_count} /market/api/ now present", flush=True)
        
        # Inject JavaScript to set source_type to 'collection' - MUST be in <head> to run early
        source_type_script = """
    <script>
    // Set source_type to collection for this page - run immediately
    (function() {
        const sourceType = 'collection';
        
        // Set as global variable for frontend to use
        window.MARKET_SCANNER_SOURCE_TYPE = sourceType;
        
        // Intercept API calls IMMEDIATELY - must happen before any fetch calls
        if (!window._market_scanner_fetch_intercepted) {
            window._market_scanner_fetch_intercepted = true;
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                const url = args[0];
                if (typeof url === 'string' && (
                    url.includes('/market/api/deals') || url.includes('/market/api/results') ||
                    url.includes('/api/results') || url.includes('/api/deals')
                )) {
                    // Add source_type if not already present
                    if (!url.includes('source_type=') && !url.includes('sourceType=')) {
                        const separator = url.includes('?') ? '&' : '?';
                        args[0] = url + separator + 'source_type=' + sourceType;
                        console.log('📊 Intercepted API call, added source_type=' + sourceType + ' to:', url);
                    }
                }
                return originalFetch.apply(this, args);
            };
        }
        
        console.log('📊 Market Scanner: source_type set to', sourceType);
    })();
    
    // Image fetch deduplication and retry prevention
    (function() {
        const imageFetchCache = new Map(); // Track pending requests
        const failedImages = new Set(); // Track images that failed to prevent infinite retries
        
        // Override fetchMissingCardImage if it exists
        window.fetchMissingCardImage = async function(imgElement, cardName, expansion) {
            const cacheKey = `${cardName}|${expansion || ''}`;
            
            // Prevent infinite retries
            if (failedImages.has(cacheKey)) {
                return; // Already failed, don't retry
            }
            
            // Prevent duplicate simultaneous requests
            if (imageFetchCache.has(cacheKey)) {
                const cachedPromise = imageFetchCache.get(cacheKey);
                try {
                    const data = await cachedPromise;
                    if (data.success && data.image_path) {
                        imgElement.src = data.image_path;
                    }
                } catch (e) {
                    // Ignore errors from cached promise
                }
                return;
            }
            
            // Show placeholder
            const placeholderText = encodeURIComponent(cardName.substring(0,8));
            imgElement.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 140%22%3E%3Crect fill=%22%23111%22 width=%22100%22 height=%22140%22/%3E%3Ctext fill=%22%23333%22 x=%2250%22 y=%2270%22 text-anchor=%22middle%22 font-size=%2212%22%3E' + placeholderText + '%3C/text%3E%3C/svg%3E';
            
            // Create and cache the fetch promise
            const fetchPromise = (async () => {
                try {
                    const params = new URLSearchParams({ name: cardName });
                    if (expansion) params.append('set', expansion);
                    
                    const response = await fetch(`/market/api/fetch-card-image?${params}`);
                    const data = await response.json();
                    
                    if (data.success && data.image_path) {
                        imgElement.src = data.image_path;
                        return data;
                    } else {
                        failedImages.add(cacheKey); // Mark as failed
                        return data;
                    }
                } catch (error) {
                    failedImages.add(cacheKey); // Mark as failed
                    console.error('Failed to fetch card image:', cardName, error);
                    throw error;
                } finally {
                    // Remove from cache after 5 seconds
                    setTimeout(() => imageFetchCache.delete(cacheKey), 5000);
                }
            })();
            
            imageFetchCache.set(cacheKey, fetchPromise);
            await fetchPromise;
        };
    })();
    </script>
"""
        # Inject in <head> section to run early, before any other scripts
        if '<head>' in html:
            # Find the <head> tag and inject right after it
            html = html.replace('<head>', '<head>' + source_type_script)
        elif '</head>' in html:
            html = html.replace('</head>', source_type_script + '\n</head>')
        else:
            # If no head tag, prepend to body
            html = source_type_script + html
        
        return HTMLResponse(content=inject_navigation(html, "market"))
    except Exception as e:
        import traceback
        error_msg = f"<h1>Error loading collection market scanner</h1><pre>{traceback.format_exc()}</pre>"
        print(f"Error in market_collection_route: {e}", flush=True)
        traceback.print_exc()
        return HTMLResponse(content=error_msg, status_code=500)

@app.get("/market/api/results/{filename:path}")
async def market_api_raw_results(filename: str):
    """
    Serve raw JSON result files for viewing/downloading.
    Example: /market/api/results/wishlist_deals_20260106_193111.json
    """
    import os
    from fastapi.responses import FileResponse
    
    # Security: ensure file is in results directory
    file_path = os.path.join('results', filename)
    
    # Prevent directory traversal
    if not os.path.abspath(file_path).startswith(os.path.abspath('results')):
        return JSONResponse(content={'error': 'Invalid file path'}, status_code=400)
    
    if not os.path.exists(file_path):
        return JSONResponse(content={'error': 'File not found'}, status_code=404)
    
    # Return as JSON with proper content type
    return FileResponse(file_path, media_type='application/json', filename=filename)

@app.get("/market/api/results")
async def market_api_results(source_type: str = None):
    return await api_results(source_type=source_type)

@app.get("/market/api/deals")
async def market_api_deals(
    request: Request,
    file: str = None,
    source_type: str = None,
    category: str = None,
    min_discount: float = None,
    sort: str = 'discount',
    order: str = 'desc',
    sets: str = None,
    countries: str = None,
    price_min: float = None,
    price_max: float = None,
    min_available: int = None
):
    # Get current user for per-user wishlist filtering
    user_id = auth.get_current_user(request)
    
    return await api_deals(
        file=file,
        source_type=source_type,
        category=category,
        min_discount=min_discount,
        sort=sort,
        order=order,
        sets=sets,
        countries=countries,
        price_min=price_min,
        price_max=price_max,
        min_available=min_available,
        user_id=user_id
    )

@app.get("/market/api/filter-options")
async def market_api_filter_options(file: str = None):
    return await api_filter_options(file=file)

@app.get("/market/api/fetch-card-image")
async def market_api_fetch_card_image(name: str, set: str = None):
    """Fetch card image from Scryfall if it doesn't exist locally. Supports set-specific fetching."""
    # Import the fetch function from wishlist_ui (they share the same implementation)
    from wishlist_ui import fetch_card_image_from_scryfall, get_image_filename, IMAGE_DIR_SETS, IMAGE_DIR
    from fastapi.responses import Response
    import os
    
    # Create cache key for request deduplication
    cache_key = f"{name}|{set or ''}"
    
    try:
        # Generate filename with set if provided
        filename = get_image_filename(name, set)
        target_dir = IMAGE_DIR_SETS if set else IMAGE_DIR
        filepath = os.path.join(target_dir, filename)
        
        # Check if image already exists
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            # Don't log cached responses - they're too frequent
            # URL-encode the filename to handle semicolons and other special characters
            from urllib.parse import quote
            encoded_filename = quote(filename, safe='')
            response = JSONResponse({
                "success": True,
                "image_path": f"/card_images_sets/{encoded_filename}" if set else f"/card_images/{encoded_filename}",
                "message": "Image already exists"
            })
            # Add caching headers - cache for 1 day
            response.headers["Cache-Control"] = "public, max-age=86400"
            response.headers["ETag"] = f'"{cache_key}-{os.path.getmtime(filepath)}"'
            return response
        
        # Only log when actually fetching from Scryfall (not cached)
        print(f"🖼️  Fetching card image from Scryfall: {name} ({set or 'no set'})", flush=True)
        
        # Fetch from Scryfall (with set if provided)
        image_path = fetch_card_image_from_scryfall(name, set)
        
        if image_path:
            print(f"✅ Successfully fetched image for {name}", flush=True)
            # URL-encode the filename in the path to handle semicolons and other special characters
            from urllib.parse import quote
            # Extract filename from path and encode it
            path_parts = image_path.split('/')
            if path_parts:
                filename = path_parts[-1]
                encoded_filename = quote(filename, safe='')
                path_parts[-1] = encoded_filename
                image_path = '/'.join(path_parts)
            
            response = JSONResponse({
                "success": True,
                "image_path": image_path,
                "message": "Image fetched successfully"
            })
            # Add caching headers - cache for 1 day
            response.headers["Cache-Control"] = "public, max-age=86400"
            response.headers["ETag"] = f'"{cache_key}"'
            return response
        else:
            print(f"❌ Could not fetch image for {name} from Scryfall", flush=True)
            response = JSONResponse({
                "success": False,
                "message": "Could not fetch image from Scryfall"
            }, status_code=404)
            # Cache 404s for 1 hour to prevent repeated failed requests
            response.headers["Cache-Control"] = "public, max-age=3600"
            return response
    except Exception as e:
        import traceback
        print(f"❌ Error in market_api_fetch_card_image for {name}: {e}", flush=True)
        traceback.print_exc()
        response = JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)
        # Don't cache errors
        response.headers["Cache-Control"] = "no-cache"
        return response

# Market auth endpoints (shared with wishlist/collection auth system)
@app.post("/market/api/auth/register")
async def market_api_register(request: Request):
    return await wishlist_register(request)

@app.post("/market/api/auth/login")
async def market_api_login(request: Request):
    return await wishlist_login(request)

@app.post("/market/api/auth/logout")
async def market_api_logout():
    return await wishlist_logout()

@app.get("/market/api/auth/me")
async def market_api_auth_me(request: Request):
    return await wishlist_get_current_user_info(request)

# Wishlist routes
@app.get("/wishlist", response_class=HTMLResponse)
async def wishlist_route(request: Request):
    """Wishlist page with navigation."""
    try:
        response = await wishlist_index()
        
        # Extract HTML content from response
        if isinstance(response, HTMLResponse):
            html = response.body.decode('utf-8') if response.body else ""
        elif hasattr(response, 'body'):
            html = response.body.decode('utf-8') if isinstance(response.body, bytes) else str(response.body)
        else:
            html = str(response)
        
        if not html or html.strip() == "":
            return HTMLResponse(content="<h1>Error: Empty response from wishlist</h1>", status_code=500)
        
        # Update API paths in HTML to use /wishlist prefix
        # Replace all occurrences of /api/ with /wishlist/api/ (but not if already /wishlist/api/)
        html = re.sub(r'(?<!wishlist)/api/', '/wishlist/api/', html)
        
        return HTMLResponse(content=inject_navigation(html, "wishlist"))
    except Exception as e:
        import traceback
        error_msg = f"<h1>Error loading wishlist</h1><pre>{traceback.format_exc()}</pre>"
        print(f"Error in wishlist_route: {e}", flush=True)
        traceback.print_exc()
        return HTMLResponse(content=error_msg, status_code=500)

@app.get("/wishlist/api/wishlist")
async def wishlist_api_wishlist(request: Request):
    return await get_wishlist(request)

@app.get("/wishlist/api/sets")
async def wishlist_api_sets():
    return await get_sets()

@app.get("/wishlist/api/card-printings")
async def wishlist_api_card_printings(name: str):
    return await get_card_printings(name=name)

@app.get("/wishlist/api/wishlist-cards")
async def wishlist_api_wishlist_cards(request: Request):
    return await get_wishlist_cards(request)

@app.post("/wishlist/api/wishlist")
async def wishlist_api_add(request: Request):
    return await add_wishlist_item(request)

@app.put("/wishlist/api/wishlist/{index}")
async def wishlist_api_update(index: int, request: Request):
    return await update_wishlist_item(index, request)

@app.delete("/wishlist/api/wishlist/{index}")
async def wishlist_api_delete(index: int, request: Request):
    return await archive_wishlist_item(index, request)

@app.post("/wishlist/api/wishlist/{index}/move-to-collection")
async def wishlist_api_move_to_collection(index: int, request: Request):
    return await move_wishlist_to_collection(index, request)

@app.get("/wishlist/api/autocomplete-card")
async def wishlist_api_autocomplete(q: str = ""):
    return await wishlist_autocomplete(q=q)

@app.get("/wishlist/api/fetch-card-image")
async def wishlist_api_fetch_image(name: str, set: str = None):
    return await wishlist_fetch_image(name=name, set=set)

# Wishlist auth endpoints
@app.post("/wishlist/api/auth/register")
async def wishlist_api_register(request: Request):
    return await wishlist_register(request)

@app.post("/wishlist/api/auth/login")
async def wishlist_api_login(request: Request):
    return await wishlist_login(request)

@app.post("/wishlist/api/auth/logout")
async def wishlist_api_logout():
    return await wishlist_logout()

@app.get("/wishlist/api/auth/me")
async def wishlist_api_auth_me(request: Request):
    return await wishlist_get_current_user_info(request)

# Collection routes
@app.get("/collection", response_class=HTMLResponse)
async def collection_route(request: Request):
    """Collection page with navigation."""
    try:
        response = await collection_index()
        
        # Extract HTML content from response
        if isinstance(response, HTMLResponse):
            html = response.body.decode('utf-8') if response.body else ""
        elif hasattr(response, 'body'):
            html = response.body.decode('utf-8') if isinstance(response.body, bytes) else str(response.body)
        else:
            html = str(response)
        
        if not html or html.strip() == "":
            return HTMLResponse(content="<h1>Error: Empty response from collection</h1>", status_code=500)
        
        # Update API paths in HTML to use /collection prefix
        # Replace all occurrences of /api/ with /collection/api/ (but not if already /collection/api/)
        html = re.sub(r'(?<!collection)/api/', '/collection/api/', html)
        
        return HTMLResponse(content=inject_navigation(html, "collection"))
    except Exception as e:
        import traceback
        error_msg = f"<h1>Error loading collection</h1><pre>{traceback.format_exc()}</pre>"
        print(f"Error in collection_route: {e}", flush=True)
        traceback.print_exc()
        return HTMLResponse(content=error_msg, status_code=500)

# Auth endpoints
@app.post("/collection/api/auth/register")
async def collection_api_register(request: Request):
    return await collection_ui.register(request)

@app.post("/collection/api/auth/login")
async def collection_api_login(request: Request):
    return await collection_ui.login(request)

@app.post("/collection/api/auth/logout")
async def collection_api_logout():
    return await collection_ui.logout()

@app.get("/collection/api/auth/me")
async def collection_api_me(request: Request):
    return await collection_ui.get_current_user_info(request)

@app.get("/collection/api/collection")
async def collection_api_collection(request: Request):
    return await get_collection(request)

@app.get("/collection/api/sets")
async def collection_api_sets():
    return await collection_get_sets()

@app.get("/collection/api/card-printings")
async def collection_api_card_printings(name: str):
    return await collection_get_card_printings(name=name)

@app.get("/collection/api/collection-cards")
async def collection_api_collection_cards(request: Request):
    return await get_collection_cards(request)

@app.post("/collection/api/collection")
async def collection_api_add(request: Request, background_tasks: BackgroundTasks):
    return await add_collection_item(request, background_tasks)

@app.put("/collection/api/collection/{index}")
async def collection_api_update(index: int, request: Request):
    return await update_collection_item(index, request)

@app.delete("/collection/api/collection/{index}")
async def collection_api_delete(index: int, request: Request):
    return await archive_collection_item(index, request)

@app.post("/collection/api/collection/reorder")
async def collection_api_reorder(request: Request):
    return await collection_ui.reorder_collection(request)

@app.get("/collection/api/autocomplete-card")
async def collection_api_autocomplete(q: str = ""):
    return await collection_autocomplete(q=q)

@app.get("/collection/api/fetch-card-image")
async def collection_api_fetch_image(name: str, set: str = None):
    return await collection_fetch_image(name=name, set=set)

@app.get("/collection/api/archived-stats")
async def collection_api_archived_stats(request: Request):
    return await get_archived_stats(request)

# Games routes
@app.get("/games")
async def games_route(request: Request):
    """Games lobby page - redirects to full screen game frontend."""
    game_frontend_url = os.getenv("GAME_FRONTEND_URL", "http://localhost:5173")
    
    # Check if user is logged in and pass their username to the game frontend
    try:
        user_info = await wishlist_get_current_user_info(request)
        data = user_info.body.decode('utf-8') if hasattr(user_info, 'body') else '{}'
        import json
        user_data = json.loads(data)
        if user_data.get('authenticated') and user_data.get('username'):
            from urllib.parse import urlencode
            game_frontend_url = f"{game_frontend_url}?{urlencode({'user': user_data['username']})}"
    except Exception:
        pass  # If auth check fails, just redirect without username
    
    # Redirect directly to the game frontend for full screen experience
    return RedirectResponse(url=game_frontend_url)


def run_wishlist_analysis(wishlist_file: str = "wishlist.json", delay: float = 10.0, source: str = "json"):
    """
    Run wishlist deals analysis.
    
    Args:
        wishlist_file: Path to wishlist JSON file (used when source="json")
        delay: Delay between cards when scraping
        source: Where to load wishlists from:
            - "json": Load from wishlist_file only (original behavior)
            - "db": Load union of all users' wishlists from database
            - "all": Load both JSON + all database wishlists combined
    """
    print("\n" + "=" * 60)
    print("🔍 Running Wishlist Deals Analysis")
    print("=" * 60)
    print(f"📋 Source: {source}")
    if source == "json":
        print(f"📄 Wishlist file: {wishlist_file}")
    elif source == "db":
        print(f"🗄️  Loading from database (all users)")
    else:  # "all"
        print(f"📄 JSON file: {wishlist_file}")
        print(f"🗄️  + Database (all users)")
    
    # Add simple_version to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simple_version'))
    
    try:
        from wishlist_deals import check_wishlist_deals, save_results
        
        deals = check_wishlist_deals(
            wishlist_file=wishlist_file,
            delay_between_cards=delay,
            use_historical=True,
            source=source
        )
        
        if deals:
            output_file = save_results(deals, None, wishlist_file, source=source)  # Auto-generate filename
            print(f"\n✅ Analysis complete! Results saved to: {output_file}")
            return output_file
        else:
            print("\n⚠️  No deals found")
            return None
    except Exception as e:
        print(f"\n❌ Error running wishlist analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run the unified web application."""
    parser = argparse.ArgumentParser(
        description="MTG Cards Unified Web Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_app.py                         # Start server without scanning (default)
  python main_app.py --scan                  # Run market scan, then start server
  python main_app.py --scan --delay 15       # Run scan with custom delay
  python main_app.py --scan --source db      # Scan all users' wishlists from database
  python main_app.py --scan --source all     # Scan JSON + all database wishlists
  python main_app.py --port 6000             # Start server on custom port
        """
    )
    parser.add_argument(
        '--port',
        type=int,
        default=DEFAULT_PORT,
        help=f'Port to run server on (default: {DEFAULT_PORT})'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--scan',
        action='store_true',
        dest='run_scan',
        default=False,
        help='Run market scan analysis before starting server (default: False)'
    )
    parser.add_argument(
        '--wishlist-file',
        type=str,
        default='wishlist.json',
        help='Path to wishlist JSON file for scanning (default: wishlist.json)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=10.0,
        help='Delay between cards when scanning (default: 10.0 seconds)'
    )
    parser.add_argument(
        '--source',
        type=str,
        choices=['json', 'db', 'all'],
        default='json',
        help='Wishlist source: json=wishlist.json only, db=all users from database, all=both (default: json)'
    )
    
    args = parser.parse_args()
    
    # Run market scan if requested
    if args.run_scan:
        print("\n" + "=" * 60)
        print("🃏 MTG Cards Unified Manager - Running Market Scan")
        print("=" * 60)
        
        # For source=json, require the wishlist file to exist
        # For source=db or all, we can scan even without a JSON file
        if args.source == "json" and not os.path.exists(args.wishlist_file):
            print(f"\n⚠️  Warning: Wishlist file '{args.wishlist_file}' not found.")
            print("   Skipping market scan. Server will start with existing results.")
        else:
            print(f"📋 Scanning market with source: {args.source}")
            if args.source in ("json", "all"):
                print(f"   JSON file: {args.wishlist_file}")
            run_wishlist_analysis(args.wishlist_file, args.delay, args.source)
            print("\n" + "=" * 60)
    
    import uvicorn
    print(f"\n🎴 MTG Cards Unified Manager")
    print(f"=" * 60)
    print(f"🌐 Server starting on http://{args.host}:{args.port}")
    print(f"\n🗂️  Collection:      http://{args.host}:{args.port}/collection")
    print(f"📋 Wishlist:        http://{args.host}:{args.port}/wishlist")
    print(f"📊 Market Scanner:  http://{args.host}:{args.port}/market")
    print(f"=" * 60)
    
    try:
        uvicorn.run(
            "main_app:app",
            host=args.host,
            port=args.port,
            log_level="info",
            reload=False
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Server stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n\n❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
