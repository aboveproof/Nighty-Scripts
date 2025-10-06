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
        "speedtest_download_size_mb": 10,  # MB to download for speed test
        "speedtest_upload_size_mb": 5,     # MB to upload for speed test
        "speedtest_connections": 3,         # Concurrent connections
        "speedtest_timeout": 15,            # Timeout in seconds
        "speedtest_history_limit": 20       # Max stored results
    }
    
    for key, default_value in config_defaults.items():
        if getConfigData().get(key) is None:
            updateConfigData(key, default_value)
    
    # ============================================================================
    # TEST SERVERS
    # ============================================================================
    
    # Public test files for speed testing (large, publicly accessible files)
    TEST_SERVERS = [
        {
            "name": "GitHub",
            "download_url": "https://github.com/git/git/archive/refs/tags/v2.40.0.zip",
            "ping_url": "https://api.github.com",
            "upload_url": "https://httpbin.org/post"
        },
        {
            "name": "Cloudflare",
            "download_url": "https://speed.cloudflare.com/__down?bytes=10000000",
            "ping_url": "https://1.1.1.1",
            "upload_url": "https://httpbin.org/post"
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
        if bytes_per_second <= 0:
            return "0.00 Mbps"
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
    
    async def test_ping(server_url, count=4):
        """
        Measure ping (latency) to a server.
        Returns average ping in milliseconds and jitter.
        """
        pings = []
        timeout_config = aiohttp.ClientTimeout(total=5)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                for i in range(count):
                    start = time.time()
                    try:
                        async with session.get(server_url, allow_redirects=True) as response:
                            # Just read a bit to ensure connection
                            await response.read()
                            elapsed = (time.time() - start) * 1000  # Convert to ms
                            pings.append(elapsed)
                            print(f"Ping {i+1}/{count}: {elapsed:.1f}ms", type_="INFO")
                    except Exception as e:
                        print(f"Ping attempt {i+1} failed: {e}", type_="ERROR")
                    
                    if i < count - 1:  # Don't sleep after last ping
                        await asyncio.sleep(0.2)
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
    
    async def download_chunk(session, url, chunk_num, max_bytes):
        """Download data and return bytes received."""
        bytes_downloaded = 0
        try:
            print(f"Starting download chunk {chunk_num}...", type_="INFO")
            async with session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    # Read in chunks to track progress
                    chunk_size = 8192
                    while bytes_downloaded < max_bytes:
                        chunk = await response.content.read(chunk_size)
                        if not chunk:
                            break
                        bytes_downloaded += len(chunk)
                        if bytes_downloaded >= max_bytes:
                            break
                    
                    print(f"Chunk {chunk_num} downloaded {format_size(bytes_downloaded)}", type_="INFO")
                else:
                    print(f"Chunk {chunk_num} got status {response.status}", type_="ERROR")
        except asyncio.TimeoutError:
            print(f"Chunk {chunk_num} timed out after {format_size(bytes_downloaded)}", type_="ERROR")
        except Exception as e:
            print(f"Chunk {chunk_num} error: {e}", type_="ERROR")
        
        return bytes_downloaded
    
    async def test_download(server_url, size_mb, connections):
        """
        Test download speed by downloading data from server.
        Returns download speed in bytes per second.
        """
        total_size = size_mb * 1024 * 1024  # Convert MB to bytes
        chunk_size = total_size // connections
        
        timeout_config = aiohttp.ClientTimeout(total=30, sock_read=15)
        
        try:
            print(f"Testing download with {connections} connections, {size_mb}MB total", type_="INFO")
            
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                start_time = time.time()
                
                # Create concurrent download tasks
                tasks = [
                    download_chunk(session, server_url, i+1, chunk_size)
                    for i in range(connections)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter out exceptions and sum bytes
                total_downloaded = sum(r for r in results if isinstance(r, int))
                
                elapsed = time.time() - start_time
                
                print(f"Downloaded {format_size(total_downloaded)} in {elapsed:.2f}s", type_="INFO")
                
                if elapsed > 0 and total_downloaded > 0:
                    speed = total_downloaded / elapsed
                    print(f"Download speed: {format_speed(speed)}", type_="SUCCESS")
                    return speed
                else:
                    print("Download test produced no valid results", type_="ERROR")
                    return 0
        except Exception as e:
            print(f"Download test error: {e}", type_="ERROR")
            return 0
    
    async def upload_chunk(session, url, chunk_num, data_size):
        """Upload a chunk of data and return bytes sent."""
        try:
            # Generate data to upload
            data = b'X' * data_size
            
            print(f"Starting upload chunk {chunk_num}...", type_="INFO")
            async with session.post(url, data=data) as response:
                await response.read()  # Consume response
                if response.status < 500:
                    print(f"Chunk {chunk_num} uploaded {format_size(data_size)}", type_="INFO")
                    return data_size
                else:
                    print(f"Chunk {chunk_num} upload failed with status {response.status}", type_="ERROR")
        except Exception as e:
            print(f"Upload chunk {chunk_num} error: {e}", type_="ERROR")
        return 0
    
    async def test_upload(server_url, size_mb, connections):
        """
        Test upload speed by uploading data to server.
        Returns upload speed in bytes per second.
        """
        total_size = size_mb * 1024 * 1024
        chunk_size = total_size // connections
        
        timeout_config = aiohttp.ClientTimeout(total=30, sock_read=15)
        
        try:
            print(f"Testing upload with {connections} connections, {size_mb}MB total", type_="INFO")
            
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                start_time = time.time()
                
                tasks = [
                    upload_chunk(session, server_url, i+1, chunk_size)
                    for i in range(connections)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter out exceptions and sum bytes
                total_uploaded = sum(r for r in results if isinstance(r, int))
                
                elapsed = time.time() - start_time
                
                print(f"Uploaded {format_size(total_uploaded)} in {elapsed:.2f}s", type_="INFO")
                
                if elapsed > 0 and total_uploaded > 0:
                    speed = total_uploaded / elapsed
                    print(f"Upload speed: {format_speed(speed)}", type_="SUCCESS")
                    return speed
                else:
                    print("Upload test produced no valid results", type_="ERROR")
                    return 0
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
        download_size = getConfigData().get("speedtest_download_size_mb", 10)
        upload_size = getConfigData().get("speedtest_upload_size_mb", 5)
        connections = getConfigData().get("speedtest_connections", 3)
        
        server = TEST_SERVERS[0]
        
        # Test ping
        print("Testing ping...", type_="INFO")
        avg_ping, jitter = await test_ping(server["ping_url"])
        results["ping"] = avg_ping
        results["jitter"] = jitter
        
        # Test download
        print("Testing download speed...", type_="INFO")
        download_speed = await test_download(server["download_url"], download_size, connections)
        results["download"] = download_speed
        
        # Test upload (skip in quick mode)
        if not quick_mode:
            print("Testing upload speed...", type_="INFO")
            upload_speed = await test_upload(server["upload_url"], upload_size, connections)
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
            msg = await ctx.send("🚀 Running quick speed test...", silent=True)
            
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
                except Exception as embed_error:
                    print(f"Embed send error: {embed_error}", type_="ERROR")
                    # Fallback to regular message
                    await ctx.send(content)
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
**Download URL:** {server['download_url'][:60]}...
**Ping URL:** {server['ping_url']}
**Upload URL:** {server['upload_url']}

**Configuration:**
- Download Size: {getConfigData().get('speedtest_download_size_mb', 10)} MB
- Upload Size: {getConfigData().get('speedtest_upload_size_mb', 5)} MB
- Connections: {getConfigData().get('speedtest_connections', 3)}
- Timeout: {getConfigData().get('speedtest_timeout', 15)}s
"""
            
            current_private = getConfigData().get("private")
            updateConfigData("private", False)
            
            try:
                await forwardEmbedMethod(
                    channel_id=ctx.channel.id,
                    content=content
                )
            except:
                await ctx.send(content)
            finally:
                updateConfigData("private", current_private)
        
        # Configuration
        elif subcommand == "config":
            if not subargs:
                await ctx.send("Usage: `<p>speedtest config <setting> <value>`\nSettings: size, upload, connections, timeout", silent=True)
                return
            
            config_parts = subargs.split(maxsplit=1)
            if len(config_parts) != 2:
                await ctx.send("Invalid config format. Use: `<p>speedtest config <setting> <value>`", silent=True)
                return
            
            setting, value = config_parts
            setting = setting.lower()
            
            try:
                value = int(value)
                
                if setting in ["size", "download"]:
                    if 1 <= value <= 50:
                        updateConfigData("speedtest_download_size_mb", value)
                        await ctx.send(f"✅ Download test size set to {value} MB", silent=True)
                    else:
                        await ctx.send("❌ Download size must be between 1 and 50 MB", silent=True)
                
                elif setting == "upload":
                    if 1 <= value <= 25:
                        updateConfigData("speedtest_upload_size_mb", value)
                        await ctx.send(f"✅ Upload test size set to {value} MB", silent=True)
                    else:
                        await ctx.send("❌ Upload size must be between 1 and 25 MB", silent=True)
                
                elif setting in ["connections", "conn"]:
                    if 1 <= value <= 5:
                        updateConfigData("speedtest_connections", value)
                        await ctx.send(f"✅ Concurrent connections set to {value}", silent=True)
                    else:
                        await ctx.send("❌ Connections must be between 1 and 5", silent=True)
                
                elif setting == "timeout":
                    if 10 <= value <= 60:
                        updateConfigData("speedtest_timeout", value)
                        await ctx.send(f"✅ Timeout set to {value} seconds", silent=True)
                    else:
                        await ctx.send("❌ Timeout must be between 10 and 60 seconds", silent=True)
                
                else:
                    await ctx.send(f"❌ Unknown setting: {setting}", silent=True)
            
            except ValueError:
                await ctx.send("❌ Value must be a number", silent=True)
        
        # History
        elif subcommand == "history":
            history = load_history()
            
            if not history:
                await ctx.send("No speed test history available.", silent=True)
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
            except:
                await ctx.send(content)
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
- `size` or `download` - Download test size (1-50 MB)
- `upload` - Upload test size (1-25 MB)
- `connections` - Concurrent connections (1-5)
- `timeout` - Request timeout (10-60 seconds)

**Examples:**
`{getConfigData().get('prefix', '<p>')}speedtest`
`{getConfigData().get('prefix', '<p>')}speedtest quick`
`{getConfigData().get('prefix', '<p>')}speedtest config size 10`
"""
            
            current_private = getConfigData().get("private")
            updateConfigData("private", False)
            
            try:
                await forwardEmbedMethod(
                    channel_id=ctx.channel.id,
                    content=help_text
                )
            except:
                await ctx.send(help_text)
            finally:
                updateConfigData("private", current_private)
        
        # Default: Full speed test
        else:
            msg = await ctx.send("🚀 Running full speed test... This may take 30-60 seconds.", silent=True)
            
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
                except Exception as embed_error:
                    print(f"Embed send error: {embed_error}", type_="ERROR")
                    # Fallback to regular message
                    await ctx.send(content)
                finally:
                    updateConfigData("private", current_private)
                
            except Exception as e:
                await msg.edit(content=f"❌ Speed test failed: {str(e)}")
                print(f"Speed test error: {e}", type_="ERROR")
    
    print("Speed Test script loaded successfully!", type_="SUCCESS")

# Initialize the script
speedtest_script()
