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

if __name__ == "__main__":
    web.run_app(app, host="localhost", port=config.app.port)