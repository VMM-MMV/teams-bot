import os
import src.agent.agent as agent
from db import AsyncChatStore

async def invoke_agent(user_id: str, question: str):
    os.makedirs("db", exist_ok=True)

    async with AsyncChatStore("db/chat.db") as store:
        user_messages = [x.message for x in await store.get_messages(user_id)]

        result = await agent.ainvoke(question, user_messages)

        async with store.transaction() as transaction:
            await transaction.add_message(user_id, "User: " + question)
            await transaction.add_message(user_id, "Agent:" + result)

    return result