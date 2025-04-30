from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
import os
import logging
import sys
from colorama import Fore, Style
# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from utils.error_utils import log_and_raise_error
from services.hubspot_service import HubspotService

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger(__name__)

load_dotenv()

class DealsTool:
    """Tool for getting deals from HubSpot"""
    
    @staticmethod
    def get_deals(ctx: Context, query: str = None) -> dict:
        """Get all deals from HubSpot"""
        logger.info(f"Getting deals with query: {query}")
        try:
            hubspot_service = HubspotService()
            all_deals = hubspot_service.get_all_deals()
            
            logger.info(Fore.GREEN + f"Found {len(all_deals)} deals" + Style.RESET_ALL)
            return {
                "deals": all_deals,
                "total_deals": len(all_deals)
            }

        except Exception as e:
            log_and_raise_error(e, "get deals")

    @staticmethod
    def register(mcp: FastMCP) -> None:
        @mcp.tool(name="get_deals")
        def _get_deals(ctx: Context, query: str = None) -> dict:
            """
                List all current deals in the pipeline for Galileo. This includes all active as well as closed deals.
            """
            return DealsTool.get_deals(ctx, query)

# For MCP registration
def register_get_deals(mcp: FastMCP) -> None:
    DealsTool.register(mcp)

if __name__ == "__main__":
    class MockContext:
        def __init__(self):
            self.user_id = "test_user"
            self.workspace_id = "test_workspace"
    
    # Test the function
    try:
        test_queries = [
            "list all deals",
        ]

        for query in test_queries:
            print(f"\nTesting get_deals with query: {query}")
            result = DealsTool.get_deals(MockContext(), query)
            print("\nResults:")
            print(f"Total Deals: {result['total_deals']}")
            if 'stage' in result:
                print(f"Stage: {result['stage']}")
            print(f"First deal (if any): {result['deals'][0] if result['deals'] else 'No deals found'}")
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        raise
