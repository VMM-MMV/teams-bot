import os
import asyncio
from pathlib import Path
from typing import List
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.utils.context_manager import load_procedures
from dotenv import load_dotenv
load_dotenv()

class AgentChain:
    def __init__(self): 
        self.groq_model = ChatGroq(
            model_name="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0.1
        )
        print(os.environ["GROQ_API_KEY"], os.environ["GOOGLE_API_KEY"])
        
        self.google_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite-preview-06-17",
            temperature=0.7,
            max_retries=2,
        )

        with open(Path("agent/prompts/base_prompt.txt"), "r") as f:
            template = f.read()

        self.context_prompt = ChatPromptTemplate.from_template(
            template=template
        )
        
        with open(Path("agent/prompts/knowledge_base_prompt.txt"), "r") as f:
            template = f.read()

        self.answer_prompt = ChatPromptTemplate.from_template(
            template=template
        )

        self.context = load_procedures("/procedures")
        
        self.chain = self._create_chain()

    def debug(self, obj: str):
        """Debugging utility to print messages"""
        print(f"DEBUG: {obj}")
        return obj
    
    def _create_chain(self):
        """Create the async chain"""
        
        # Step 1: Enhance the question with context using Groq
        context_enhancement_chain = (
            self.context_prompt
            | self.groq_model
            | StrOutputParser()
            | RunnableLambda(lambda x: self.debug(x))
        )
        
        # Step 2: Get final answer using Google Generative AI
        answer_chain = (
            {"query": RunnablePassthrough(), "context": RunnableLambda(lambda _: self.context)}
            | self.answer_prompt
            | self.google_model
            | StrOutputParser()
        )
        
        # Combine both steps
        full_chain = context_enhancement_chain | answer_chain
        
        return full_chain
    
    async def ainvoke(self, user_question: str, conversation_history: List[BaseMessage] = None) -> str:
        """Async invoke the chain"""
        if conversation_history is None:
            conversation_history = []
        
        input_data = {
            "user_question": user_question,
            "conversation_history": conversation_history
        }
        
        result = await self.chain.ainvoke(input_data)
        return result
    
    async def astream(self, user_question: str, conversation_history: List[BaseMessage] = None):
        """Async stream the chain results"""
        if conversation_history is None:
            conversation_history = []
        
        input_data = {
            "user_question": user_question,
            "conversation_history": conversation_history
        }
        
        async for chunk in self.chain.astream(input_data):
            yield chunk

# Example usage
async def main():
    # Initialize the chain
    chain = AgentChain()
    
    # Current user question
    user_question = "Should I bring an umbrella?"
    
    # Get the enhanced response
    # result = await chain.ainvoke(user_question, [])
    # print("Final Answer:")
    # print(result)
    
    # print("\n" + "="*50 + "\n")
    
    # # Example of streaming
    # print("Streaming response:")
    # async for chunk in chain.astream(user_question, []):
    #     print(chunk, end="", flush=True)
    # print()
        

if __name__ == "__main__":
    asyncio.run(main())