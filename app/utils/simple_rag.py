"""
SIMPLE RAG - Retrieval Augmented Generation

Lightweight RAG system for photography tips and knowledge base.
No complex setup - just add documents and search!

Usage:
    from app.utils.simple_rag import get_rag_system
    
    rag = get_rag_system()
    
    # Search for tips
    tips = rag.search("wedding photography tips", k=3)
    
    # Add new tips
    rag.add_tip("Use golden hour for best lighting")
"""

import os
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from langchain.embeddings import OpenAIEmbeddings
import logging

logger = logging.getLogger(__name__)


class SimpleRAG:
    """
    Simple RAG system for photography knowledge
    
    Features:
    - Easy to use (no complex setup)
    - Persistent storage (survives restarts)
    - Fast semantic search
    - Pre-loaded with photography tips
    """
    
    def __init__(self, persist_directory: str = "./rag_data"):
        """
        Initialize RAG system
        
        Parameters:
        - persist_directory: Where to store the vector database
        """
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB (lightweight vector database)
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection("photography_tips")
        except:
            self.collection = self.client.create_collection(
                name="photography_tips",
                metadata={"description": "Photography tips and knowledge base"}
            )
        
        # Initialize embeddings (for semantic search)
        try:
            self.embeddings = OpenAIEmbeddings()
            self.use_openai = True
        except:
            # Fallback to sentence transformers if OpenAI not available
            logger.warning("OpenAI not available, using sentence-transformers")
            self.use_openai = False
        
        # Load default tips if collection is empty
        if self.collection.count() == 0:
            self._load_default_tips()
    
    def _load_default_tips(self):
        """Load default photography tips"""
        default_tips = [
            # General Photography
            "Golden hour (sunrise/sunset) provides the best natural lighting for outdoor photography",
            "Use the rule of thirds to compose balanced and interesting shots",
            "Shoot in RAW format for maximum editing flexibility",
            "Keep ISO as low as possible to reduce noise in your images",
            "Use a tripod for sharp images, especially in low light",
            
            # Portrait Photography
            "For portraits, use f/1.8 to f/2.8 for beautiful background blur (bokeh)",
            "Focus on the eyes - they should always be sharp in portrait photography",
            "Use natural window light for flattering portrait lighting",
            "Shoot at eye level or slightly above for most flattering angles",
            "Use a longer focal length (85mm-135mm) for flattering portraits",
            
            # Wedding Photography
            "Capture candid moments between posed shots for authentic emotions",
            "Scout the venue beforehand to find the best photo locations",
            "Bring backup equipment - cameras, lenses, batteries, memory cards",
            "Create a shot list with the couple before the wedding day",
            "Use continuous shooting mode to capture perfect moments",
            
            # Outdoor Photography
            "Overcast days provide soft, even lighting perfect for portraits",
            "Use a polarizing filter to reduce glare and enhance colors",
            "Shoot during blue hour for dramatic twilight scenes",
            "Include foreground elements to add depth to landscape shots",
            "Use a wide aperture (f/2.8-f/4) to isolate subjects from background",
            
            # Indoor Photography
            "Bounce flash off ceiling or walls for softer, more natural light",
            "Increase ISO when shooting indoors without flash",
            "Use available window light whenever possible",
            "Bring a reflector to fill in shadows",
            "Use a fast lens (f/1.4-f/2.8) for low-light situations",
            
            # Event Photography
            "Arrive early to capture setup and details",
            "Photograph the venue from multiple angles",
            "Capture reactions and emotions, not just posed shots",
            "Use a fast shutter speed (1/250s+) to freeze action",
            "Take photos of decorations, food, and small details",
            
            # Technical Tips
            "Use back-button focus for better control over focus",
            "Shoot in manual mode for consistent exposure",
            "Use spot metering for accurate exposure in tricky lighting",
            "Enable image stabilization when shooting handheld",
            "Shoot slightly underexposed to preserve highlights",
            
            # Client Communication
            "Send a questionnaire before the shoot to understand client expectations",
            "Provide a shot list so clients know what to expect",
            "Communicate clearly about timeline and schedule",
            "Send reminders 48 hours before the shoot",
            "Follow up within 24 hours after the shoot",
            
            # Location Tips
            "Central Park: Bethesda Terrace and Bow Bridge are iconic spots",
            "Urban photography: Shoot during early morning to avoid crowds",
            "Beach photography: Shoot during golden hour to avoid harsh shadows",
            "Forest photography: Use dappled light filtering through trees",
            "City skyline: Shoot from elevated positions during blue hour"
        ]
        
        self.add_tips(default_tips)
        logger.info(f"Loaded {len(default_tips)} default photography tips")
    
    def add_tip(self, tip: str, metadata: Optional[Dict] = None):
        """
        Add a single tip to the knowledge base
        
        Parameters:
        - tip: The tip text
        - metadata: Optional metadata (category, source, etc.)
        """
        self.add_tips([tip], [metadata] if metadata else None)
    
    def add_tips(self, tips: List[str], metadatas: Optional[List[Dict]] = None):
        """
        Add multiple tips to the knowledge base
        
        Parameters:
        - tips: List of tip texts
        - metadatas: Optional list of metadata dicts
        """
        try:
            # Generate IDs
            start_id = self.collection.count()
            ids = [f"tip_{start_id + i}" for i in range(len(tips))]
            
            # Add to collection
            self.collection.add(
                documents=tips,
                ids=ids,
                metadatas=metadatas if metadatas else [{}] * len(tips)
            )
            
            logger.info(f"Added {len(tips)} tips to knowledge base")
        except Exception as e:
            logger.error(f"Failed to add tips: {str(e)}")
    
    def search(self, query: str, k: int = 3) -> List[str]:
        """
        Search for relevant tips
        
        Parameters:
        - query: Search query (e.g., "wedding photography tips")
        - k: Number of results to return
        
        Returns:
        - List of relevant tips
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k
            )
            
            if results and results['documents']:
                return results['documents'][0]
            return []
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    def search_with_scores(self, query: str, k: int = 3) -> List[Dict]:
        """
        Search with relevance scores
        
        Parameters:
        - query: Search query
        - k: Number of results
        
        Returns:
        - List of dicts with 'text' and 'score'
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k
            )
            
            if results and results['documents']:
                tips = []
                for i, doc in enumerate(results['documents'][0]):
                    tips.append({
                        'text': doc,
                        'score': results['distances'][0][i] if results.get('distances') else 0,
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') else {}
                    })
                return tips
            return []
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    def get_stats(self) -> Dict:
        """Get statistics about the knowledge base"""
        return {
            "total_tips": self.collection.count(),
            "collection_name": self.collection.name,
            "persist_directory": self.persist_directory
        }
    
    def clear(self):
        """Clear all tips (use with caution!)"""
        try:
            self.client.delete_collection("photography_tips")
            self.collection = self.client.create_collection("photography_tips")
            logger.info("Cleared all tips from knowledge base")
        except Exception as e:
            logger.error(f"Failed to clear tips: {str(e)}")


