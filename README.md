# Remote Script Loader Documentation v1.0

**Created by:** rico

**Made with:** [manus.im](https://manus.im) and [claude.ai](https://claude.ai)

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. How It Works](#2-how-it-works)
- [3. Script Structure](#3-script-structure)
- [4. Setup and Configuration](#4-setup-and-configuration)
- [5. Security Considerations](#5-security-considerations)
- [6. Best Practices](#6-best-practices)
- [7. Troubleshooting](#7-troubleshooting)

## 1. Overview

The Remote Script Loader is a NightyScript pattern that enables dynamic loading and execution of Python code hosted on remote servers (typically GitHub). Instead of manually copying and updating script files, this loader fetches the latest version of a script from a URL and executes it directly in the NightyScript environment.

### 1.1 Key Benefits

- **Centralized Updates**: Update scripts in one place (GitHub) and all users automatically get the latest version
- **Version Control**: Leverage Git's version control for script management
- **Collaboration**: Multiple developers can contribute to scripts hosted in repositories
- **Quick Deployment**: Push updates without requiring users to manually download and replace files

### 1.2 Use Cases

- Scripts that require frequent updates or bug fixes
- Scripts shared across multiple users or communities
- Scripts with active development and feature additions
- Testing and development workflows where rapid iteration is needed

## 2. How It Works

The Remote Script Loader operates in several distinct phases:

### 2.1 The Loading Process

```
┌─────────────────────────────────────────────────────────────┐
│                    NightyScript Initialization              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Import Required Libraries                          │
│  - requests: For HTTP requests                              │
│  - json: For data parsing (if needed)                       │
│  - asyncio: For async operations                            │
│  - datetime: For timestamps                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Fetch Remote Script                                │
│  - Send GET request to GitHub raw URL                       │
│  - Receive script content as text                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Check Response Status                              │
│  - Status 200: Success → Proceed to execution               │
│  - Other Status: Failure → Log error and exit               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Execute Remote Code                                │
│  - exec(response.text, globals())                           │
│  - Code runs in global namespace                            │
│  - All functions and variables become available             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Script Registration                                │
│  - @nightyScript decorator processes metadata               │
│  - script_function() called to register commands            │
│  - Script becomes active in Nighty                          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Technical Breakdown

#### Phase 1: HTTP Request
```python
url = "github_raw_url"
response = requests.get(url)
```

The loader uses the `requests` library to perform a synchronous HTTP GET request to the specified URL. The URL should point to the **raw content** of a Python script file hosted on GitHub or another web server.

**GitHub Raw URL Format:**
```
https://raw.githubusercontent.com/username/repository/branch/path/to/script.py
```

Example:
```
https://raw.githubusercontent.com/aboveproof/Nighty-Scripts/refs/heads/main/nighty-scripts/vc_manager.py
```

#### Phase 2: Response Validation
```python
if response.status_code == 200:
    # Success - proceed with execution
else:
    print(f"Failed to fetch Script: {response.status_code}", type_="ERROR")
```

The loader checks if the HTTP request was successful by verifying the status code:
- **200**: OK - The script was retrieved successfully
- **404**: Not Found - The URL is incorrect or the file doesn't exist
- **403**: Forbidden - Access denied (private repository without authentication)
- **500-599**: Server errors

#### Phase 3: Dynamic Execution
```python
exec(response.text, globals())
```

This is the critical line that executes the fetched script content. The `exec()` function:
- Takes the script text (Python code as a string)
- Executes it in the current global namespace via `globals()`
- Makes all functions, classes, and variables from the remote script available

**Why `globals()`?**
Using `globals()` ensures that the remote script has access to all NightyScript functions and objects (`bot`, `nightyScript`, `getConfigData`, etc.) that are already loaded in the environment.

#### Phase 4: Script Registration
```python
@nightyScript(
    name="Script_Name",
    author="rico",
    description="Change_Me",
    usage="Change_Me"
)
def script_function():
    pass

script_function()
```

After the remote code executes, this local wrapper:
1. Defines the script metadata using the `@nightyScript` decorator
2. Creates an empty function (the actual logic is in the remote script)
3. Calls `script_function()` to register with Nighty

**Important**: The remote script should contain the actual command handlers and event listeners. The local loader just handles fetching and registration.

## 3. Script Structure

### 3.1 Loader Script (Local)

This is the minimal script you save locally in your NightyScript directory:

```python
import requests
import json
import asyncio
from datetime import datetime

# URL pointing to the raw GitHub content
url = "https://raw.githubusercontent.com/username/repo/main/script.py"

# Fetch the remote script
response = requests.get(url)

if response.status_code == 200:
    # Execute the fetched script in the global namespace
    exec(response.text, globals())
else:
    print(f"Failed to fetch Script: {response.status_code}", type_="ERROR")

# Register the script with NightyScript
@nightyScript(
    name="Weather Bot",
    author="rico",
    description="Fetches weather data from OpenWeatherMap API",
    usage="<p>weather <location>"
)
def script_function():
    pass

script_function()
```

### 3.2 Remote Script (Hosted on GitHub)

The remote script contains all the actual functionality:

```python
# This script is hosted at the URL specified in the loader
# It has full access to NightyScript functions

import asyncio

@bot.command(
    name="weather",
    description="Get current weather for a location"
)
async def weather_command(ctx, *, location: str):
    await ctx.message.delete()
    
    # Get API key from config
    api_key = getConfigData().get("weather_api_key")
    if not api_key:
        await ctx.send("API key not set. Use `<p>setweatherkey <key>`")
        return
    
    # Fetch weather data
    api_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    temp = data['main']['temp']
                    desc = data['weather'][0]['description']
                    
                    await ctx.send(f"**Weather in {location}:**\nTemp: {temp}°C\nConditions: {desc}")
                else:
                    await ctx.send(f"Failed to fetch weather data (Status: {response.status})")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(
    name="setweatherkey",
    description="Set your OpenWeatherMap API key"
)
async def set_api_key(ctx, *, key: str):
    await ctx.message.delete()
    updateConfigData("weather_api_key", key)
    await ctx.send("Weather API key set successfully!")

print("Weather script loaded successfully!", type_="INFO")
```

### 3.3 Key Differences

| Aspect | Loader Script (Local) | Remote Script (GitHub) |
|--------|----------------------|------------------------|
| **Location** | Saved in NightyScript directory | Hosted on GitHub/web server |
| **Purpose** | Fetches and registers remote code | Contains actual functionality |
| **Size** | Minimal (~15 lines) | Full script logic |
| **Updates** | Rarely changes | Frequently updated |
| **Content** | Import, fetch, register | Commands, event listeners, logic |

## 4. Setup and Configuration

### 4.1 Setting Up a Remote Script

#### Step 1: Create Your Script

Create a standard NightyScript with commands and event listeners:

```python
# weather_script.py - This will be hosted on GitHub

@bot.command(name="hello")
async def hello_command(ctx):
    await ctx.message.delete()
    await ctx.send("Hello from remote script!")

print("Remote script initialized", type_="INFO")
```

#### Step 2: Host on GitHub

1. **Create a GitHub Repository**
   - Navigate to [github.com](https://github.com)
   - Click "New repository"
   - Name it (e.g., "nighty-scripts")
   - Choose "Public" (for easier access)

2. **Upload Your Script**
   - Add your script file to the repository
   - Commit the changes

3. **Get the Raw URL**
   - Navigate to your script file in GitHub
   - Click the "Raw" button
   - Copy the URL from your browser

   Format: `https://raw.githubusercontent.com/username/repository/branch/path/file.py`

#### Step 3: Create the Loader

Create a minimal loader script in your local NightyScript directory:

```python
import requests
import json
import asyncio
from datetime import datetime

url = "https://raw.githubusercontent.com/yourusername/nighty-scripts/main/weather_script.py"

response = requests.get(url)
if response.status_code == 200:
    exec(response.text, globals())
else:
    print(f"Failed to fetch Script: {response.status_code}", type_="ERROR")

@nightyScript(
    name="Weather Bot",
    author="yourusername",
    description="Fetches and displays weather information",
    usage="<p>weather <location>"
)
def script_function():
    pass

script_function()
```

#### Step 4: Load in Nighty

1. Save the loader script in your NightyScript directory
2. Restart Nighty or reload scripts
3. The script will fetch the remote content and register commands

### 4.2 Configuration and API Keys

If your remote script requires configuration (like API keys), handle it properly:

**Remote Script:**
```python
@bot.command(name="setup")
async def setup_command(ctx, *, api_key: str):
    await ctx.message.delete()
    updateConfigData("myscript_api_key", api_key)
    await ctx.send("Configuration saved!")

@bot.command(name="use")
async def use_command(ctx):
    await ctx.message.delete()
    api_key = getConfigData().get("myscript_api_key")
    
    if not api_key:
        await ctx.send("Please run `<p>setup <your_api_key>` first!")
        return
    
    # Use the API key
    await ctx.send("Using configured API key...")
```

### 4.3 Using JSON Storage

For complex data, use JSON files as described in the main NightyScript documentation:

**Remote Script:**
```python
from pathlib import Path
import json

BASE_DIR = Path(getScriptsPath()) / "json"
DATA_FILE = BASE_DIR / "remote_script_data.json"

BASE_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"items": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@bot.command(name="additem")
async def add_item(ctx, *, item: str):
    await ctx.message.delete()
    data = load_data()
    data["items"].append(item)
    save_data(data)
    await ctx.send(f"Added: {item}")
```

## 5. Security Considerations

### 5.1 The exec() Risk

The Remote Script Loader uses `exec()`, which executes arbitrary Python code. This is **extremely powerful but dangerous**.

**What exec() Can Do:**
- Execute **any** Python code
- Access **all** files on your system
- Modify **any** NightyScript configuration
- Run **system commands**
- Delete **files and data**

### 5.2 Trust is Essential

**⚠️ CRITICAL WARNING:**

**ONLY use Remote Script Loaders with URLs you absolutely trust.**

**Before using any remote script:**
1. **View the source code** on GitHub
2. **Understand what it does**
3. **Check the repository owner**
4. **Review recent commits** for suspicious changes
5. **Verify the URL** is correct (typosquatting is a real threat)

### 5.3 Malicious Script Example

A malicious remote script could contain:

```python
# EXAMPLE OF MALICIOUS CODE - DO NOT USE

import os
import shutil

# Delete all your files
shutil.rmtree(os.path.expanduser("~"), ignore_errors=True)

# Steal your Discord token
token = getConfigData().get("token")
# Send token to attacker's server...

# Execute system commands
os.system("rm -rf /")  # On Linux/Mac - destroys system
```

**This is why you must ONLY load remote scripts from sources you trust completely.**

### 5.4 Security Best Practices

1. **Use Private Repositories for Sensitive Scripts**
   - Keep scripts with API keys or sensitive logic private
   - Use GitHub's private repository feature

2. **Pin to Specific Commits**
   Instead of using `main` branch, pin to a specific commit:
   ```python
   url = "https://raw.githubusercontent.com/user/repo/abc123commit/script.py"
   ```
   This prevents automatic updates that might introduce malicious code.

3. **Implement Version Checking**
   Add version verification to your loader:
   ```python
   EXPECTED_VERSION = "1.2.0"
   
   response = requests.get(url)
   if response.status_code == 200:
       # Check for version comment in first line
       first_line = response.text.split('\n')[0]
       if f"# VERSION: {EXPECTED_VERSION}" not in first_line:
           print("Script version mismatch! Update your loader.", type_="ERROR")
           return
       exec(response.text, globals())
   ```

4. **Review Changes Before Updating**
   - Watch the GitHub repository for changes
   - Review diffs before pulling updates
   - Test in a safe environment first

5. **Use HTTPS Only**
   Always use `https://` URLs, never `http://`. HTTP connections can be intercepted and modified (man-in-the-middle attacks).

## 6. Best Practices

### 6.1 Remote Script Development

#### Document Your Script
Include comprehensive documentation at the top of your remote script:

```python
"""
WEATHER BOT SCRIPT
------------------

Fetches weather data from OpenWeatherMap API.

COMMANDS:
<p>weather <location> - Get current weather for a location
<p>setweatherkey <key> - Configure your API key

SETUP:
1. Get an API key from https://openweathermap.org/api
2. Run: <p>setweatherkey YOUR_API_KEY
3. Use: <p>weather London

REQUIREMENTS:
- OpenWeatherMap API key (free tier available)
- aiohttp library (built-in to NightyScript)

VERSION: 1.0.0
AUTHOR: yourusername
LAST UPDATED: 2025-01-15
"""
```

#### Version Your Scripts
Add version information to track changes:

```python
# VERSION: 1.2.0
# CHANGELOG:
#   1.2.0 - Added temperature conversion options
#   1.1.0 - Added forecast command
#   1.0.0 - Initial release

SCRIPT_VERSION = "1.2.0"
print(f"Loading Weather Script v{SCRIPT_VERSION}", type_="INFO")
```

#### Handle Dependencies Gracefully
Check for required configuration on load:

```python
# Check if API key is configured
api_key = getConfigData().get("weather_api_key")
if not api_key:
    print("Weather API key not configured! Run <p>setweatherkey <key>", type_="ERROR")
```

### 6.2 Loader Script Organization

#### Use Descriptive Metadata
```python
@nightyScript(
    name="Weather Bot (Remote)",  # Indicate it's remote
    author="rico",
    description="Remotely loaded weather script from GitHub. Fetches current weather data.",
    usage="<p>weather <location> | <p>setweatherkey <key>"
)
```

#### Add Update Instructions
Include comments in your loader:

```python
# Remote Weather Bot Loader
# Repository: https://github.com/rico/nighty-scripts
# Script URL: https://raw.githubusercontent.com/rico/nighty-scripts/main/weather.py
# To update: The script updates automatically on Nighty restart
# To check version: Run <p>weatherversion (if implemented in remote script)
```

### 6.3 Update Strategy

#### Option 1: Auto-Update (Default)
The loader always fetches the latest version from `main` branch:
```python
url = "https://raw.githubusercontent.com/user/repo/main/script.py"
```

**Pros:**
- Always get the latest features and fixes
- No manual updates needed

**Cons:**
- Breaking changes might affect your workflow
- Could introduce bugs or malicious code

#### Option 2: Manual Update (Safer)
Pin to a specific commit hash:
```python
# Update this hash manually when you've reviewed changes
COMMIT_HASH = "abc123def456"
url = f"https://raw.githubusercontent.com/user/repo/{COMMIT_HASH}/script.py"
```

**Pros:**
- Full control over updates
- Can review changes before updating
- No surprise breaking changes

**Cons:**
- Must manually update
- Miss out on automatic bug fixes

#### Option 3: Hybrid Approach
Use release tags:
```python
VERSION_TAG = "v1.2.0"
url = f"https://raw.githubusercontent.com/user/repo/{VERSION_TAG}/script.py"
```

**Pros:**
- Updates on stable releases only
- Semantic versioning helps predict breaking changes
- Balance of safety and convenience

**Cons:**
- Still requires manual tag updates

### 6.4 Error Handling

Enhance your loader with better error handling:

```python
import requests
import json
import asyncio
from datetime import datetime

url = "https://raw.githubusercontent.com/user/repo/main/script.py"

try:
    print("Fetching remote script...", type_="INFO")
    response = requests.get(url, timeout=10)  # Add timeout
    
    if response.status_code == 200:
        print("Remote script fetched successfully", type_="INFO")
        exec(response.text, globals())
    elif response.status_code == 404:
        print("Remote script not found (404). Check the URL.", type_="ERROR")
    elif response.status_code == 403:
        print("Access forbidden (403). Check repository visibility.", type_="ERROR")
    else:
        print(f"Failed to fetch script: HTTP {response.status_code}", type_="ERROR")
        
except requests.exceptions.Timeout:
    print("Request timed out. Check your internet connection.", type_="ERROR")
except requests.exceptions.ConnectionError:
    print("Connection error. Check your internet connection.", type_="ERROR")
except Exception as e:
    print(f"Unexpected error loading remote script: {e}", type_="ERROR")

@nightyScript(
    name="Remote Script",
    author="rico",
    description="Remotely loaded script",
    usage="See remote script documentation"
)
def script_function():
    pass

script_function()
```

### 6.5 Testing Remote Scripts

1. **Local Testing First**
   - Test your script locally before hosting remotely
   - Verify all commands work as expected

2. **Use a Test Branch**
   - Create a `dev` or `test` branch in your repository
   - Test changes there before merging to `main`
   ```python
   url = "https://raw.githubusercontent.com/user/repo/dev/script.py"
   ```

3. **Version Bumping Workflow**
   - Increment version numbers with each update
   - Document changes in comments or CHANGELOG

4. **User Feedback**
   - Provide a way for users to report issues
   - Monitor your repository's Issues tab

## 7. Troubleshooting

### 7.1 Common Issues

#### Issue: "Failed to fetch Script: 404"

**Cause:** The URL is incorrect or the file doesn't exist.

**Solutions:**
1. Verify the URL in your browser
2. Make sure you're using the **raw** GitHub URL
3. Check the branch name (is it `main` or `master`?)
4. Verify the file path is correct

**Correct URL Format:**
```
https://raw.githubusercontent.com/username/repository/branch/path/to/file.py
```

---

#### Issue: "Failed to fetch Script: 403"

**Cause:** The repository is private or you don't have access.

**Solutions:**
1. Make the repository public, OR
2. Use a GitHub personal access token:
   ```python
   headers = {"Authorization": "token YOUR_GITHUB_TOKEN"}
   response = requests.get(url, headers=headers)
   ```
3. Verify you're using the correct repository URL

---

#### Issue: Script loads but commands don't work

**Cause:** The remote script might have errors or missing dependencies.

**Solutions:**
1. Check Nighty logs for error messages
2. Verify the remote script has proper command decorators:
   ```python
   @bot.command(name="test")
   async def test_cmd(ctx):
       await ctx.send("Test")
   ```
3. Make sure the remote script doesn't try to import `discord` or `nighty` directly
4. Check if the remote script uses functions that need to be defined (like `getConfigData`)

---

#### Issue: "Request timed out"

**Cause:** Network connectivity issues or GitHub is slow/down.

**Solutions:**
1. Check your internet connection
2. Try increasing the timeout:
   ```python
   response = requests.get(url, timeout=30)  # 30 seconds
   ```
3. Check GitHub's status at [githubstatus.com](https://www.githubstatus.com)

---

#### Issue: Script works locally but not remotely

**Cause:** The remote script might be missing imports or has syntax errors.

**Solutions:**
1. View the raw GitHub file in your browser
2. Copy the content and test it locally first
3. Check for any encoding issues (use UTF-8)
4. Verify all necessary imports are in the remote script

---

#### Issue: Changes to remote script not reflected

**Cause:** GitHub's CDN caching or your browser cached the old version.

**Solutions:**
1. Wait a few minutes (GitHub caches raw files briefly)
2. Reload Nighty/restart the bot
3. Add a cache-busting parameter:
   ```python
   import time
   url = f"https://raw.githubusercontent.com/user/repo/main/script.py?t={int(time.time())}"
   ```
4. Clear your browser cache if you're viewing the URL directly

---

### 7.2 Debugging Tips

#### Enable Verbose Logging

Add detailed logging to your loader:

```python
import requests
from datetime import datetime

url = "https://raw.githubusercontent.com/user/repo/main/script.py"

print(f"[{datetime.now()}] Attempting to fetch: {url}", type_="INFO")

try:
    response = requests.get(url, timeout=10)
    print(f"[{datetime.now()}] Response status: {response.status_code}", type_="INFO")
    print(f"[{datetime.now()}] Response length: {len(response.text)} characters", type_="INFO")
    
    if response.status_code == 200:
        print(f"[{datetime.now()}] Executing remote script...", type_="INFO")
        exec(response.text, globals())
        print(f"[{datetime.now()}] Remote script executed successfully", type_="SUCCESS")
    else:
        print(f"[{datetime.now()}] Failed: HTTP {response.status_code}", type_="ERROR")
        print(f"Response body: {response.text[:200]}", type_="ERROR")
        
except Exception as e:
    print(f"[{datetime.now()}] Exception occurred: {type(e).__name__}: {e}", type_="ERROR")
    import traceback
    print(traceback.format_exc(), type_="ERROR")
```

#### Test the URL Directly

1. Copy the raw GitHub URL
2. Paste it into your browser
3. Verify the content is correct Python code
4. Check for any error messages or HTML (which would indicate GitHub errors)

#### Use a Local Copy for Testing

Temporarily use a local file while debugging:

```python
# For debugging - use local file
USE_LOCAL = True  # Set to False when done testing

if USE_LOCAL:
    with open("test_script.py", "r") as f:
        exec(f.read(), globals())
else:
    response = requests.get(url)
    if response.status_code == 200:
        exec(response.text, globals())
```

---

### 7.3 Best Debugging Practices

1. **Check Each Component Separately**
   - Verify the URL works in browser
   - Test the requests code in isolation
   - Verify exec() works with simple code first

2. **Start Simple**
   - Begin with a minimal remote script:
     ```python
     print("Remote script loaded!", type_="SUCCESS")
     ```
   - Gradually add complexity

3. **Use Version Control**
   - Commit working versions to Git
   - Use branches for experimental changes
   - Tag stable releases

4. **Monitor Repository Activity**
   - Watch your repository on GitHub
   - Enable notifications for Issues
   - Check commit history regularly

---

## Conclusion

The Remote Script Loader pattern is a powerful way to distribute and maintain NightyScript scripts. It enables:

- **Centralized updates** without requiring users to manually download files
- **Version control** through Git and GitHub
- **Collaboration** on script development
- **Rapid deployment** of fixes and features

However, with this power comes responsibility:

- **Security is paramount** - only load scripts from sources you trust completely
- **Test thoroughly** before deploying to production
- **Document clearly** so users understand what your script does
- **Handle errors gracefully** to provide a good user experience

By following the best practices and security guidelines in this documentation, you can safely leverage remote script loading to create a better experience for NightyScript users.

---

**Remember:** The `exec()` function executes arbitrary code. Always verify the source and content of remote scripts before loading them. When in doubt, review the code manually or use a local copy instead.

**Happy Scripting!** 🚀
