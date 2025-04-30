from datetime import datetime, timedelta
from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
import os
import logging
import sys

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from utils.error_utils import log_and_raise_error
from utils.general_utils import extract_company_name
from services.gong_service import GongAnalyzer

import logging
from colorama import Fore, Style

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger(__name__)

load_dotenv()

class LatestCallDateTool:
    """Tool for getting latest call dates for a customer"""
    
    @staticmethod
    def get_latest_call_date_for_customer(ctx: Context, company_name: str) -> dict:
        try:
            analyzer = GongAnalyzer()
            
            # Extract company name from deal name
            company_name = extract_company_name(company_name)
            logger.debug(Fore.RED + f"### Extracted company name: {company_name}" + Style.RESET_ALL)
            
            # Get calls for the last 6 months
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)  # 6 months
            
            # Fetch calls from Gong API
            calls = analyzer._fetch_calls(company_name, start_date, end_date)
            logger.debug(Fore.RED + f"### Found {len(calls)} calls for company: {company_name}" + Style.RESET_ALL)
            
            # Extract and sort unique dates
            call_dates = set()
            for call in calls:
                # Get date from started field
                if 'started' in call:
                    try:
                        # Parse the ISO format date
                        call_date = datetime.fromisoformat(call['started'].replace('Z', '+00:00'))
                        call_dates.add(call_date.date())
                        logger.debug(f"### Extracted date {call_date.date()} from call: {call.get('title', 'No title')}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"### Error parsing date from call: {str(e)}")
            
            # Sort dates in descending order and take the latest 3
            sorted_dates = sorted(call_dates, reverse=True)[:3]
            
            # Convert dates to string format
            formatted_dates = [date.strftime('%Y-%m-%d') for date in sorted_dates]
            
            return {
                "company_name": company_name,
                "latest_call_dates": formatted_dates,
                "total_calls_found": len(calls)
            }

        except Exception as e:
            log_and_raise_error(e, "get latest call dates")

    @staticmethod
    def register(mcp: FastMCP) -> None:
        @mcp.tool(name="get_latest_call_date_for_customer")
        def _get_latest_call_date_for_customer(ctx: Context, company_name: str) -> dict:
            """
                Return the dates of the 3 most recent calls with a customer/company/deal.
            """
            return LatestCallDateTool.get_latest_call_date_for_customer(ctx, company_name)

def register_get_latest_call_date_for_customer(mcp: FastMCP) -> None:
    """Register the tool with the MCP server"""
    LatestCallDateTool.register(mcp)

if __name__ == "__main__":
    class MockContext:
        def __init__(self):
            self.user_id = "test_user"
            self.workspace_id = "test_workspace"
    
    # Test the function
    try:
        test_company = "PandaDoc"
        print(f"\nTesting get_latest_call_date_for_customer with company: {test_company}")
        result = LatestCallDateTool.get_latest_call_date_for_customer(MockContext(), test_company)
        print("\nResults:")
        print(f"Company Name: {result['company_name']}")
        print(f"Latest Call Dates: {result['latest_call_dates']}")
        print(f"Total Calls Found: {result['total_calls_found']}")
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        raise