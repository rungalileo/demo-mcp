from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import anthropic
import os
import logging
import sys

logger = logging.getLogger(__name__)

@dataclass
class GongContext:
    access_key: str
    client_secret: str
    anthropic_client: anthropic.Anthropic

@asynccontextmanager
async def gong_lifespan(server: FastMCP) -> AsyncIterator[GongContext]:
    """Manage Gong API lifecycle with type-safe context"""
    access_key = os.getenv("GONG_ACCESS_KEY")
    client_secret = os.getenv("GONG_CLIENT_SECRET")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not all([access_key, client_secret, anthropic_api_key]):
        logger.error("Missing required environment variables")
        raise ValueError("Missing required environment variables")
    
    try:
        logger.info("Creating Gong context...")
        yield GongContext(
            access_key=access_key,
            client_secret=client_secret,
            anthropic_client=anthropic.Anthropic(api_key=anthropic_api_key)
        )
    except Exception as e:
        logger.error(f"Error creating Gong context: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("Cleaning up Gong context...")
        pass

def create_mcp() -> FastMCP:
    """Create and return a new MCP server instance"""
    try:
        mcp = FastMCP(
            name="gong_summarizer",
            port=6274,
            host="127.0.0.1",
            lifespan=gong_lifespan
        )
        logger.info("MCP server instance created successfully")
        return mcp
    except Exception as e:
        logger.error(f"Failed to create MCP server: {str(e)}", exc_info=True)
        sys.exit(1) 