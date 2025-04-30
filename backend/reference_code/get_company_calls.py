import requests
import json
from datetime import datetime, timedelta
from colorama import Fore, Style, init
import os
from dotenv import load_dotenv

load_dotenv()

call_date = "2025-03-15"
N = 10
title = "American Airlines"

GONG_ACCESS_KEY = os.getenv("GONG_ACCESS_KEY")
GONG_ACCESS_KEY_SECRET = os.getenv("GONG_ACCESS_KEY_SECRET")


def print_call_titles(calls):
    print("\nMeeting titles found:")
    for call in calls:
        print(f"- {call.get('title', 'No title')}")

def list_calls(call_date):
    url = "https://us-5738.api.gong.io/v2/calls"
    
    # Fix: URL encode the datetime string properly
    from_datetime = f"{call_date}T00:00:00Z"
    to_datetime = f"{call_date}T23:59:59Z"
    
    params = {
        "fromDateTime": from_datetime,
        "toDateTime": to_datetime
    }
    
    response = requests.get(url, auth=(GONG_ACCESS_KEY, GONG_ACCESS_KEY_SECRET), params=params)
    if response.ok:
        return response.json().get("calls", [])
    else:
        print(f"Error fetching calls: {response.status_code}, {response.text}")
        return []

def find_call_by_title(calls, call_title):
    for call in calls:
        # Split both titles into words and convert to lowercase for case-insensitive comparison
        search_words = call_title.lower().split()
        call_title_words = call.get("title", "").lower().split()
        
        # Check if any of the search words appear in the call title words
        if any(word in call_title_words for word in search_words):
            return str(call["id"])
    return None

def get_gong_call_transcripts(call_ids, from_date, to_date):
    url = 'https://us-5738.api.gong.io/v2/calls/transcript'
    headers = {'Content-Type': 'application/json'}
    payload = {
        "filter": {
            "fromDateTime": from_date,
            "toDateTime": to_date,
            "callIds": [str(cid) for cid in call_ids]
        }
    }

    response = requests.post(url, auth=(GONG_ACCESS_KEY, GONG_ACCESS_KEY_SECRET), headers=headers, json=payload)

    if response.ok:
        return response.json()
    else:
        print(Fore.RED + f"Error fetching transcripts: {response.status_code}, {response.text}" + Style.RESET_ALL)
        return None


def get_transcript_and_topics(call_id, start_time, end_time):
   full_transcript = ""
   topics = []
   call_transcripts = get_gong_call_transcripts([call_id], start_time, end_time)

   if call_transcripts and "callTranscripts" in call_transcripts:
        for transcript in call_transcripts["callTranscripts"]:
            for tx in transcript["transcript"]:
                topics.append(tx["topic"])
                if "sentences" in tx:
                    for sentence in tx["sentences"]:
                        full_transcript += sentence["text"] + " "
   
   return full_transcript, topics

def main(call_date_str, title, n=1):
    # Ensure call_date_str is a string
    if isinstance(call_date_str, datetime):
        call_date_str = call_date_str.strftime("%Y-%m-%d")
    
    # Try to find the call starting from the initial date and up to n days ahead
    call_id = None
    current_date_str = call_date_str
    current_date = datetime.strptime(call_date_str, "%Y-%m-%d")
    
    for day in range(n + 1):  # +1 to include the current day (day 0)
        if day > 0:
            # Only update the date if we're checking beyond the initial day
            current_date = datetime.strptime(call_date_str, "%Y-%m-%d") + timedelta(days=day)
            current_date_str = current_date.strftime("%Y-%m-%d")
            print(Fore.RED + f"Call with '{title}' in title not found. Checking {current_date_str} (Day {day} of {n})" + Style.RESET_ALL)
        
        calls = list_calls(current_date_str)
        
        if calls:
            
            call_id = find_call_by_title(calls, title)
            if call_id:
                # Found the call, print success message and break out of the loop
                print(Fore.GREEN + f"CALL FOUND on {current_date_str}" + Style.RESET_ALL)
                break
        else:
            print(Fore.RED + f"Call not found on {current_date_str}." + Style.RESET_ALL)
    
    if not call_id:
        print(Fore.RED + f"Could not find a call with the title within {n} days from {call_date_str}!" + Style.RESET_ALL)
        return
    
    # If we found a call, proceed to get transcript and topics
    if call_id:
        start_time = f"{current_date_str}T00:00:00Z"
        end_time = f"{current_date_str}T23:59:59Z"
        full_transcript, topics = get_transcript_and_topics(call_id, start_time, end_time)

        if full_transcript:
            print(full_transcript)
        else:
            print(Fore.RED + "No transcript found" + Style.RESET_ALL)
        if topics:
            print(set(topics))
        else:
            print(Fore.RED + "No topics found" + Style.RESET_ALL)


if __name__ == "__main__":
    main(call_date, title, n=N)