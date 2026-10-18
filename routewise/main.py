"""Uvicorn entry point: uvicorn routewise.main:app --reload."""
from .api import create_app

app = create_app()
