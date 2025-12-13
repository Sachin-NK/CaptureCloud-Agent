from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import argparse
import os 
from datetime import datetime
import httpx

from dotenv import load_dotenv
load_dotenv()

