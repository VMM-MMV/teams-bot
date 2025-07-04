from pathlib import Path
import agent as agent
from db import AsyncChatStore
from utils.config import config

DB_DIR = Path(config.app.dir) / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
CONNECTION_STRING = str(DB_DIR / f"{config.db.file}.sqlite")

async def invoke_agent(user_id: str, question: str):
    DB_DIR.mkdir(parents=True, exist_ok=True)

    async with AsyncChatStore(CONNECTION_STRING) as store:
        user_messages = [x.message for x in await store.get_messages(user_id)]

        result = await agent.ainvoke(question, user_messages)

        async with store.transaction() as transaction:
            await transaction.add_message(user_id, f"User: {question}")
            await transaction.add_message(user_id, f"Agent: {result}")

    return result

async def new_session(user_id: str):
    DB_DIR.mkdir(parents=True, exist_ok=True)

    async with AsyncChatStore(CONNECTION_STRING) as store:
        return await store.delete_all_messages(user_id)
    
if __name__ == "__main__":
    print(DB_DIR)