from datetime import datetime
from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP

import os
import requests
import logging
import sys

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger(__name__)

load_dotenv()

def register_list_customer_calls(mcp: FastMCP) -> None:
    @mcp.tool(name="list_customer_calls")
    def get_all_customer_calls_on_date(ctx: Context, date: str) -> dict:
        """
            Get all the calls (between a buyer or potential buyer, and Galileo) that happened on a particular date.
        """
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
