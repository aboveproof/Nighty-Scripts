"""
NightyScript Speed Test
-----------------------

A comprehensive network speed test script for Nighty that measures download speed,
upload speed, ping, and jitter using multiple test servers.

COMMANDS:
<p>speedtest - Run a full speed test (download, upload, ping)
<p>speedtest quick - Run a quick speed test (download and ping only)
<p>speedtest server - Show current test server information
<p>speedtest config - Configure speed test settings
<p>speedtest history - View recent speed test results

EXAMPLES:
<p>speedtest              - Full speed test
<p>speedtest quick        - Quick test (faster)
<p>speedtest config size 50  - Set download test size to 50MB

NOTES:
- Uses multiple concurrent connections for accurate results
- Tests against reliable public test servers
- Stores test history in JSON for tracking over time
- All tests run asynchronously to avoid blocking the bot
- Results are formatted with appropriate units (Mbps, ms)

DEPENDENCIES:
- aiohttp (built-in)
- asyncio (built-in)
- json (built-in)
- time (built-in)
"""

import aiohttp
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

def speedtest_script():
    """
    Main script function - initializes commands and configuration.
    """
    
    # ============================================================================
    # CONFIGURATION & DATA MANAGEMENT
    # ============================================================================
    
    # JSON storage setup
    BASE_DIR = Path(getScriptsPath()) / "json"
    HISTORY_FILE = BASE_DIR / "speedtest_history.json"
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize history file
    if not HISTORY_FILE.exists():
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f, indent=4)
    
    # Initialize config with defaults
    config_defaults = {
        "speedtest_download_size_mb": 25,  # MB to download for speed test
        "speedtest_upload_size_mb": 10,    # MB to upload for speed test
        "speedtest_connections": 4,         # Concurrent connections
        "speedtest_timeout": 30,            # Timeout in seconds
        "speedtest_history_limit": 20       # Max stored results
    }
    
    for key, default_value in config_defaults.items():
        if getConfigData().get(key) is None:
            updateConfigData(key, default_value)
    
    # ============================================================================
    # TEST SERVERS
    # ============================================================================
    
    # Public test servers for speed testing
    TEST_SERVERS = [
        {
            "name": "Cloudflare",
            "url": "https://speed.cloudflare.com/__down",
            "ping_url": "https://1.1.1.1"
        },
        {
            "name": "Google",
            "url": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png",
            "ping_url": "https://www.google.com"
        },
        {
            "name": "GitHub",
            "url": "https://github.com",
            "ping_url": "https://github.com"
        }
    ]
    
    # ============================================================================
    # HELPER FUNCTIONS
    # ============================================================================
    
    def load_history():
        """Load speed test history from JSON file."""
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def save_history(history):
        """Save speed test history to JSON file."""
        try:
            # Limit history size
            history_limit = getConfigData().get("speedtest_history_limit", 20)
            limited_history = history[-history_limit:]
            
            with open(HISTORY_FILE, "w") as f:
                json.dump(limited_history, f, indent=4)
        except IOError as e:
            print(f"Error saving speed test history: {e}", type_="ERROR")
    
    def format_speed(bytes_per_second):
        """Convert bytes/second to Mbps."""
        mbps = (bytes_per_second * 8) / (1024 * 1024)
        return f"{mbps:.2f} Mbps"
    
    def format_size(size_bytes):
        """Format bytes into human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    # ============================================================================
    # SPEED TEST FUNCTIONS
    # ============================================================================
    
    async def test_ping(server_url, count=5):
        """
        Measure ping (latency) to a server.
        Returns average ping in milliseconds and jitter.
        """
        pings = []
        
        try:
            async with aiohttp.ClientSession() as session:
                for _ in range(count):
                    start = time.time()
                    try:
                        async with session.head(server_url, timeout=5) as response:
                            if response.status < 500:  # Accept any non-server-error
                                elapsed = (time.time() - start) * 1000  # Convert to ms
                                pings.append(elapsed)
                    except:
                        pass  # Skip failed pings
                    
                    await asyncio.sleep(0.1)  # Small delay between pings
        except Exception as e:
            print(f"Ping test error: {e}", type_="ERROR")
            return None, None
        
        if not pings:
            return None, None
        
        avg_ping = sum(pings) / len(pings)
        
        # Calculate jitter (variance in ping)
        if len(pings) > 1:
            jitter = sum(abs(pings[i] - pings[i-1]) for i in range(1, len(pings))) / (len(pings) - 1)
        else:
            jitter = 0
        
        return avg_ping, jitter
    
    async def download_chunk(session, url, chunk_size):
        """Download a chunk of data and return bytes received."""
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.read()
                    return len(data)
        except:
            pass
        return 0
    
    async def test_download(server_url, size_mb, connections):
        """
        Test download speed by downloading data from server.
        Returns download speed in bytes per second.
        """
        total_size = size_mb * 1024 * 1024  # Convert MB to bytes
        chunk_size = total_size // connections
        
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                # Create concurrent download tasks
                tasks = [
                    download_chunk(session, server_url, chunk_size)
                    for _ in range(connections)
                ]
                
                results = await asyncio.gather(*tasks)
                total_downloaded = sum(results)
                
                elapsed = time.time() - start_time
                
                if elapsed > 0 and total_downloaded > 0:
                    return total_downloaded / elapsed
        except Exception as e:
            print(f"Download test error: {e}", type_="ERROR")
        
        return 0
    
    async def upload_chunk(session, url, data_size):
        """Upload a chunk of data and return bytes sent."""
        try:
            # Generate random data to upload
            data = b'0' * data_size
            
            async with session.post(url, data=data, timeout=10) as response:
                if response.status < 500:
                    return data_size
        except:
            pass
        return 0
    
    async def test_upload(server_url, size_mb, connections):
        """
        Test upload speed by uploading data to server.
        Returns upload speed in bytes per second.
        """
        total_size = size_mb * 1024 * 1024
        chunk_size = total_size // connections
        
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                tasks = [
                    upload_chunk(session, server_url, chunk_size)
                    for _ in range(connections)
                ]
                
                results = await asyncio.gather(*tasks)
                total_uploaded = sum(results)
                
                elapsed = time.time() - start_time
                
                if elapsed > 0 and total_uploaded > 0:
                    return total_uploaded / elapsed
        except Exception as e:
            print(f"Upload test error: {e}", type_="ERROR")
        
        return 0
    
    async def run_full_speedtest(quick_mode=False):
        """
        Run a complete speed test.
        Returns dictionary with all results.
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "server": TEST_SERVERS[0]["name"],
            "ping": None,
            "jitter": None,
            "download": None,
            "upload": None,
            "quick_mode": quick_mode
        }
        
        # Get config values
        download_size = getConfigData().get("speedtest_download_size_mb", 25)
        upload_size = getConfigData().get("speedtest_upload_size_mb", 10)
        connections = getConfigData().get("speedtest_connections", 4)
        
        server = TEST_SERVERS[0]
        
        # Test ping
        print("Testing ping...", type_="INFO")
        avg_ping, jitter = await test_ping(server["ping_url"])
        results["ping"] = avg_ping
        results["jitter"] = jitter
        
        # Test download
        print("Testing download speed...", type_="INFO")
        download_speed = await test_download(server["url"], download_size, connections)
        results["download"] = download_speed
        
        # Test upload (skip in quick mode)
        if not quick_mode:
            print("Testing upload speed...", type_="INFO")
            upload_speed = await test_upload(server["url"], upload_size, connections)
            results["upload"] = upload_speed
        
        return results
    
    # ============================================================================
    # COMMANDS
    # ============================================================================
    
    @bot.command(
        name="speedtest",
        aliases=["st"],
        usage="[quick|server|config|history] [args]",
        description="Run network speed test or manage settings"
    )
    async def speedtest_command(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        parts = args.strip().split(maxsplit=1)
        subcommand = parts[0].lower() if parts else ""
        subargs = parts[1] if len(parts) > 1 else ""
        
        # Quick mode
        if subcommand == "quick":
            msg = await ctx.send("🚀 Running quick speed test...")
            
            try:
                results = await run_full_speedtest(quick_mode=True)
                
                # Save to history
                history = load_history()
                history.append(results)
                save_history(history)
                
                # Format results
                content = f"""# 🚀 Quick Speed Test Results

**Server:** {results['server']}
**Time:** {datetime.fromisoformat(results['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}

📊 **Results:**
"""
                
                if results['ping'] is not None:
                    content += f"- **Ping:** {results['ping']:.1f} ms\n"
                    if results['jitter'] is not None:
                        content += f"- **Jitter:** {results['jitter']:.1f} ms\n"
                
                if results['download'] and results['download'] > 0:
                    content += f"- **Download:** {format_speed(results['download'])}\n"
                else:
                    content += "- **Download:** Test failed\n"
                
                content += "\n> Quick mode: Upload test skipped"
                
                await msg.delete()
                
                # Temporarily disable private mode
                current_private = getConfigData().get("private")
                updateConfigData("private", False)
                
                try:
                    await forwardEmbedMethod(
                        channel_id=ctx.channel.id,
                        content=content,
                        title="⚡ Quick Speed Test"
                    )
                finally:
                    updateConfigData("private", current_private)
                
            except Exception as e:
                await msg.edit(content=f"❌ Speed test failed: {str(e)}")
                print(f"Speed test error: {e}", type_="ERROR")
        
        # Server info
        elif subcommand == "server":
            server = TEST_SERVERS[0]
            content = f"""# 🌐 Speed Test Server

**Current Server:** {server['name']}
**Test URL:** {server['url'][:50]}...
**Ping URL:** {server['ping_url']}

**Configuration:**
- Download Size: {getConfigData().get('speedtest_download_size_mb', 25)} MB
- Upload Size: {getConfigData().get('speedtest_upload_size_mb', 10)} MB
- Connections: {getConfigData().get('speedtest_connections', 4)}
- Timeout: {getConfigData().get('speedtest_timeout', 30)}s
"""
            
            current_private = getConfigData().get("private")
            updateConfigData("private", False)
            
            try:
                await forwardEmbedMethod(
                    channel_id=ctx.channel.id,
                    content=content
                )
            finally:
                updateConfigData("private", current_private)
        
        # Configuration
        elif subcommand == "config":
            if not subargs:
                await ctx.send("Usage: `<p>speedtest config <setting> <value>`\nSettings: size, upload, connections, timeout")
                return
            
            config_parts = subargs.split(maxsplit=1)
            if len(config_parts) != 2:
                await ctx.send("Invalid config format. Use: `<p>speedtest config <setting> <value>`")
                return
            
            setting, value = config_parts
            setting = setting.lower()
            
            try:
                value = int(value)
                
                if setting in ["size", "download"]:
                    if 1 <= value <= 100:
                        updateConfigData("speedtest_download_size_mb", value)
                        await ctx.send(f"✅ Download test size set to {value} MB")
                    else:
                        await ctx.send("❌ Download size must be between 1 and 100 MB")
                
                elif setting == "upload":
                    if 1 <= value <= 50:
                        updateConfigData("speedtest_upload_size_mb", value)
                        await ctx.send(f"✅ Upload test size set to {value} MB")
                    else:
                        await ctx.send("❌ Upload size must be between 1 and 50 MB")
                
                elif setting in ["connections", "conn"]:
                    if 1 <= value <= 10:
                        updateConfigData("speedtest_connections", value)
                        await ctx.send(f"✅ Concurrent connections set to {value}")
                    else:
                        await ctx.send("❌ Connections must be between 1 and 10")
                
                elif setting == "timeout":
                    if 10 <= value <= 120:
                        updateConfigData("speedtest_timeout", value)
                        await ctx.send(f"✅ Timeout set to {value} seconds")
                    else:
                        await ctx.send("❌ Timeout must be between 10 and 120 seconds")
                
                else:
                    await ctx.send(f"❌ Unknown setting: {setting}")
            
            except ValueError:
                await ctx.send("❌ Value must be a number")
        
        # History
        elif subcommand == "history":
            history = load_history()
            
            if not history:
                await ctx.send("No speed test history available.")
                return
            
            # Show last 5 results
            recent = history[-5:]
            content = "# 📊 Speed Test History\n\n"
            
            for i, result in enumerate(reversed(recent), 1):
                timestamp = datetime.fromisoformat(result['timestamp']).strftime('%m/%d %H:%M')
                content += f"**{i}. {timestamp}** - {result['server']}\n"
                
                if result.get('ping'):
                    content += f"   Ping: {result['ping']:.1f}ms"
                if result.get('download'):
                    content += f" | Down: {format_speed(result['download'])}"
                if result.get('upload'):
                    content += f" | Up: {format_speed(result['upload'])}"
                
                content += "\n\n"
            
            current_private = getConfigData().get("private")
            updateConfigData("private", False)
            
            try:
                await forwardEmbedMethod(
                    channel_id=ctx.channel.id,
                    content=content
                )
            finally:
                updateConfigData("private", current_private)
        
        # Help or unknown subcommand
        elif subcommand in ["help", "?"] or (subcommand and subcommand not in ["quick", "server", "config", "history"]):
            help_text = f"""# 🚀 Speed Test Help

**Usage:**
`{getConfigData().get('prefix', '<p>')}speedtest` - Run full speed test
`{getConfigData().get('prefix', '<p>')}speedtest quick` - Quick test (no upload)
`{getConfigData().get('prefix', '<p>')}speedtest server` - Server information
`{getConfigData().get('prefix', '<p>')}speedtest config <setting> <value>` - Configure
`{getConfigData().get('prefix', '<p>')}speedtest history` - View history

**Config Settings:**
- `size` or `download` - Download test size (1-100 MB)
- `upload` - Upload test size (1-50 MB)
- `connections` - Concurrent connections (1-10)
- `timeout` - Request timeout (10-120 seconds)

**Examples:**
`{getConfigData().get('prefix', '<p>')}speedtest`
`{getConfigData().get('prefix', '<p>')}speedtest quick`
`{getConfigData().get('prefix', '<p>')}speedtest config size 50`
"""
            
            current_private = getConfigData().get("private")
            updateConfigData("private", False)
            
            try:
                await forwardEmbedMethod(
                    channel_id=ctx.channel.id,
                    content=help_text
                )
            finally:
                updateConfigData("private", current_private)
        
        # Default: Full speed test
        else:
            msg = await ctx.send("🚀 Running full speed test... This may take a minute.")
            
            try:
                results = await run_full_speedtest(quick_mode=False)
                
                # Save to history
                history = load_history()
                history.append(results)
                save_history(history)
                
                # Format results
                content = f"""# 🚀 Speed Test Results

**Server:** {results['server']}
**Time:** {datetime.fromisoformat(results['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}

📊 **Results:**
"""
                
                if results['ping'] is not None:
                    content += f"- **Ping:** {results['ping']:.1f} ms"
                    if results['jitter'] is not None:
                        content += f" (Jitter: {results['jitter']:.1f} ms)"
                    content += "\n"
                
                if results['download'] and results['download'] > 0:
                    content += f"- **Download:** {format_speed(results['download'])}\n"
                else:
                    content += "- **Download:** Test failed\n"
                
                if results['upload'] and results['upload'] > 0:
                    content += f"- **Upload:** {format_speed(results['upload'])}\n"
                else:
                    content += "- **Upload:** Test failed\n"
                
                # Add quality assessment
                if results['download'] and results['download'] > 0:
                    mbps = (results['download'] * 8) / (1024 * 1024)
                    if mbps > 100:
                        quality = "🟢 Excellent"
                    elif mbps > 50:
                        quality = "🟡 Good"
                    elif mbps > 25:
                        quality = "🟠 Fair"
                    else:
                        quality = "🔴 Poor"
                    
                    content += f"\n**Connection Quality:** {quality}"
                
                await msg.delete()
                
                # Temporarily disable private mode
                current_private = getConfigData().get("private")
                updateConfigData("private", False)
                
                try:
                    await forwardEmbedMethod(
                        channel_id=ctx.channel.id,
                        content=content,
                        title="⚡ Full Speed Test"
                    )
                finally:
                    updateConfigData("private", current_private)
                
            except Exception as e:
                await msg.edit(content=f"❌ Speed test failed: {str(e)}")
                print(f"Speed test error: {e}", type_="ERROR")
    
    print("Speed Test script loaded successfully!", type_="SUCCESS")

speedtest_script()
