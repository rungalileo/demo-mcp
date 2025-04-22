from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import anthropic
import os
from dotenv import load_dotenv
from gong_service import GongService
from datetime import datetime
import requests
import json

# Load environment variables
load_dotenv()

app = FastAPI(title="Gong Call Analyzer MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize clients
gong_service = GongService()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class CallSummaryRequest(BaseModel):
    """Request model for call summary"""
    call_title: str
    call_date: Optional[str] = None

class BuyerAnalysis(BaseModel):
    """Response model for buyer analysis"""
    call_id: str
    title: str
    date: str
    intent: str
    explanation: str
    transcript: str

class ListCallsRequest(BaseModel):
    """Request model for listing calls"""
    date: str

class CallInfo(BaseModel):
    """Model for basic call information"""
    id: str
    title: str
    start_time: str
    duration: int
    participants: List[str]

class ListCallsResponse(BaseModel):
    """Response model for listing calls"""
    date: str
    calls: List[CallInfo]

@app.post("/calls", response_model=ListCallsResponse)
async def list_calls(request: ListCallsRequest):
    """
    List all Gong calls for a specific date
    """
    try:
        # Validate date format
        try:
            datetime.strptime(request.date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Get calls from Gong
        url = "https://us-5738.api.gong.io/v2/calls"
        from_datetime = f"{request.date}T00:00:00Z"
        to_datetime = f"{request.date}T23:59:59Z"

        params = {
            "fromDateTime": from_datetime,
            "toDateTime": to_datetime
        }
        
        response = requests.get(
            url, 
            auth=(gong_service.access_key, gong_service.client_secret), 
            params=params
        )
        
        if not response.ok:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Error fetching calls: {response.text}"
            )

        calls_data = response.json().get("calls", [])
        
        # Transform the response into our model
        calls = []
        for call in calls_data:
            calls.append(CallInfo(
                id=str(call.get("id")),
                title=call.get("title", ""),
                start_time=call.get("startTime", ""),
                duration=call.get("duration", 0),
                participants=call.get("participants", [])
            ))

        return ListCallsResponse(
            date=request.date,
            calls=calls
        )

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analysis", response_model=BuyerAnalysis)
async def get_buyer_analysis(request: CallSummaryRequest):
    """
    Get a buyer analysis of a Gong call by title
    """
    try:
        # Get transcript from Gong
        transcript_data = gong_service.get_call_transcript(
            call_title=request.call_title,
            call_date=request.call_date
        )

        # Generate buyer analysis using Claude
        prompt = f"""
            Analyze the buyer sentiment from this transcript. 
            Return the intent, and a structured explanation in JSON. 
            Intent options: Less likely to buy, Neutral, Unsure, Likely to buy, Very likely to buy
            If there is any explicit frustration, hesitation, or uncertainty in buying - choose Less likely to buy.
            Choose 'Very likely to buy' only if there is strong interest from the buyer 
            i.e. they mention they love the product.

            For the explanation, include the following sections (only if mentioned in the transcript):
            1. Background & Team Context
            2. Current State & Use Cases
            3. Gap Analysis & Pain Points
            4. Next Steps & Requirements
            5. Requirements

            Format the explanation as a single string with clear section headers.
            Please provide your response without using markdown formatting like **, ##.
            Keep each section brief and only include information explicitly mentioned in the transcript.
            The output should be JSON with 2 fields only: intent and explanation.
            STRICTLY RETURN JSON. No other text.

            Transcript: {transcript_data['transcript']}
        """

        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Get the raw response
        raw_response = message.content[0].text
        print(f"Raw Claude response: {raw_response}")  # Debug log

        try:
            # Try to parse the JSON response
            analysis_data = json.loads(raw_response)
            
            # Validate the required fields
            if 'intent' not in analysis_data or 'explanation' not in analysis_data:
                raise ValueError("Response missing required fields: intent and explanation")
            
            # Validate intent value
            valid_intents = ['Less likely to buy', 'Neutral', 'Unsure', 'Likely to buy', 'Very likely to buy']
            if analysis_data['intent'] not in valid_intents:
                raise ValueError(f"Invalid intent value: {analysis_data['intent']}")

            return BuyerAnalysis(
                call_id=transcript_data['call_id'],
                title=transcript_data['title'],
                date=transcript_data['date'],
                intent=analysis_data['intent'],
                explanation=analysis_data['explanation'],
                transcript=transcript_data['transcript']
            )
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")  # Debug log
            print(f"Raw response that failed to parse: {raw_response}")  # Debug log
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse Claude's response as JSON. Raw response: {raw_response}"
            )
        except ValueError as e:
            print(f"Validation error: {str(e)}")  # Debug log
            raise HTTPException(
                status_code=500,
                detail=f"Invalid response format: {str(e)}"
            )

    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 