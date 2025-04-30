from setuptools import setup, find_packages

setup(
    name="demo-mcp",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "requests",
        "python-dotenv",
        "anthropic",
        "fastapi",
        "uvicorn",
        "redis",
        "mcp-server"
    ],
) 