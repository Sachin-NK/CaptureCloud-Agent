"""
TEST AGENT - Your First Step to Understanding AI Agents

This is the simplest possible agent - perfect for beginners to understand the basics!
It does two things:
1. Tests if we can talk to OpenAI's GPT models
2. Tests if we can connect to our database

Think of this as a "Hello World" for AI agents. If this works, your setup is correct!

Key Learning Points:
- How to create an AI model connection
- How to send messages to AI and get responses
- How to connect to a database
- Basic error handling with try/catch
- Async programming (functions that can wait for responses)
"""

# Import the libraries we need
from langchain_openai import ChatOpenAI  # OpenAI's GPT models
from app.config import get_settings  # App configuration
from app.database import get_supabase_agent  # Database connection

class TestAgent:
    """
    Simple Test Agent - Perfect for Beginners!
    
    This agent has only two jobs:
    1. Test if we can talk to OpenAI (the AI provider)
    2. Test if we can connect to our database
    
    It's like a "health check" for your AI system.
    """
    
    def __init__(self):
        """
        Set up the test agent
        
        What happens here:
        1. Get app settings (API keys, database URLs)
        2. Create connection to OpenAI's GPT-4
        3. Create connection to our database
        """
        # Get configuration settings (API keys, etc.)
        settings = get_settings()
        
        # Create AI model connection
        # GPT-4 is OpenAI's most advanced model
        # Temperature 0.7 = balanced creativity
        self.llm = ChatOpenAI(
            model="gpt-4",  # Use GPT-4 (the smart one!)
            temperature=0.7,  # Medium creativity level
            openai_api_key=settings.openai_api_key  # Your OpenAI API key
        )
        
        # Create database connection with admin privileges
        self.db = get_supabase_agent()
    
    async def test_ai(self, message: str) -> str:
        """
        Test AI Connection - Send a message to GPT and get response
        
        This is the most basic AI interaction:
        1. Send a message to GPT-4
        2. Wait for response (that's why it's async)
        3. Return the AI's answer
        
        Example usage:
        response = await test_agent.test_ai("Hello, how are you?")
        print(response)  # AI will respond with something like "I'm doing well, thank you!"
        """
        # Send message to AI and wait for response
        # The message format is: [{"role": "user", "content": "your message"}]
        response = await self.llm.ainvoke([{"role": "user", "content": message}])
        
        # Return just the text content of the AI's response
        return response.content
    
    async def test_database(self) -> dict:
        """
        Test Database Connection - Try to query the database
        
        This checks if we can connect to our Supabase database:
        1. Try to count users in the users table
        2. If it works, return success
        3. If it fails, return error details
        
        Returns a dictionary with either:
        - {"status": "success", "data": [...]}
        - {"status": "error", "error": "error message"}
        """
        try:
            # Try to query the users table
            # select("count") gets the count of users
            # execute() actually runs the query
            result = self.db.table("users").select("count").execute()
            
            # If we get here, the database connection works!
            return {
                "status": "success", 
                "data": result.data
            }
            
        except Exception as e:
            # If something went wrong, return the error
            # This could be: wrong database URL, network issues, etc.
            return {
                "status": "error", 
                "error": str(e)
            }

# How to use this agent (example):
# 
# test_agent = TestAgent()
# 
# # Test AI
# ai_response = await test_agent.test_ai("What is 2 + 2?")
# print(f"AI says: {ai_response}")
# 
# # Test Database  
# db_result = await test_agent.test_database()
# if db_result["status"] == "success":
#     print("Database connection works!")
# else:
#     print(f"Database error: {db_result['error']}")