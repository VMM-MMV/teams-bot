import os
from agent.utils.context_manager import get_procedures_metadata, load_procedures
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema.output_parser import StrOutputParser
from langchain.prompts import PromptTemplate
from agent.utils.io_manager import get_env
from pathlib import Path

os.environ["GOOGLE_API_KEY"] = get_env("GOOGLE_API_KEY")

gemini_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite-preview-06-17",
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

with open(Path("agent/prompt.txt"), "r") as f:
    template = f.read()

prompt = PromptTemplate(
    input_variables=["original_query", "context"],
    template=template
)

chain = prompt | gemini_model | StrOutputParser()

context = load_procedures("/home/serveruser/mcp-sse/procedures")

def invoke_agent(query: str) -> str:
    """Invoke the agent with a given query and return the response."""

    # if not context:
    #     return "No procedures found"

    response = chain.invoke({
        "original_query": query,
        "context": context
    })

    metadata = get_procedures_metadata()
    for name, url in metadata.items():
        response = response.replace(name.strip(), f"[{name}]({url})")

    return response