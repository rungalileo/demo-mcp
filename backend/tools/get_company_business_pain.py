from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
import os
import json
import logging
import sys
from colorama import Fore, Style

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from utils.error_utils import log_and_raise_error, AnalysisError
from utils.general_utils import extract_company_name
from services.gong_service import GongAnalyzer
from services.llm_service import ask_anthropic

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger(__name__)

load_dotenv()

class CompanyBusinessPainTool:
    """Tool for getting business pain points for a company"""
    
    @staticmethod
    def get_company_business_pain(ctx: Context, company_name: str) -> dict:
        """Get business pain points for a company"""
        try:
            company_name = extract_company_name(company_name)
            logger.info(Fore.GREEN + f"Company name extracted: {company_name}" + Style.RESET_ALL)
            analyzer = GongAnalyzer()
            
            # Check cache first
            cached_data = analyzer.redis_service.get_company_data(company_name)
            if cached_data:
                logger.info(Fore.GREEN + f"### CACHE HIT ### for Key: {company_name}" + Style.RESET_ALL)
                return {
                    "business_pain_points": cached_data.get("business_pain_points", []),
                    "total_pain_points": len(cached_data.get("business_pain_points", []))
                }

            logger.debug(Fore.GREEN + "Calling analyzer.get_company_calls" + Style.RESET_ALL)
            company_data = analyzer.get_company_calls(company_name)
            logger.debug(Fore.YELLOW + "### OUTPUT OF get_company_calls ###" + Style.RESET_ALL)
            logger.debug(company_data)
            # Extract unique business pain points from all calls
            pain_points = set()

            # Get business pain from champions
            champions = company_data.get("champions", [])

            logger.debug(f"### Found {len(champions)} champions")
            for champion in champions:
                if champion.get("business_pain"):
                    logger.debug(f"### Adding champion business pain: {champion['business_pain']}")
                    pain_points.add(champion["business_pain"])
            
            # Get business pain from all calls by analyzing transcripts
            full_transcript = company_data.get("full_transcript", "")
            logger.debug(f"### Full transcript length: {len(full_transcript)}")
            
            if full_transcript:
                # Analyze the full transcript for business pain
                from prompts import business_pain_prompt
                
                logger.debug(Fore.GREEN + "### Sending prompt to Claude for business pain analysis" + Style.RESET_ALL)

                response = ask_anthropic(
                    user_content=business_pain_prompt.format(full_transcript=full_transcript),
                    system_content="You are a smart Sales Operations Analyst that analyzes Sales calls."
                )
                
                logger.debug(Fore.YELLOW + f"### Claude response for business pain: {response}" + Style.RESET_ALL)
                
                try:
                    # Clean the response by removing 'json' prefix if present
                    cleaned_response = response.strip()
                    if cleaned_response.lower().startswith('json'):
                        cleaned_response = cleaned_response[4:].strip()
                    
                    # Parse the response as JSON
                    pain_points_list = json.loads(cleaned_response)
                    if isinstance(pain_points_list, list):
                        logger.debug(f"### Adding {len(pain_points_list)} pain points from transcript analysis")
                        pain_points.update(pain_points_list)
                    else:
                        logger.error(f"### Expected list but got: {type(pain_points_list)}")
                except json.JSONDecodeError as e:
                    logger.error(f"### Failed to parse business pain points from response: {response}")
                    logger.error(f"### JSON decode error: {str(e)}")
                    # Try to extract pain points even if JSON parsing fails
                    try:
                        # Look for array-like structure in the response
                        if '[' in response and ']' in response:
                            start = response.find('[')
                            end = response.rfind(']') + 1
                            array_str = response[start:end]
                            pain_points_list = json.loads(array_str)
                            if isinstance(pain_points_list, list):
                                logger.debug(f"### Adding {len(pain_points_list)} pain points from fallback parsing")
                                pain_points.update(pain_points_list)
                    except Exception as fallback_error:
                        logger.error(f"### Fallback parsing also failed: {str(fallback_error)}")
            
            final_response = {
                "business_pain_points": list(pain_points),
                "total_pain_points": len(pain_points)
            }
            
            logger.debug(f"### Final business pain response: {json.dumps(final_response, indent=2)}")
            return final_response

        except Exception as e:
            log_and_raise_error(e, "get company business pain")

    @staticmethod
    def register(mcp: FastMCP) -> None:
        @mcp.tool(name="get_company_business_pain")
        def _get_company_business_pain(ctx: Context, company_name: str) -> dict:
            """
                Get the challenges mentioned by the buyer or user around LLM or Gen AI Evaluation and Observability for their Gen AI applications.
            """
            return CompanyBusinessPainTool.get_company_business_pain(ctx, company_name)

# For MCP registration
def register_get_company_business_pain(mcp: FastMCP) -> None:
    """Register the tool with the MCP server"""
    CompanyBusinessPainTool.register(mcp)

if __name__ == "__main__":
    # Create a mock context for local testing
    class MockContext:
        def __init__(self):
            self.user_id = "test_user"
            self.workspace_id = "test_workspace"
    
    # Test the function
    try:
        test_companies = [
            "PandaDoc",
        ]
        
        for company in test_companies:
            print(f"\n{Fore.CYAN}Testing get_company_business_pain with company: {company}{Style.RESET_ALL}")
            result = CompanyBusinessPainTool.get_company_business_pain(MockContext(), company)
            print(f"\n{Fore.GREEN}Results for {company}:{Style.RESET_ALL}")
            print(f"Total Pain Points: {result['total_pain_points']}")
            print("\nPain Points:")
            for i, pain in enumerate(result['business_pain_points'], 1):
                print(f"{i}. {pain}")
            print("\n" + "="*50)
    except Exception as e:
        print(f"\n{Fore.RED}Error occurred: {str(e)}{Style.RESET_ALL}")
        raise 