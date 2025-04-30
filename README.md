How to run this?

1. open a terminal and "cd" go to the `backend/` folder
2. create a virtualenv: python -m venv venv
3. run `pip install -r requirements.txt`. ensure success - if failures, ask an LLM.
4. Go to ~/Library/Application Support/Claude
5. Open claude_desktop_config.json

6. Add the following

```
{
  "mcpServers": {
    "sales_agent": {
      "command": "ROOT_PATH_TO_THIS PROJECT/backend/venv/bin/python3.10",
      "args": [
        "ROOT_PATH_TO_THIS_PROJECT/backend/gong_mcp.py"
      ]
    }
  },
  "globalShortcut": ""
}
```

7. Create a `.env` inside the /backend folder. Add the following:
```
GONG_CLIENT_SECRET=your_gong_client_secret
GONG_ACCESS_KEY=your_gong_access_key
ANTHROPIC_API_KEY=anthropic_api_key
REDIS_URL=redis://localhost:6379
HUBSPOT_API_KEY=hubspot_api_key
DISABLE_COST_WARNINGS=1
DISABLE_ERROR_REPORTING=1
DISABLE_TELEMETRY=1
```
8. Run `gong_mcp.py`

9. Open Claude Desktop
10. Go to Settings, Developer and ensure you see sales_agent
11. Try any query e.g. "Show me deals in the sales qualification stage"
