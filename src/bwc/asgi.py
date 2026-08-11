"""ASGI entry point: `uvicorn bwc.asgi:app`.

Kept separate from app.py so importing create_app never touches the filesystem.
"""

from .app import create_app

app = create_app()
