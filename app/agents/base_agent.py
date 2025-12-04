from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from typing import List, Dict , Any
from app.config import get_setting

settings = get_setting()

class BaseAgent:
    def __init__(self, model_name:str = "gpt-4-turbo-preview", temperature: float = 0.7):

        # Create the ai model connection
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,  
            openai_api_key=settings.openai_api_key  
        )
        
        # Initialize empty list of tools
        self.tools: List[Tool] = []
        
        self.agent_executor = None

    def add_tool(self, tool:Tool):
        self.tools.append(tool)

    def create_prompt(self, system_message: str) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", system_message),  # instructions
            MessagesPlaceholder(variable_name="chat_history", optional=True),  # Previous messages
            ("human", "{input}"),  # Current user input
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
    
    def build_agent(self, system_message: str):

        prompt = self.create_prompt(system_message)
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)

        self.agent_executor = AgentExecutor(
            agent = agent,
            tools = self.tools,
            verbose = True,
            return_intermediate_steps= True
        )

    async def run(self, input_text: str, **kwargs) -> Dict[str, Any]:
        
        if not self.agent_executor: 
            raise ValueError("Agent not built properly !!!!")
        
        result = await self.agent_executor.ainvoke({
            "input": input_text,
            **kwargs
        })
        return result

