from dotenv import load_dotenv
from mcp_config import create_mcp

import os
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

logger.info("Creating MCP server...")

# Create a single MCP instance
mcp = create_mcp()

# Import all tools to register them
from tools.analyze_customer_call import register_analyze_customer_call
from tools.get_company_business_pain import register_get_company_business_pain
from tools.get_deals import register_get_deals
from tools.get_latest_call_date_for_customer import register_get_latest_call_date_for_customer
from tools.list_customer_calls import register_list_customer_calls
from tools.get_customer_use_case import register_get_customer_use_case
from tools.get_next_steps import register_get_next_steps
from tools.get_company_champions import register_get_company_champions
# Register all tools with the single MCP instance
register_analyze_customer_call(mcp)
register_get_deals(mcp)
register_get_latest_call_date_for_customer(mcp)
register_list_customer_calls(mcp)
register_get_customer_use_case(mcp)
register_get_next_steps(mcp)
register_get_company_champions(mcp)

if __name__ == "__main__":
    try:
        logger.debug("Starting MCP server...")
        mcp.run()
        logger.debug("MCP server started successfully")
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}", exc_info=True)
        sys.exit(1)