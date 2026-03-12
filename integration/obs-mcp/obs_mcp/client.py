#!/usr/bin/env python3

import os
import json
import asyncio
import websockets
import logging
import hashlib
import base64
from typing import Any, Dict, Optional

OBS_WS_URL = os.environ.get("OBS_WEBSOCKET_URL", "ws://localhost:4455")
OBS_WS_PASSWORD = os.environ.get("OBS_WEBSOCKET_PASSWORD", "")

logger = logging.getLogger("obs_client")

class OBSWebSocketClient:
    def __init__(self, url: str = OBS_WS_URL, password: str = OBS_WS_PASSWORD):
        self.url = url
        self.password = password
        self.ws = None
        self.message_id = 0
        self.authenticated = False
        self._lock = None  # Lazy init
    
    @property
    def lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
    
    async def connect(self):
        if self.ws:
            try:
                pong = await self.ws.ping()
                await asyncio.wait_for(pong, timeout=2.0)
                return
            except Exception:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
                self.authenticated = False
        
        try:
            logger.info(f"Connecting to OBS WebSocket at {self.url}")
            self.ws = await websockets.connect(self.url)
            await self._authenticate()
            logger.info("Successfully connected to OBS WebSocket server")
        except Exception as e:
            self.ws = None
            self.authenticated = False
            raise Exception(f"Failed to connect to OBS WebSocket server: {e}")

    async def _authenticate(self):
        hello = await self.ws.recv()
        hello_data = json.loads(hello)
        
        if hello_data["op"] != 0:
            raise Exception("Did not receive Hello message")
        
        auth_data = {"op": 1, "d": {"rpcVersion": 1, "eventSubscriptions": 0}}
        
        auth_info = hello_data.get("d", {}).get("authentication")
        if auth_info and self.password:
            challenge = auth_info.get("challenge", "")
            salt = auth_info.get("salt", "")
            secret_hash = hashlib.sha256((self.password + salt).encode()).digest()
            secret_b64 = base64.b64encode(secret_hash).decode()
            auth_hash = hashlib.sha256((secret_b64 + challenge).encode()).digest()
            auth_data["d"]["authentication"] = base64.b64encode(auth_hash).decode()
        
        await self.ws.send(json.dumps(auth_data))
        response = await self.ws.recv()
        response_data = json.loads(response)
        
        if response_data["op"] != 2:
            raise Exception("Authentication failed")
        
        self.authenticated = True

    async def send_request(self, request_type: str, request_data: Optional[Dict] = None) -> Dict:
        async with self.lock:
            if not self.ws or not self.authenticated:
                await self.connect()
            
            request_id = str(self.message_id)
            self.message_id += 1
            
            payload = {"op": 6, "d": {"requestType": request_type, "requestId": request_id}}
            if request_data:
                payload["d"]["requestData"] = request_data
            
            await self.ws.send(json.dumps(payload))
            
            timeout = 5.0
            start = asyncio.get_event_loop().time()
            while True:
                if asyncio.get_event_loop().time() - start > timeout:
                    raise Exception(f"Timeout waiting for {request_type}")
                try:
                    response = await asyncio.wait_for(self.ws.recv(), 0.5)
                    data = json.loads(response)
                    if data["op"] == 7 and data["d"]["requestId"] == request_id:
                        if not data["d"]["requestStatus"]["result"]:
                            raise Exception(data["d"]["requestStatus"].get("comment", "Error"))
                        return data["d"].get("responseData", {})
                except asyncio.TimeoutError:
                    continue

    async def close(self):
        if self.ws:
            await self.ws.close()
            self.ws = None
            self.authenticated = False
