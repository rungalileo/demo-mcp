import requests
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GongService:
    def __init__(self):
        self.access_key = os.getenv("GONG_ACCESS_KEY")
        self.client_secret = os.getenv("GONG_CLIENT_SECRET")
        if not self.access_key or not self.client_secret:
            raise ValueError("Gong API credentials not found in environment variables")

    def get_call_transcript(self, call_title: str, call_date: str = None) -> dict:
        """
        Get transcript for a call by title and optional date
        """
        if not call_date:
            call_date = datetime.now().strftime("%Y-%m-%d")

        # First, find the call ID
        url = "https://us-5738.api.gong.io/v2/calls"
        from_datetime = f"{call_date}T00:00:00Z"
        to_datetime = f"{call_date}T23:59:59Z"

        params = {
            "fromDateTime": from_datetime,
            "toDateTime": to_datetime
        }
        
        response = requests.get(url, auth=(self.access_key, self.client_secret), params=params)
        if not response.ok:
            raise Exception(f"Error fetching calls: {response.status_code}, {response.text}")

        calls = response.json().get("calls", [])
        call_id = None
        
        # Find call by title (case-insensitive)
        for call in calls:
            if call_title.lower() in call.get("title", "").lower():
                call_id = str(call["id"])
                break

        if not call_id:
            raise Exception(f"No call found with title '{call_title}' on {call_date}")

        # Get transcript for the call
        transcript_url = 'https://us-5738.api.gong.io/v2/calls/transcript'
        headers = {'Content-Type': 'application/json'}
        payload = {
            "filter": {
                "fromDateTime": from_datetime,
                "toDateTime": to_datetime,
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
            raise Exception(f"Error fetching transcript: {response.status_code}, {response.text}")

        transcript_data = response.json()
        full_transcript = ""

        # Process transcript
        if "callTranscripts" in transcript_data:
            for transcript in transcript_data["callTranscripts"]:
                for part in transcript.get("transcript", []):
                    if "sentences" in part:
                        for sentence in part["sentences"]:
                            full_transcript += sentence.get("text", "") + " "

        return {
            "call_id": call_id,
            "title": call_title,
            "date": call_date,
            "transcript": full_transcript.strip()
        } 