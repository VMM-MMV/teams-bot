import asyncio
import aiosqlite
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from contextlib import asynccontextmanager


@dataclass
class ChatMessage:
    user_id: str
    message: str
    timestamp: datetime
    message_id: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            'message_id': self.message_id,
            'user_id': self.user_id,
            'message': self.message,
            'timestamp': self.timestamp.isoformat()
        }


class AsyncChatStore:
    def __init__(self, db_path: str = "chat_messages.db"):
        self.db_path = db_path
        self._db = None
    
    async def __aenter__(self):
        await self.__connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__close()
    
    async def __connect(self):
        """Initialize database connection and create table if needed"""
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_timestamp 
            ON chat_messages(user_id, timestamp DESC)
        """)
        await self._db.commit()
    
    async def __close(self):
        """Close database connection"""
        if self._db:
            await self._db.close()
    
    @asynccontextmanager
    async def transaction(self):
        """
        Async context manager for database transactions.
        Yields control back to caller before committing.
        Only commits if no exceptions are raised.
        """
        await self._db.execute("BEGIN TRANSACTION")
        try:
            yield self
            await self._db.commit()
        except Exception as e:
            await self._db.rollback()
            raise e
    
    async def add_message(self, user_id: str, message: str) -> ChatMessage:
        """
        Add a new message and maintain only the last 5 messages per user.
        Should be called within a transaction context.
        """
        timestamp = datetime.now()
        
        # Insert new message
        cursor = await self._db.execute("""
            INSERT INTO chat_messages (user_id, message, timestamp)
            VALUES (?, ?, ?)
        """, (user_id, message, timestamp.isoformat()))
        
        message_id = cursor.lastrowid
        
        # Keep only the last 5 messages for this user
        await self._db.execute("""
            DELETE FROM chat_messages 
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM chat_messages 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 5
            )
        """, (user_id, user_id))
        
        return ChatMessage(
            message_id=message_id,
            user_id=user_id,
            message=message,
            timestamp=timestamp
        )
    
    async def get_messages(self, user_id: str) -> List[ChatMessage]:
        """Get all messages for a user in descending order of timestamp"""
        cursor = await self._db.execute("""
            SELECT id, user_id, message, timestamp
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY timestamp DESC
        """, (user_id,))
        
        rows = await cursor.fetchall()
        messages = []
        
        for row in rows:
            messages.append(ChatMessage(
                message_id=row[0],
                user_id=row[1],
                message=row[2],
                timestamp=datetime.fromisoformat(row[3])
            ))
        
        return messages
    
    async def delete_all_messages(self, user_id: str) -> int:
        """
        Delete all messages for a user. Returns number of deleted messages.
        Should be called within a transaction context.
        """
        cursor = await self._db.execute("""
            DELETE FROM chat_messages WHERE user_id = ?
        """, (user_id,))
        return cursor.rowcount
    
    async def get_message_count(self, user_id: str) -> int:
        """Get total message count for a user"""
        cursor = await self._db.execute("""
            SELECT COUNT(*) FROM chat_messages WHERE user_id = ?
        """, (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else 0


# Example usage and testing
async def main():
    """Example usage of the AsyncChatStore with manual transaction control"""
    async with AsyncChatStore("chat.db") as store:
        user_id = "user123"
        
        print("Adding messages with manual transaction control...")
        
        # Method 1: Manual transaction control
        async with store.transaction() as transaction:
            message1 = await transaction.add_message(user_id, "Hello, world!")
            message2 = await transaction.add_message(user_id, "How are you today?")
            print(f"Added 2 messages in single transaction: {message1.message}, {message2.message}")

        for i in await store.get_messages(user_id):
            print(f"  {i.message} (ID: {i.message_id}, Timestamp: {i.timestamp})")

# Performance testing with batch transactions
async def performance_test():
    """Test performance with batch transactions"""
    async with AsyncChatStore("perf_test.db") as store:
        user_id = "perf_user"
        
        print("Performance test: Adding 1000 messages in batches of 100...")
        start_time = asyncio.get_event_loop().time()
        
        # Process in batches of 100 messages per transaction
        for batch in range(10):
            async with store.transaction() as transaction:
                for i in range(100):
                    msg_num = batch * 100 + i
                    await transaction.add_message(user_id, f"Batch message {msg_num}")
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        count = await store.get_message_count(user_id)
        print(f"Added 1000 messages in {elapsed:.2f} seconds (batched)")
        print(f"Final message count: {count} (should be 5)")
        print(f"Average time per message: {elapsed/1000*1000:.2f}ms")


# Example of error handling with transactions
async def transaction_error_example():
    """Demonstrate transaction rollback on error"""
    async with AsyncChatStore("error_test.db") as store:
        user_id = "error_user"
        
        print("Testing transaction rollback on error...")
        
        # First, add a message successfully
        async with store.transaction() as transaction:
            await transaction.add_message(user_id, "Initial message")
        
        initial_count = await store.get_message_count(user_id)
        print(f"Initial message count: {initial_count}")
        
        # Now try a transaction that will fail
        try:
            async with store.transaction() as transaction:
                await transaction.add_message(user_id, "Message 1 in failed transaction")
                await transaction.add_message(user_id, "Message 2 in failed transaction")

                # Simulate an error
                raise Exception("Simulated error!")

        except Exception as e:
            print(f"Transaction rolled back due to: {e}")
        
        final_count = await store.get_message_count(user_id)
        print(f"Final message count: {final_count} (should be same as initial)")
        
        # Show that the rollback worked
        messages = await store.get_messages(user_id)
        print("Messages after rollback:")
        for msg in messages:
            print(f"  {msg.message}")

if __name__ == "__main__":
    # Run example
    # print("=== Basic Usage Example ===")
    asyncio.run(main())
    
    # print("\n=== Performance Test ===")
    # asyncio.run(performance_test())
    
    # print("\n=== Transaction Error Handling ===")
    # asyncio.run(transaction_error_example())