import requests
import json
import asyncio
from datetime import datetime
# Basic Imports, update for your needs.

url = "github_raw_url"
response = requests.get(url)
if response.status_code == 200:
    exec(response.text, globals())
else:
    print(f"Failed to fetch Script: {response.status_code}", type_="ERROR")

@nightyScript(
    name="Script_Name",
    author="rico",
    description="Change_Me",
    usage="Change_Me"
)

def script_function():
    pass

script_function()
