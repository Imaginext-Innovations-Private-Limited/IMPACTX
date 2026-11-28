"""
Routes package for Sahaaya AI.
Exposes Flask Blueprints for APIs and Frontend Views.
"""

from routes.api_eligibility import eligibility_bp
from routes.api_rag import rag_bp
from routes.api_agent import agent_bp
from routes.api_schemes import schemes_api_bp
from routes.views import views_bp

__all__ = [
    "eligibility_bp",
    "rag_bp",
    "agent_bp",
    "schemes_api_bp",
    "views_bp",
]
