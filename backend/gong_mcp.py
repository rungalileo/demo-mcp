from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
import os
import json
import anthropic
import logging
import sys

from dotenv import load_dotenv
import requests
from mcp.server.fastmcp import FastMCP, Context

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

load_dotenv()

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
    
    logger.debug(f"Environment variables loaded - Access Key: {'Present' if access_key else 'Missing'}, Client Secret: {'Present' if client_secret else 'Missing'}, Anthropic Key: {'Present' if anthropic_api_key else 'Missing'}")
    
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

logger.info("Creating MCP server...")
try:
    mcp = FastMCP(
        name="gong_summarizer",
        port=6274,
        host="127.0.0.1",
        lifespan=gong_lifespan
    )
    logger.info("MCP server instance created successfully")
except Exception as e:
    logger.error(f"Failed to create MCP server: {str(e)}", exc_info=True)
    sys.exit(1)

@mcp.tool(name="list_calls")
def list_calls(ctx: Context, date: str) -> dict:
    """List all Gong calls for a specific date"""
    logger.info(f"Listing calls for date: {date}")
    try:
        datetime.strptime(date, "%Y-%m-%d")
        
        url = "https://us-5738.api.gong.io/v2/calls"
        from_datetime = f"{date}T00:00:00Z"
        to_datetime = f"{date}T23:59:59Z"

        params = {
            "fromDateTime": from_datetime,
            "toDateTime": to_datetime
        }
        
        logger.debug(f"Making request to Gong API: {url}")
        response = requests.get(
            url, 
            auth=(ctx.request_context.lifespan_context.access_key, 
                  ctx.request_context.lifespan_context.client_secret), 
            params=params
        )
        
        if not response.ok:
            logger.error(f"Error fetching calls: {response.text}")
            raise Exception(f"Error fetching calls: {response.text}")

        calls_data = response.json().get("calls", [])
        
        calls = []
        for call in calls_data:
            calls.append({
                "id": str(call.get("id")),
                "title": call.get("title", ""),
                "start_time": call.get("startTime", ""),
                "duration": call.get("duration", 0),
                "participants": call.get("participants", [])
            })

        logger.info(f"Successfully retrieved {len(calls)} calls")
        return {
            "date": date,
            "calls": calls
        }
    except Exception as e:
        logger.error(f"Failed to list calls: {str(e)}", exc_info=True)
        raise Exception(f"Failed to list calls: {str(e)}")

@mcp.tool(name="analyze_call")
def analyze_call(ctx: Context, call_title: str, call_date: str = None) -> dict:
    """Analyze a Gong call transcript for buyer sentiment"""
    logger.info(f"Analyzing call: {call_title} on date: {call_date}")
    try:
        if not call_date:
            call_date = datetime.now().strftime("%Y-%m-%d")

        url = "https://us-5738.api.gong.io/v2/calls"
        from_datetime = f"{call_date}T00:00:00Z"
        to_datetime = f"{call_date}T23:59:59Z"

        params = {
            "fromDateTime": from_datetime,
            "toDateTime": to_datetime
        }
        
        logger.debug(f"Making request to Gong API: {url}")
        response = requests.get(
            url, 
            auth=(ctx.request_context.lifespan_context.access_key, 
                  ctx.request_context.lifespan_context.client_secret), 
            params=params
        )
        
        if not response.ok:
            logger.error(f"Error fetching calls: {response.status_code}, {response.text}")
            raise Exception(f"Error fetching calls: {response.status_code}, {response.text}")

        calls = response.json().get("calls", [])
        call_id = None
        
        for call in calls:
            if call_title.lower() in call.get("title", "").lower():
                call_id = str(call["id"])
                break

        if not call_id:
            logger.error(f"No call found with title '{call_title}' on {call_date}")
            raise Exception(f"No call found with title '{call_title}' on {call_date}")

        transcript_url = 'https://us-5738.api.gong.io/v2/calls/transcript'
        headers = {'Content-Type': 'application/json'}
        payload = {
            "filter": {
                "fromDateTime": from_datetime,
                "toDateTime": to_datetime,
                "callIds": [call_id]
            }
        }

        logger.debug(f"Making request to Gong API for transcript: {transcript_url}")
        response = requests.post(
            transcript_url, 
            auth=(ctx.request_context.lifespan_context.access_key, 
                  ctx.request_context.lifespan_context.client_secret), 
            headers=headers, 
            json=payload
        )
        
        if not response.ok:
            logger.error(f"Error fetching transcript: {response.status_code}, {response.text}")
            raise Exception(f"Error fetching transcript: {response.status_code}, {response.text}")

        transcript_data = response.json()
        full_transcript = ""

        if "callTranscripts" in transcript_data:
            for transcript in transcript_data["callTranscripts"]:
                for part in transcript.get("transcript", []):
                    if "sentences" in part:
                        for sentence in part["sentences"]:
                            full_transcript += sentence.get("text", "") + " "

        prompt = f"""
            Analyze the buyer sentiment from this transcript. 
            Return the intent, and a 1-2 line explanation in JSON.
            Intent options: 
            Less likely to buy, 
            Neutral, 
            Unsure, 
            Likely to buy, 
            Very likely to buy
            
            If there is any explicit frustration, hesitation, or uncertainty in buying - choose Less likely to buy.
            Choose 'Very likely to buy' only if there is strong interest from the buyer 
            i.e. they mention they love the product.

            Strictly return raw JSON with 2 fields: buyer_intent and explanation, no other surrounding text.

            In the explanation text, include why the buyer is feeling that way.

            Format the explanation as a single string.
            Please provide your response without using markdown formatting like **, ##.
            Keep each section brief and only include information explicitly mentioned in the transcript.

            -- STARTTRANSCRIPT --
            {full_transcript.strip()}
            -- END TRANSCRIPT --
        """

        logger.debug("Generating analysis using Claude")
        message = ctx.request_context.lifespan_context.anthropic_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        try:
            # Log the raw response for debugging
            raw_response = message.content[0].text.strip()
            logger.debug(f"Raw Claude response: {raw_response}")
            
            # Remove any markdown code block markers
            raw_response = raw_response.replace("```json", "").replace("```", "").strip()
            logger.debug(f"Cleaned response: {raw_response}")
            
            analysis_data = json.loads(raw_response)

            if not isinstance(analysis_data, dict):
                raise ValueError("Response is not a valid JSON object")

            # Handle both 'intent' and 'buyer_intent' field names
            intent = analysis_data.get('buyer_intent')
            explanation = analysis_data.get('explanation')

            if not intent or not explanation:
                logger.error(f"Response missing required fields. Got: {analysis_data}")
                raise ValueError("Response missing required fields: intent and explanation")

            valid_intents = ['Less likely to buy', 'Neutral', 'Unsure', 'Likely to buy', 'Very likely to buy']

            if intent not in valid_intents:
                logger.error(f"Invalid intent value: {intent}")
                raise ValueError(f"Invalid intent value: {intent}")

            logger.info("Successfully analyzed call")
            return {
                "call_id": call_id,
                "title": call_title,
                "date": call_date,
                "intent": intent,
                "explanation": explanation
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response: {raw_response}")
            raise ValueError(f"Failed to parse JSON response: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to analyze call: {str(e)}", exc_info=True)
        raise Exception(f"Failed to analyze call: {str(e)}")

if __name__ == "__main__":
    try:
        logger.info("Starting Gong Call Analyzer MCP server...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Server configuration - Host: 127.0.0.1, Port: 8000")
        mcp.run()
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}", exc_info=True)
        sys.exit(1)