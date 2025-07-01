from http import HTTPStatus
from aiohttp import web
from botbuilder.core.integration import aiohttp_error_middleware
from bot import bot_app
from utils.config import config

routes = web.RouteTableDef()

@routes.post("/api/messages")
async def on_messages(req: web.Request) -> web.Response:
    res = await bot_app.process(req)

    if res is not None:
        return res

    return web.Response(status=HTTPStatus.OK)

app = web.Application(middlewares=[aiohttp_error_middleware])
app.add_routes(routes)

from store import shared_store

async def startup():
    await shared_store.__aenter__()

async def shutdown():
    await shared_store.__aexit__(None, None, None)

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(startup())
    web.run_app(app, host="localhost", port=config.app.port)
    loop.run_until_complete(shutdown())