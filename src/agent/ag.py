from typing import List
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from agent.utils.context_manager import load_procedures, get_procedure_names, get_procedures_metadata
from langchain_google_genai import ChatGoogleGenerativeAI
from pathlib import Path
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from agent.utils.io_manager import get_env
from langchain.globals import set_debug
set_debug(True)

main_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite-preview-06-17",
    temperature=0.7,
    max_retries=2,
    google_api_key=get_env("MAIN_GOOGLE_API_KEY")
)

with open(Path("agent/prompts/base_prompt.txt"), "r") as f:
    template = f.read()

base_prompt = ChatPromptTemplate.from_template(
    template=template
)

tool_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite-preview-06-17",
    temperature=0.1,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=get_env("TOOL_GOOGLE_API_KEY")
)

with open(Path("agent/prompts/knowledge_base_prompt.txt"), "r") as f:
    template = f.read()

knowledge_base_prompt = ChatPromptTemplate.from_template(
    template=template
)

context = load_procedures("procedures")
tool_chain = knowledge_base_prompt | tool_model | StrOutputParser()

@tool
async def search_knowledge_base(query: str) -> str:
    """
    Answer user queries using internal company knowledge.
    """
    return await tool_chain.ainvoke({
        "query": query,
        "context": context
    })
    
tools = [search_knowledge_base]
agent_executor = create_react_agent(main_model, tools)

def extract_final_answer(result: dict) -> str:
    for message in reversed(result["messages"]):
        if getattr(message, "type", None) == "ai" or message.__class__.__name__ == "AIMessage":
            return message.content
    raise ValueError("No AIMessage found in messages.")

main_chain = base_prompt | agent_executor | RunnableLambda(extract_final_answer) | StrOutputParser()
procedure_names = get_procedure_names()

def add_links(response: str) -> str:
    metadata = get_procedures_metadata()
    for name, url in metadata.items():
        response = response.replace(name.strip(), f"[{name}]({url})")
    return response

async def ainvoke(query: str, user_messages: List[str]):
    res = await main_chain.ainvoke({
        "query": query,
        "conversation_history": user_messages,
        "procedure_names": procedure_names
    })
    return add_links(res)

if __name__ == "__main__":
    import asyncio
    query = "What is the procedure for onboarding a new employee?"
    user_messages = ["Hello, I need help with onboarding."]
    response = asyncio.run(ainvoke(query, user_messages))
    print(response)