import asyncio
from aiohttp import web
import json

USERS = {}       # username -> password
CLIENTS = {}     # username -> WebSocketResponse
ADMINS = {"admin", "root"}

async def register(request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    if username in USERS:
        return web.json_response({"status": "fail", "reason": "Пользователь уже существует"})
    USERS[username] = password
    return web.json_response({"status": "ok"})

async def login(request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    if USERS.get(username) == password:
        return web.json_response({"status": "ok"})
    return web.json_response({"status": "fail", "reason": "Неверные данные"})

async def find_user(request):
    name = request.query.get("username")
    return web.json_response({"found": name in USERS})

async def is_admin(request):
    name = request.query.get("username")
    return web.json_response({"admin": name in ADMINS})

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    user = None

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
                if data.get("type") == "init":
                    user = data["from"]
                    CLIENTS[user] = ws
                else:
                    peer = data["to"]
                    if peer in CLIENTS:
                        await CLIENTS[peer].send_str(msg.data)
            except Exception as e:
                print("Ошибка:", e)

    if user:
        CLIENTS.pop(user, None)
    return ws

app = web.Application()
app.router.add_post("/register", register)
app.router.add_post("/login", login)
app.router.add_get("/find_user", find_user)
app.router.add_get("/is_admin", is_admin)
app.router.add_get("/ws", ws_handler)

web.run_app(app, port=9898)