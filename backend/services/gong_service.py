import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os
import json
from dotenv import load_dotenv
import logging
import sys
from colorama import Fore, Style

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from backend root
from utils.general_utils import extract_company_name
from services.redis_service import RedisService
from services.llm_service import ask_anthropic
from prompts import champion_prompt
import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class GongAnalyzer:
    def __init__(self):
        self.redis_service = RedisService()
        self.access_key = os.getenv("GONG_ACCESS_KEY")
        self.client_secret = os.getenv("GONG_CLIENT_SECRET")
        self.NUM_DAYS = 100

    def get_company_calls(self, company_name: str) -> Dict[str, Any]:
        """Get and analyze calls for a company"""
        # Check cache first
        cached_data = self.redis_service.get_company_data(company_name)
        if cached_data:
            return cached_data

        # Initialize data structure
        company_data = {
            "full_transcript": "",
            "likely_to_buy_count": 0,
            "champions": [],
            "business_pain_points": [],
            "use_cases": [],
            "next_steps": [],
            "last_updated": datetime.now().isoformat()
        }

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.NUM_DAYS)

        logger.debug(f"### Getting calls with keywords {company_name} between {start_date} and {end_date}")
        
        # Fetch calls from Gong API
        calls = self._fetch_calls(company_name, start_date, end_date)

        logger.debug(f"### Found {len(calls)} calls for company: {company_name}")
        
        # Initialize sets for deduplication
        pain_points_set = set()
        use_cases_set = set()
        next_steps_set = set()  # Using a set of tuples for next steps
        
        for call in calls:
            # Get transcript
            transcript = self._get_call_transcript(call["id"])
            if not transcript:
                continue

            # Analyze buyer intent
            logger.debug(f"Analyzing buyer intent for call: {call['title']}")
            intent = self._analyze_buyer_intent(transcript)
            if intent in ["Likely to buy", "Very likely to buy"]:
                company_data["likely_to_buy_count"] += 1

            # Identify champions
            champions = self._identify_champions(transcript)
            company_data["champions"].extend(champions)

            # Analyze business pain points
            pain_points = self._analyze_business_pain(transcript)
            pain_points_set.update(pain_points)

            # Analyze use cases
            use_cases = self._analyze_use_cases(transcript)
            use_cases_set.update(use_cases)

            # Analyze next steps
            next_steps = self._analyze_next_steps(transcript)
            # Add call metadata to next steps
            for step in next_steps:
                step['call_date'] = call.get('started', 'Unknown date')
                step['call_title'] = call.get('title', 'Unknown title')
                # Convert to tuple for deduplication
                next_step_tuple = (
                    step['action'],
                    step['responsible'],
                    step['timeline'],
                    step['call_date'],
                    step['call_title']
                )
                logger.debug(Fore.YELLOW + f"### Adding next step to set........" + Style.RESET_ALL)
                next_steps_set.add(next_step_tuple)

            # Append transcript
            company_data["full_transcript"] += f"\n\nCall: {call['title']}\n{transcript}"

        # Convert sets back to lists and store in company_data
        company_data["business_pain_points"] = list(pain_points_set)
        company_data["use_cases"] = list(use_cases_set)
        logger.debug(Fore.BLUE + f"### ADDING NEXT STEP SET TO COMPANY DATA ###" + Style.RESET_ALL)
        company_data["next_steps"] = [
            {
                "action": step[0],
                "responsible": step[1],
                "timeline": step[2],
            }
            for step in next_steps_set
        ]

        # Sort next steps by date (most recent first)
        company_data["next_steps"].sort(key=lambda x: x.get('call_date', ''), reverse=True)

        # Cache the results
        logger.debug(Fore.RED + f"### CACHING COMPANY DATA ###" + Style.RESET_ALL)
        self.redis_service.set_company_data(company_name, company_data)
        
        return company_data

    def _fetch_calls(self, company_name: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch calls from Gong API with pagination support"""
        url = "https://us-5738.api.gong.io/v2/calls"
        from_datetime = f"{start_date.strftime('%Y-%m-%d')}T00:00:00Z"
        to_datetime = f"{end_date.strftime('%Y-%m-%d')}T23:59:59Z"

        all_calls = []
        cursor = None
        limit = 100  # Maximum calls per page
        page_count = 0

        while True:
            page_count += 1
            logger.debug(Fore.MAGENTA + f"### Fetching page {page_count} with cursor: {cursor}" + Style.RESET_ALL)
            params = {
                "fromDateTime": from_datetime,
                "toDateTime": to_datetime,
                "limit": 100
            }
            
            if cursor:
                params["cursor"] = cursor

            logger.debug(Fore.GREEN + f"### Fetching page {page_count} with cursor: {cursor}" + Style.RESET_ALL)
            
            response = requests.get(
                url, 
                auth=(self.access_key, self.client_secret), 
                params=params
            )
            
            if not response.ok:
                logger.error(Fore.RED + f"Error fetching calls: {response.status_code}" + Style.RESET_ALL)
                break

            response_data = response.json()
            calls = response_data.get("calls", [])
            all_calls.extend(calls)
            
            logger.debug(Fore.MAGENTA + f"### Page {page_count}: {len(calls)} calls fetched. Total so far: {len(all_calls)}" + Style.RESET_ALL)
            # logger.debug(Fore.YELLOW + f"### Response data: {response_data}" + Style.RESET_ALL)
            
            # Check if there are more pages
            cursor = response_data["records"].get("cursor")
            logger.debug(Fore.CYAN + f"### Next cursor: {cursor}" + Style.RESET_ALL)
            
            if not cursor:
                logger.debug(Fore.GREEN + "### No more pages to fetch" + Style.RESET_ALL)
                break

        logger.debug(Fore.MAGENTA + f"### Total calls fetched across {page_count} pages: {len(all_calls)}" + Style.RESET_ALL)
        
        # Filter calls by company name
        company_words = company_name.lower().split()
        matching_calls = []
        
        for call in all_calls:
            call_title_words = call.get("title", "").lower().split()
            if any(word in call_title_words for word in company_words):
                logger.debug(f"### CALL MATCH: {call['title']}")
                matching_calls.append(call)
        
        return matching_calls

    def _get_call_transcript(self, call_id: str) -> Optional[str]:
        """Get transcript for a specific call"""
        transcript_url = 'https://us-5738.api.gong.io/v2/calls/transcript'
        headers = {'Content-Type': 'application/json'}
        payload = {
            "filter": {
                "callIds": [call_id]
            }
        }

        response = requests.post(
            transcript_url, 
            auth=(self.access_key, self.client_secret), 
            headers=headers, 
            json=payload
        )

        if not response.ok:
            print(f"Error fetching transcript: {response.status_code}")
            return None

        transcript_data = response.json()
        full_transcript = ""

        if "callTranscripts" in transcript_data:
            for transcript in transcript_data["callTranscripts"]:
                for part in transcript.get("transcript", []):
                    if "sentences" in part:
                        for sentence in part["sentences"]:
                            full_transcript += sentence.get("text", "") + " "

        return full_transcript.strip()

    def _analyze_buyer_intent(self, transcript: str) -> str:
        """Analyze buyer intent from transcript"""
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

            Transcript:
            {transcript}
        """

        response = ask_anthropic(
            user_content=prompt,
            system_content="You are a smart Sales Operations Analyst that analyzes Sales calls."
        )

        try:
            import json
            result = json.loads(response)
            return result.get("buyer_intent", "Neutral")
        except:
            return "Neutral"

    def _identify_champions(self, transcript: str) -> List[Dict[str, Any]]:
        """Identify champions from transcript"""
        response = ask_anthropic(
            user_content=champion_prompt.format(transcript=transcript),
            system_content="You are a smart Sales Operations Analyst that analyzes Sales calls."
        )

        logger.debug(f"### CHAMPION RESPONSE: {response}")

        try:
            import json
            result = json.loads(response)
            if result.get("champion", False):
                return [{
                    "name": result.get("name", "Unknown"),
                    "explanation": result.get("explanation", ""),
                    "business_pain": result.get("business_pain", "")
                }]
        except:
            pass

        return []

    def _analyze_business_pain(self, transcript: str) -> List[str]:
        """Analyze transcript for business pain points"""
        prompt = f"""
            Analyze this transcript and extract the challenges mentioned.
            Challenges can be business or technical.
            Return a JSON array of pain points, where each pain point is a string.
            Do not include the keyword 'json' in your response, return the array directly.
            
            Transcript:
            {transcript}

            Return only the JSON array of pain points, nothing else.
        """
        
        response = ask_anthropic(
            user_content=prompt,
            system_content="You are a smart Sales Operations Analyst that analyzes Sales calls."
        )
        
        try:
            # Clean the response by removing 'json' prefix if present
            cleaned_response = response.strip()
            if cleaned_response.lower().startswith('json'):
                cleaned_response = cleaned_response[4:].strip()
            
            # Parse the response as JSON
            pain_points = json.loads(cleaned_response)
            if isinstance(pain_points, list):
                return pain_points
        except Exception as e:
            logger.error(f"Error parsing business pain points: {str(e)}")
        
        return []

    def _analyze_use_cases(self, transcript: str) -> List[str]:
        """Analyze transcript for use cases"""
        prompt = f"""
            Analyze this transcript and extract the customer's use cases mentioned.
            Focus on how the customer is using or planning to use the product.
            Return a JSON array of use cases, where each use case is a string.
            Do not include the keyword 'json' in your response, return the array directly.
            
            Transcript:
            {transcript}

            Return only the JSON array of use cases, nothing else.
        """
        
        response = ask_anthropic(
            user_content=prompt,
            system_content="You are a smart Sales Operations Analyst that analyzes Sales calls."
        )
        
        try:
            # Clean the response by removing 'json' prefix if present
            cleaned_response = response.strip()
            if cleaned_response.lower().startswith('json'):
                cleaned_response = cleaned_response[4:].strip()
            
            # Parse the response as JSON
            use_cases = json.loads(cleaned_response)
            if isinstance(use_cases, list):
                return use_cases
        except Exception as e:
            logger.error(f"Error parsing use cases: {str(e)}")
        
        return []

    def _analyze_next_steps(self, transcript: str) -> List[Dict[str, str]]:
        """Analyze transcript for next steps"""
        prompt = f"""
            Analyze this call transcript and extract next steps, action items, and commitments mentioned.

            For each next step, identify:
            1. The action item
            2. Who is responsible (if mentioned)
            3. The timeline (if mentioned)
            
            Return a JSON array of next steps, where each next step is an object with these fields:
            - action: string (the action item)
            - responsible: string (who is responsible, or "Not specified")
            - timeline: string (when it should be done, or "Not specified")
            
            Transcript:
            {transcript}
            
            Return only the JSON array of next steps, nothing else.
        """
        
        response = ask_anthropic(
            user_content=prompt,
            system_content="You are a smart Sales Operations Analyst that analyzes Sales calls."
        )
        
        try:
            # Clean the response by removing 'json' prefix if present
            cleaned_response = response.strip()
            if cleaned_response.lower().startswith('json'):
                cleaned_response = cleaned_response[4:].strip()
            
            # Parse the response as JSON
            next_steps = json.loads(cleaned_response)
            if isinstance(next_steps, list):
                return next_steps
        except Exception as e:
            logger.error(f"Error parsing next steps: {str(e)}")
        
        return []