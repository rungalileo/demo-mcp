from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
from utils.error_utils import log_and_raise_error
from utils.general_utils import extract_company_name
from services.gong_service import GongAnalyzer

load_dotenv()

def register_get_company_champions(mcp: FastMCP) -> None:
    @mcp.tool(name="get_company_champions")
    def get_company_champions(ctx: Context, company_name: str) -> dict:
        """
            Get the champions of a company.
            The champions are the people (on the buyer side) who are most likely to buy the product or support you in the deal.
            Champions are identified by their comments, questions, and feedback, usually around how good the product is, how it will help them, etc.
        """
        try:
            company_name = extract_company_name(company_name)
            analyzer = GongAnalyzer()
            
            # Check cache first
            cached_data = analyzer.redis_service.get_company_data(company_name)
            if cached_data:
                return {
                    "champions": cached_data.get("champions", []),
                    "total_champions": len(cached_data.get("champions", [])),
                    "likely_to_buy_count": cached_data.get("likely_to_buy_count", 0)
                }
                
            company_data = analyzer.get_company_calls(company_name)

            return {
                "champions": company_data.get("champions", []),
                "total_champions": len(company_data.get("champions", [])),
                "likely_to_buy_count": company_data.get("likely_to_buy_count", 0)
            }
        except Exception as e:
            log_and_raise_error(e, "get company champions") 