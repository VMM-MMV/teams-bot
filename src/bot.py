import re
import sys
import json
import traceback
from dataclasses import asdict
from botbuilder.core import MemoryStorage, TurnContext
from teams import Application, ApplicationOptions, TeamsAdapter
from teams.state import TurnState
from teams.feedback_loop_data import FeedbackLoopData
from agent_service import invoke_agent, new_session
from utils.logger import logger
from botbuilder.schema import Activity, Attachment, ActivityTypes

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    APP_ID = os.environ.get("BOT_ID", "")
    APP_PASSWORD = os.environ.get("BOT_PASSWORD", "")
    APP_TYPE = os.environ.get("BOT_TYPE", "")
    APP_TENANTID = os.environ.get("BOT_TENANT_ID", "")

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

async def create_feedback_card(user_message: str, response: str) -> Activity:
    return Activity(
                type=ActivityTypes.message,
                attachments=[
                    Attachment(
                        content_type="application/vnd.microsoft.card.adaptive",
                        content={
                            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                            "type": "AdaptiveCard",
                            "version": "1.4",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": "Was this answer helpful? Please provide feedback so we can improve the agent.",
                                    "wrap": True
                                }
                            ],
                            "actions": [
                                {
                                    "type": "Action.Submit",
                                    "title": "👍 Yes",
                                    "data": {
                                        "feedback": "thumbs_up",
                                        "originalQuestion": user_message,
                                        "agentResponse": response
                                    }
                                },
                                {
                                    "type": "Action.Submit",
                                    "title": "👎 No",
                                    "data": {
                                        "feedback": "thumbs_down",
                                        "originalQuestion": user_message,
                                        "agentResponse": response
                                    }
                                }
                            ]
                        }
                    )
                ]
            )   


@bot_app.activity("message")
async def on_message_activity(context: TurnContext, state: TurnState):
    """Handle incoming messages and echo them back"""
    if context.activity.value and isinstance(context.activity.value, dict) and "feedback" in context.activity.value:
        logger.info("🔁 Skipping feedback message in message activity handler.")
        return
    user_message = context.activity.text

    print(user_message)
    user_id = context.activity.conversation.id if context.activity.conversation else None
    if not user_id:
        print("No user ID found in the conversation.")
        await context.send_activity("No user ID found in the conversation.")
        return
    
    clean_uuid = re.sub(r'[^a-zA-Z0-9]', '', user_id)

    logger.info(f"Received message from user ID: {clean_uuid}")

    match user_message:
        case "/new_session":
            await new_session(clean_uuid)
            await context.send_activity("New Session started. Chat history cleared.")
        case _:
            response = await invoke_agent(clean_uuid, user_message)
            await context.send_activity(response)

            feedback_card = await create_feedback_card(user_message, response)
            await context.send_activity(feedback_card)