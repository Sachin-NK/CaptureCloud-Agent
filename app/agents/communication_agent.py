from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI 
from app.database import get_supabase, get_supabase_agent
from datetime import datetime, timedelta
import json
from typing import TypeDict, Annotated

class CommunicationState(TypeDict):
    client_id: str
    message_type: str
    context: str
    client_data: dict
    generated_message: str
    personalization_applied: bool
    message_sent: bool
    current_step: str

class ClientCommunicationAgent:
    def __init__(self, llm:ChatOpenAI):
        self.llm = llm
        self.supabase = get_supabase_agent()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(CommunicationState)

        # Define nodes
        workflow.add_node("fetch_client_data", self.fetch_client_data)
        workflow.add_node("generate_message", self.generate_message)
        workflow.add_node("personalize", self.personalize)
        workflow.add_node("send_message", self.send_message)

        # Define the order of execution
        workflow.set_entry_point("fetch_client_data")
        workflow.add_edge("fetch_client_data", "generate_message")
        workflow.add_edge("generate_message", "personalize")
        workflow.add_edge("personalize", "send_message")
        workflow.add_edge("send_message", END)

        return workflow.compile()
    
    def fetch_client_data(self, state: CommunicationState) -> CommunicationState:
        client_response = self.supabase.table("clients").select("id,email,firstName").eq("id", state["client_id"]).single().execute()
        
        booking_response = self.supabase.table("bookings").select("date,time,service").eq("client_id", state["client_id"]).gte("date", datetime.now().date()).order("date", ascending=True).limit(1).single().execute()

        state["client_data"] = {
            "profile": client_response.data[0] if client_response.data else {},
            "booking_history": booking_response.data if booking_response.data else {},
            "total_bookings": len(booking_response.data) if booking_response.data else 0
        }
        state["current_step"] = "data_fetched"
        return state
    
    async def generate_message(self, state: CommunicationState) -> CommunicationState:
        message_type = state["message_type"]
        
        # Different templates for different message types
        templates = {
            "questionnaire": self._get_questionnaire_prompt(),  # Pre-shoot questions
            "reminder": self._get_reminder_prompt(),            # Shoot day reminder
            "followup": self._get_followup_prompt(),            # Post-shoot follow-up
            "faq": self._get_faq_prompt()                       # Answer questions
        }

        prompt = templates.get(message_type, templates["faq"])
        chain = prompt | self.llm

        response = await chain.ainvoke({
            "client_data": json.dumps(state["client_data"]),
            "context": json.dumps(state["context"], {})
        })

        # Store the AI's generated message in state
        state["generated_message"] = response.content
        state["curreny_step"] = "message_generated"

        return state
    
    async def personalize(self, state: CommunicationState) -> CommunicationState:
        client_name = state["client_data"]["profile"].get("first_name", "Valued Client")
        booking_count = state["client_data"]["total_bookings"]

        # Create instructions to personalize the message
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a friendly communication specialist.Personalize this message for the client. Add warmth and context based on their history.Keep it professional but friendly."""),
            ("user","""Message: {message}
             Client Name: {name}
             Booking Count : {count}
             personalize this message.""")
        ])

        chain = prompt | self.llm
        response = await chain.ainvoke({
            "message": state["generated_message"],  
            "name": client_name, 
            "count": booking_count                  
        })

        # Update the message with the personalized version
        state["generated_message"] = response.content
        state["personalization_applied"] = True 
        state["current_step"] = "personalized"
        
        # Pass to next step
        return state

    async def send_message(self, state: CommunicationState) -> CommunicationState:

        session_id = state.get("context", {}).get("session_id",None)

        if session_id:
             self.session_manager.add_message(
                session_id=session_id,
                message_type=state["message_type"],
                content=state["generated_message"]
                metadata={"client_id": state["client_id"]
                          "timestamp": datetime.now().isoformat()
                          }
             )

        needs_async_delivery = state.get("context", {}).get("send_via_email", False)

        if needs_async_delivery:
            booking_id = state["context"].get("booking_id", None)

            message_record = {
                "client_id": state["client_id"],
                "message_type": state["message_type"],
                "message_content": state["generated_message"],
                "status": "pending",
                "sent_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
          }
            self.supabase.table("outgoing_messages").insert(message_record).execute()
        
         # Message available in session state and session manager
        state["message_sent"] = True
        state["current_step"] = "completed"

        return state

    def _crete_prompt_template(self, system_message: str) -> ChatPromptTemplate: 
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "{client_data}\nContext: {context}")
        ])

    def _get_questionnaire_prompt(self) -> ChatPromptTemplate:
        return self._create_prompt_template(
            """Create a pre-shoot questionnaire for a photography client.Ask about: vision, must-have shots, location preferences, outfit choices, special requests, and any concerns. Keep it friendly and concise."""
        )
    
    def _get_reminder_prompt(self) -> ChatPromptTemplate:
        return self._create_prompt_template(
            """Create a friendly shoot day reminder.Include: date, time, location, what to bring, photographer contact.Add helpful tips and express excitement."""
        )
    
    def _get_followup_prompt(self) -> ChatPromptTemplate:
        
        return self._create_prompt_template(
            """Create a post-shoot follow-up message.Thank them, ask for feedback, request a review if appropriate.Mention photo delivery timeline. Keep it warm and appreciative."""
        )
    
    def _get_faq_prompt(self) -> ChatPromptTemplate:
        
        return self._create_prompt_template(
            """Answer common client questions about photography bookings.Be helpful, clear, and provide specific information.Topics: pricing, rescheduling, cancellations, photo delivery, editing."""
        )
    
    async def process_communication(self, client_id: str, message_type: str, context: dict = None) -> dict:
        # Initialize the state for the workflow
        initial_state = CommunicationState(
            client_id=client_id,                   
            message_type=message_type,              
            context=context or {},              
            client_data={},                         
            generated_message="",                  
            personalization_applied=False,          
            message_sent=False,                     
            current_step="initialized"         
        )
        
        # Run the state graph workflow
        final_state = await self.graph.ainvoke(initial_state)
        
        # Return the final state with all results
        return final_state
    