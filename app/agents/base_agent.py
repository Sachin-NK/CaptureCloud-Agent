from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import Tool
from typing import List, Dict, Any, Optional
from app.database import get_supabase_agent

class BaseAgent:
    
    def __init__(self, tools: List[Tool] = None):
        
        from app.config import get_settings
        settings = get_settings()
        self.llm = ChatOpenAI(
            model="gpt-5-nano",
            temperature=0.7,
            openai_api_key=settings.openai_api_key
        )
            
        self.tools = tools or []
        self.supabase = get_supabase_agent()
        
        if self.tools:
            self.agent_executor = self._create_agent_executor()
        else:
            self.agent_executor = None
    
    def _create_agent_executor(self) -> AgentExecutor:
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant. Use the available tools to help users."),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True
        )
    
    async def execute(self, input_text: str) -> Dict[str, Any]:
        
        if self.agent_executor:
            result = await self.agent_executor.ainvoke({"input": input_text})
            return result
        else:
            response = await self.llm.ainvoke(input_text)
            return {"output": response.content}
    
    def add_tool(self, tool: Tool):
        self.tools.append(tool)

        if self.tools:
            self.agent_executor = self._create_agent_executor()
    
    def get_database(self):
        return self.supabase