# Global RAG instance
_rag_system: Optional[SimpleRAG] = None


def get_rag_system(persist_directory: str = "./rag_data") -> SimpleRAG:
    """
    Get or create the global RAG system instance
    
    Parameters:
    - persist_directory: Where to store vector database
    
    Returns:
    - SimpleRAG instance
    """
    global _rag_system
    if _rag_system is None:
        _rag_system = SimpleRAG(persist_directory=persist_directory)
    return _rag_system


# Convenience functions
def search_tips(query: str, k: int = 3) -> List[str]:
    """Quick search for tips"""
    rag = get_rag_system()
    return rag.search(query, k=k)


def add_photography_tip(tip: str, category: Optional[str] = None):
    """Quick add a tip"""
    rag = get_rag_system()
    metadata = {"category": category} if category else None
    rag.add_tip(tip, metadata=metadata)


# Example usage
if __name__ == "__main__":
    # Initialize RAG
    rag = get_rag_system()
    
    # Get stats
    print("RAG System Stats:")
    stats = rag.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Search for tips
    print("\n1. Wedding Photography Tips:")
    tips = rag.search("wedding photography tips", k=3)
    for i, tip in enumerate(tips, 1):
        print(f"  {i}. {tip}")
    
    print("\n2. Outdoor Lighting Tips:")
    tips = rag.search("outdoor lighting", k=3)
    for i, tip in enumerate(tips, 1):
        print(f"  {i}. {tip}")
    
    print("\n3. Portrait Photography Tips:")
    tips = rag.search("portrait photography", k=3)
    for i, tip in enumerate(tips, 1):
        print(f"  {i}. {tip}")
    
    # Add custom tip
    print("\n4. Adding custom tip...")
    rag.add_tip("Always backup your photos to multiple locations", {"category": "workflow"})
    
    print("\n✅ RAG system working!")
