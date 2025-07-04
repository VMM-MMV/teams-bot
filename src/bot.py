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
from datetime import datetime

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

async def save_feedback(feedback_data: dict, feedback_type: str):
    """Save feedback data to a file with a timestamp, organized by feedback type."""
    # Directory based on feedback type
    # directory = os.path.join("..", "feedback", feedback_type)
    directory = os.path.join("/home", "feedback", feedback_type)
    os.makedirs(directory, exist_ok=True)

    # Create timestamp-based filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.json"

    # Full path to the file
    filepath = os.path.join(directory, filename)

    # Write feedback data to the file
    with open(filepath, "w") as file:
        json.dump(feedback_data, file, indent=4)

    logger.info(f"Feedback saved to {filepath}")

@bot_app.activity("message")
async def on_message_activity(context: TurnContext, state: TurnState):
    """Handle incoming messages and echo them back"""
    activity_value = context.activity.value
    is_feedback_message = activity_value and isinstance(activity_value, dict) and "feedback" in activity_value
    if is_feedback_message:
        match activity_value["feedback"]:
            case "thumbs_up":
                await save_feedback(activity_value, "positive")
            case "thumbs_down":
                await save_feedback(activity_value, "negative")
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