"""Event schemas for AgentOS using Pydantic models."""

from datetime import datetime, timezone
from typing import Optional, Dict
from pydantic import BaseModel, Field
from .event_registry import register_event_schema

