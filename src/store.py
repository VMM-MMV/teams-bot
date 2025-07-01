from db import AsyncChatStore
from utils.config import config

shared_store = AsyncChatStore(f"db/{config.db.file}.sqlite")