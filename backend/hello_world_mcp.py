from mcp.server import Server, Tool

# Define a simple tool that returns a greeting
class HelloWorldTool(Tool):
    def describe(self):
        return {
            "name": "say_hello",
            "description": "Returns a greeting message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the person to greet"
                    }
                },
                "required": ["name"]
            }
        }

    def call(self, params):
        name = params.get("name", "World")
        return {"message": f"Hello, {name}!"}

# Create and run the MCP server
server = Server(tools=[HelloWorldTool()])
server.run()