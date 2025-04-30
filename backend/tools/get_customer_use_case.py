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

class CustomerUseCaseTool:
    """Tool for getting customer use cases"""
    
    @staticmethod
    def get_customer_use_case(ctx: Context, company_name: str) -> dict:
        """Get use cases for a company"""
        try:
            company_name = extract_company_name(company_name)
            logger.info(Fore.GREEN + f"Company name extracted: {company_name}" + Style.RESET_ALL)
            analyzer = GongAnalyzer()
            
            # Check cache first
            cached_data = analyzer.redis_service.get_company_data(company_name)
            if cached_data:
                logger.info(Fore.GREEN + f"### CACHE HIT ### for Key: {company_name}" + Style.RESET_ALL)
                return {
                    "use_cases": cached_data.get("use_cases", []),
                    "total_use_cases": len(cached_data.get("use_cases", []))
                }

            logger.debug(Fore.GREEN + "Calling analyzer.get_company_calls" + Style.RESET_ALL)
            company_data = analyzer.get_company_calls(company_name)
            logger.debug(Fore.YELLOW + "### OUTPUT OF get_company_calls ###" + Style.RESET_ALL)
            logger.debug(company_data)

            # Extract use cases from company data
            use_cases = set()

            # Get use cases from champions
            champions = company_data.get("champions", [])
            logger.debug(f"### Found {len(champions)} champions")
            for champion in champions:
                if champion.get("use_case"):
                    logger.debug(f"### Adding champion use case: {champion['use_case']}")
                    use_cases.add(champion["use_case"])
            
            # Get use cases from all calls by analyzing transcripts
            full_transcript = company_data.get("full_transcript", "")
            logger.debug(f"### Full transcript length: {len(full_transcript)}")
            
            if full_transcript:
                # Analyze the full transcript for use cases
                use_case_prompt = f"""
                    Analyze this transcript and extract the customer's use cases mentioned in the transcript.
                    Focus on how the customer is using or planning to use Galileo.
                    Return a JSON array of use cases, where each use case is a string.
                    Do not include the keyword 'json' in your response, return the array directly.

                    Transcript:
                    {full_transcript}

                    Return only the JSON array of use cases, nothing else.
                """
                
                logger.debug(Fore.GREEN + "### Sending prompt to Claude for use case analysis" + Style.RESET_ALL)
                response = ask_anthropic(
                    user_content=use_case_prompt,
                    system_content="You are a smart Sales Operations Analyst that analyzes Sales calls."
                )
                
                logger.debug(Fore.YELLOW + f"### Claude response for use cases: {response}" + Style.RESET_ALL)
                
                try:
                    # Clean the response by removing 'json' prefix if present
                    cleaned_response = response.strip()
                    if cleaned_response.lower().startswith('json'):
                        cleaned_response = cleaned_response[4:].strip()
                    
                    # Parse the response as JSON
                    use_cases_list = json.loads(cleaned_response)
                    if isinstance(use_cases_list, list):
                        logger.debug(f"### Adding {len(use_cases_list)} use cases from transcript analysis")
                        use_cases.update(use_cases_list)
                    else:
                        logger.error(f"### Expected list but got: {type(use_cases_list)}")
                except json.JSONDecodeError as e:
                    logger.error(f"### Failed to parse use cases from response: {response}")
                    logger.error(f"### JSON decode error: {str(e)}")
                    # Try to extract use cases even if JSON parsing fails
                    try:
                        # Look for array-like structure in the response
                        if '[' in response and ']' in response:
                            start = response.find('[')
                            end = response.rfind(']') + 1
                            array_str = response[start:end]
                            use_cases_list = json.loads(array_str)
                            if isinstance(use_cases_list, list):
                                logger.debug(f"### Adding {len(use_cases_list)} use cases from fallback parsing")
                                use_cases.update(use_cases_list)
                    except Exception as fallback_error:
                        logger.error(f"### Fallback parsing also failed: {str(fallback_error)}")
            
            final_response = {
                "use_cases": list(use_cases),
                "total_use_cases": len(use_cases)
            }
            
            logger.debug(f"### Final use cases response: {json.dumps(final_response, indent=2)}")
            return final_response

        except Exception as e:
            log_and_raise_error(e, "get customer use case")

    @staticmethod
    def register(mcp: FastMCP) -> None:
        @mcp.tool(name="get_customer_use_case")
        def _get_customer_use_case(ctx: Context, company_name: str) -> dict:
            """
                Get the use cases mentioned by the customer for their Gen AI applications.
                This includes both current and planned use cases.
            """
            return CustomerUseCaseTool.get_customer_use_case(ctx, company_name)

# For MCP registration
def register_get_customer_use_case(mcp: FastMCP) -> None:
    """Register the tool with the MCP server"""
    CustomerUseCaseTool.register(mcp)

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
            print(f"\n{Fore.CYAN}Testing get_customer_use_case with company: {company}{Style.RESET_ALL}")
            result = CustomerUseCaseTool.get_customer_use_case(MockContext(), company)
            print(f"\n{Fore.GREEN}Results for {company}:{Style.RESET_ALL}")
            print(f"Total Use Cases: {result['total_use_cases']}")
            print("\nUse Cases:")
            for i, use_case in enumerate(result['use_cases'], 1):
                print(f"{i}. {use_case}")
            print("\n" + "="*50)
    except Exception as e:
        print(f"\n{Fore.RED}Error occurred: {str(e)}{Style.RESET_ALL}")
        raise
