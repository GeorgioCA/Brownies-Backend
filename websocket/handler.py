import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

router = APIRouter()

active_connections: dict[int, WebSocket] = {}


def get_user_id_from_token(token: str) -> Optional[int]:
    from core.security import decode_token
    payload = decode_token(token)
    if payload:
        return int(payload.get("sub", 0))
    return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Auth: first message must be auth token
    try:
        auth_msg = await websocket.receive_text()
        data = json.loads(auth_msg)
        token = data.get("token", "")
        user_id = get_user_id_from_token(token)
        if not user_id:
            await websocket.send_json({"type": "error", "data": {"message": "Auth failed"}})
            await websocket.close()
            return

        active_connections[user_id] = websocket

        # Ping/pong keepalive
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "typing_start":
                match_id = msg.get("data", {}).get("match_id")
                # Relay to the other user in the match
                # (Look up other user from match — simplified: just broadcast)
                await websocket.send_json({"type": "typing_ack", "data": {"match_id": match_id}})

            elif msg_type == "typing_stop":
                match_id = msg.get("data", {}).get("match_id")
                await websocket.send_json({"type": "typing_stop_ack", "data": {"match_id": match_id}})

    except WebSocketDisconnect:
        if user_id and user_id in active_connections:
            del active_connections[user_id]
    except Exception:
        if user_id and user_id in active_connections:
            del active_connections[user_id]


async def notify_user(user_id: int, event_type: str, data: dict):
    """Send a real-time event to a connected user."""
    if user_id in active_connections:
        try:
            await active_connections[user_id].send_json({"type": event_type, "data": data})
        except Exception:
            del active_connections[user_id]
