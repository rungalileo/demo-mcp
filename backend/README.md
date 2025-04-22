# Gong Summarizer MCP Server

This is a Model Control Protocol (MCP) server that integrates with Gong's API to fetch call transcripts and uses Anthropic's Claude to generate summaries.

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the backend directory with the following variables:
```
ANTHROPIC_API_KEY=your_anthropic_api_key
GONG_ACCESS_KEY=your_gong_access_key
GONG_CLIENT_SECRET=your_gong_client_secret
```

## Running the Server

Start the server with:
```bash
python app.py
```

The server will run on `http://localhost:8000`

## API Endpoints

- `POST /summary`: Get a summary of a Gong call by title
  - Request body:
    ```json
    {
        "call_title": "Your Call Title",
        "call_date": "2024-03-20"  // Optional, defaults to today
    }
    ```
  - Response:
    ```json
    {
        "call_id": "123",
        "title": "Your Call Title",
        "date": "2024-03-20",
        "summary": "Generated summary of the call...",
        "transcript": "Full transcript of the call..."
    }
    ```
- `GET /health`: Health check endpoint

## Development Status

The server now supports:
- Gong API integration for fetching call transcripts
- Claude API integration for generating summaries
- Basic error handling and validation 