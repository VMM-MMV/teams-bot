import sys
import json
import traceback
from dataclasses import asdict

from botbuilder.core import MemoryStorage, TurnContext
from teams import Application, ApplicationOptions, TeamsAdapter
from teams.state import TurnState
from teams.feedback_loop_data import FeedbackLoopData
from agent_service import invoke_agent

from config import Config

config = Config()

# Define storage and application
storage = MemoryStorage()
bot_app = Application[TurnState](
    ApplicationOptions(
        bot_app_id=config.APP_ID,
        storage=storage,
        adapter=TeamsAdapter(config),
    )
)

@bot_app.error
async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The agent encountered an error or bug.")

@bot_app.feedback_loop()
async def feedback_loop(_context: TurnContext, _state: TurnState, feedback_loop_data: FeedbackLoopData):
    # Add custom feedback process logic here.
    print(f"Your feedback is:\n{json.dumps(asdict(feedback_loop_data), indent=4)}")

@bot_app.activity("message")
async def on_message_activity(context: TurnContext, state: TurnState):
    """Handle incoming messages and echo them back"""
    user_message = context.activity.text

    print(user_message)
    user_id = context.activity.conversation.id if context.activity.conversation else None
    if not user_id:
        print("No user ID found in the conversation.")
        await context.send_activity("No user ID found in the conversation.")
        return

    print(f"Received message from user ID: {user_id}")

    response = await invoke_agent(user_id, user_message)

    print(response)

    await context.send_activity(response)