from datetime import datetime
from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
from utils.error_utils import (
    GongAPIError,
    ValidationError,
    AnalysisError,
    handle_api_error,
    validate_input,
    log_and_raise_error
)
from prompts import analyze_customer_call_prompt

import os
import json
import requests
import logging
import sys
from colorama import Fore, Style

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger(__name__)

load_dotenv()

def register_analyze_customer_call(mcp: FastMCP) -> None:
    @mcp.tool(name="analyze_customer_call")
    def analyze_customer_call(ctx: Context, call_title: str, call_date: str = None) -> dict:
        """
            Analyze the transcript of a call between the buyer and the seller (Galileo).
            The call_title is the title of the call and the call_date is the date of the call.
            Return the intent of the buyer (if they are likely to buy, unsure, etc) and the explanation for the intent.
        """
        logger.info(f"Analyzing call: {call_title} on date: {call_date}")
        try:
            # Validate input parameters
            validate_input(
                call_title,
                "call_title",
                lambda x: x and x.strip(),
                "Call title cannot be empty"
            )
                
            if not call_date:
                call_date = datetime.now().strftime("%Y-%m-%d")
            else:
                try:
                    datetime.strptime(call_date, "%Y-%m-%d")
                except ValueError:
                    raise ValidationError("Invalid date format. Please use YYYY-MM-DD")

            url = "https://us-5738.api.gong.io/v2/calls"
            from_datetime = f"{call_date}T00:00:00Z"
            to_datetime = f"{call_date}T23:59:59Z"

            print(Fore.GREEN + f"From Date: {from_datetime}, To Date: {to_datetime}" + Style.RESET_ALL)

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
            
            handle_api_error(response, "fetch calls")

            calls = response.json().get("calls", [])
            if not calls:
                raise ValidationError(f"No calls found for date {call_date}")

            call_id = None
            for call in calls:
                if call_title.lower() in call.get("title", "").lower():
                    call_id = str(call["id"])
                    break

            if not call_id:
                raise ValidationError(f"No call found with title '{call_title}' on {call_date}")

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
            
            handle_api_error(response, "fetch transcript")

            transcript_data = response.json()
            full_transcript = ""

            if "callTranscripts" not in transcript_data:
                raise AnalysisError("No transcript data found in API response")

            for transcript in transcript_data["callTranscripts"]:
                if not transcript.get("transcript"):
                    continue
                for part in transcript.get("transcript", []):
                    if "sentences" in part:
                        for sentence in part["sentences"]:
                            if sentence.get("text"):
                                full_transcript += sentence.get("text", "") + " "
            
            full_transcript = full_transcript.strip()
            if not full_transcript:
                raise AnalysisError("No transcript content found in the call")

            logger.debug("Generating analysis using Claude")
            message = ctx.request_context.lifespan_context.anthropic_client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": analyze_customer_call_prompt.format(full_transcript=full_transcript)
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
                    raise AnalysisError("Invalid response format from Claude")

                # Handle both 'intent' and 'buyer_intent' field names
                intent = analysis_data.get('buyer_intent')
                explanation = analysis_data.get('explanation')

                if not intent or not explanation:
                    raise AnalysisError("Response missing required fields: intent and explanation")

                valid_intents = ['Less likely to buy', 'Neutral', 'Unsure', 'Likely to buy', 'Very likely to buy']

                if intent not in valid_intents:
                    raise AnalysisError(f"Invalid intent value: {intent}")

                logger.info("Successfully analyzed call")
                return {
                    "call_id": call_id,
                    "title": call_title,
                    "date": call_date,
                    "intent": intent,
                    "explanation": explanation
                }
            except json.JSONDecodeError as e:
                raise AnalysisError("Failed to parse analysis response")
        except Exception as e:
            log_and_raise_error(e, "analyze call") 