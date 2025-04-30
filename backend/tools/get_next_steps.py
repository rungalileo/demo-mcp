from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
import os
import json
import logging
import sys
from datetime import datetime, timedelta
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

class NextStepsTrackerTool:
    """Tool for tracking next steps from call transcripts"""
    
    @staticmethod
    def get_next_steps(ctx: Context, company_name: str) -> dict:
        """Get next steps from call transcripts for a company"""
        try:
            company_name = extract_company_name(company_name)
            logger.info(Fore.GREEN + f"Company name extracted: {company_name}" + Style.RESET_ALL)
            analyzer = GongAnalyzer()
            
            # Check cache first
            cached_data = analyzer.redis_service.get_company_data(company_name)
            if cached_data:
                logger.info(Fore.GREEN + f"### CACHE HIT ### for Key: {company_name}" + Style.RESET_ALL)
                return {
                    "next_steps": cached_data.get("next_steps", []),
                    "total_next_steps": len(cached_data.get("next_steps", [])),
                    "last_updated": cached_data.get("last_updated", "")
                }

            # Get calls for the last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # Get company data with transcripts
            company_data = analyzer.get_company_calls(company_name, start_date, end_date)
            
            # Extract next steps from all calls
            next_steps = []
            
            # Get full transcript
            full_transcript = company_data.get("full_transcript", "")
            if full_transcript:
                # Analyze the transcript for next steps
                next_steps_prompt = f"""
                    Analyze the call transcript below and extract next steps, action items, and commitments mentioned.

                    For each next step, identify:
                    1. The action item
                    2. Who is responsible (if mentioned)
                    3. The timeline (if mentioned)
                    
                    Return a JSON array of next steps, where each next step is an object with these fields:
                    - action: string (the action item)
                    - responsible: string (who is responsible, or "Not specified")
                    - timeline: string (when it should be done, or "Not specified")
                    
                    Transcript:
                    {full_transcript}
                    
                    Return only the JSON array of next steps, nothing else.
                """
                
                logger.debug(Fore.GREEN + f"### Analyzing next steps for call: {company_data.get('title', 'No title')}" + Style.RESET_ALL)
                response = ask_anthropic(
                    user_content=next_steps_prompt,
                    system_content="You are a smart Sales Operations Analyst that analyzes Sales calls."
                )
                
                try:
                    # Clean the response by removing 'json' prefix if present
                    cleaned_response = response.strip()
                    if cleaned_response.lower().startswith('json'):
                        cleaned_response = cleaned_response[4:].strip()
                    
                    # Parse the response as JSON
                    call_next_steps = json.loads(cleaned_response)
                    if isinstance(call_next_steps, list):
                        # Add call metadata to each next step
                        for step in call_next_steps:
                            step['call_date'] = company_data.get('started', 'Unknown date')
                            step['call_title'] = company_data.get('title', 'Unknown title')
                        next_steps.extend(call_next_steps)
                        logger.debug(f"### Added {len(call_next_steps)} next steps from call")
                    else:
                        logger.error(f"### Expected list but got: {type(call_next_steps)}")
                except json.JSONDecodeError as e:
                    logger.error(f"### Failed to parse next steps from response: {response}")
                    logger.error(f"### JSON decode error: {str(e)}")
                    # Try to extract next steps even if JSON parsing fails
                    try:
                        # Look for array-like structure in the response
                        if '[' in response and ']' in response:
                            start = response.find('[')
                            end = response.rfind(']') + 1
                            array_str = response[start:end]
                            call_next_steps = json.loads(array_str)
                            if isinstance(call_next_steps, list):
                                # Add call metadata to each next step
                                for step in call_next_steps:
                                    step['call_date'] = company_data.get('started', 'Unknown date')
                                    step['call_title'] = company_data.get('title', 'Unknown title')
                                next_steps.extend(call_next_steps)
                                logger.debug(f"### Added {len(call_next_steps)} next steps from fallback parsing")
                    except Exception as fallback_error:
                        logger.error(f"### Fallback parsing also failed: {str(fallback_error)}")
            
            # Sort next steps by date (most recent first)
            next_steps.sort(key=lambda x: x.get('call_date', ''), reverse=True)
            
            final_response = {
                "next_steps": next_steps,
                "total_next_steps": len(next_steps),
                "last_updated": datetime.now().isoformat()
            }
            
            logger.debug(f"### Final next steps response: {json.dumps(final_response, indent=2)}")
            return final_response

        except Exception as e:
            log_and_raise_error(e, "get next steps")

    @staticmethod
    def register(mcp: FastMCP) -> None:
        @mcp.tool(name="get_next_steps")
        def _get_next_steps(ctx: Context, company_name: str) -> dict:
            """
                Get next steps for a customer. The next steps are the action items mentioned in calls with the customer.
            """
            return NextStepsTrackerTool.get_next_steps(ctx, company_name)

# For MCP registration
def register_get_next_steps(mcp: FastMCP) -> None:
    """Register the tool with the MCP server"""
    NextStepsTrackerTool.register(mcp)

if __name__ == "__main__":
    # Create a mock context for local testing
    class MockContext:
        def __init__(self):
            self.user_id = "test_user"
            self.workspace_id = "test_workspace"
    
    # Test the function
    try:
        test_companies = [
            "Bank of America",
        ]
        
        for company in test_companies:
            print(f"\n{Fore.CYAN}Testing get_next_steps with company: {company}{Style.RESET_ALL}")
            result = NextStepsTrackerTool.get_next_steps(MockContext(), company)
            print(f"\n{Fore.GREEN}Results for {company}:{Style.RESET_ALL}")
            print(f"Total Next Steps: {result['total_next_steps']}")
            print("\nNext Steps:")
            for i, step in enumerate(result['next_steps'], 1):
                print(f"\n{i}. Action: {step['action']}")
                print(f"   Responsible: {step['responsible']}")
                print(f"   Timeline: {step['timeline']}")
            print("\n" + "="*50)
    except Exception as e:
        print(f"\n{Fore.RED}Error occurred: {str(e)}{Style.RESET_ALL}")
        raise 