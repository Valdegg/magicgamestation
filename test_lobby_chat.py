#!/usr/bin/env python3
import asyncio
import websockets
import json
import sys
import time

async def test_lobby_chat():
    # Use the ngrok URL from the logs
    uri = "wss://3f9e6f265dd2.ngrok.app/ws/lobby"
    
    print(f"Connecting to {uri}...")
    
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        async with websockets.connect(uri, ssl=ssl_context) as websocket:
            print("✅ Connected! Waiting for initial message...")
            
            # Wait for initial chat history
            try:
                initial_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                initial_data = json.loads(initial_msg)
                print(f"\n📨 Received initial message:")
                print(f"   Type: {initial_data.get('type')}")
                if initial_data.get('type') == 'lobby_chat_history':
                    messages = initial_data.get('messages', [])
                    print(f"   Messages: {len(messages)}")
                    if len(messages) > 0:
                        print(f"   Last message: {messages[-1]}")
            except asyncio.TimeoutError:
                print("⚠️ No initial message received within 5 seconds")
            
            # Send a test chat message
            print(f"\n📤 Sending test chat message...")
            chat_action = {
                "action": "lobby_chat",
                "data": {
                    "message": "Test message from script",
                    "playerName": "TestUser"
                }
            }
            await websocket.send(json.dumps(chat_action))
            print("✅ Message sent")
            
            # Wait for responses (including ping messages)
            print("Waiting for responses (will listen for 10 seconds)...")
            responses = []
            start_time = time.time()
            try:
                while time.time() - start_time < 10:
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(msg)
                        responses.append(data)
                        print(f"\n📨 Response received:")
                        print(f"   Type: {data.get('type')}")
                        if data.get('type') == 'lobby_chat_message':
                            print(f"   Player: {data.get('playerName')}")
                            print(f"   Message: {data.get('message')}")
                        elif data.get('type') == 'ping':
                            print(f"   Ping received - sending pong")
                            await websocket.send(json.dumps({"type": "pong"}))
                    except asyncio.TimeoutError:
                        print(".", end="", flush=True)
                        continue
            except KeyboardInterrupt:
                print("\nInterrupted")
            
            print(f"\n✅ Test complete. Received {len(responses)} responses.")
            print(f"   Connection stayed alive for {time.time() - start_time:.1f} seconds")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed with status {e.status_code}")
        print(f"   Headers: {e.headers}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_lobby_chat())

