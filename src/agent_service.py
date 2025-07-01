import os
import agent as agent
from store import shared_store

async def invoke_agent(user_id: str, question: str):
    os.makedirs("db", exist_ok=True)

    user_messages = [x.message for x in await shared_store.get_messages(user_id)][::-1]

    result = await agent.ainvoke(question, user_messages)

    async with shared_store.transaction() as transaction:
        await transaction.add_message(user_id, "User: " + question)
        await transaction.add_message(user_id, "Agent:" + result)

    return result