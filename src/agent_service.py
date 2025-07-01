import os
import agent as agent
from db import AsyncChatStore
from utils.config import config

CONNECTION_STRING = f"db/{config.db.file}.sqlite"

async def invoke_agent(user_id: str, question: str):
    os.makedirs("db", exist_ok=True)

    async with AsyncChatStore(CONNECTION_STRING) as store:
        user_messages = [x.message for x in await store.get_messages(user_id)]

        result = await agent.ainvoke(question, user_messages)

        async with store.transaction() as transaction:
            await transaction.add_message(user_id, "User: " + question)
            await transaction.add_message(user_id, "Agent:" + result)

    return result

async def new_session(user_id: str):
    os.makedirs("db", exist_ok=True)

    async with AsyncChatStore(CONNECTION_STRING) as store:
        return await store.delete_all_messages(user_id)