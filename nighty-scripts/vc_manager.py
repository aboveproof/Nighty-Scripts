import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

def vc_manager_farm_script():
    
    # ==================== INITIALIZATION ====================
    VC_DATA_PATH = Path(getScriptsPath()) / "json" / "vc_manager_data.json"
    VC_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    DEFAULT_DATA = {
        "total_vc_time_seconds": 0,
        "sessions": [],
        "settings": {
            "auto_disconnect_minutes": None,
            "muted": False,
            "deafened": False
        }
    }
    
    # Global state
    active_channel = None
    connection_start_time = None
    disconnect_task = None
    stats_update_task = None
    temp = {}
    is_muted = False
    is_deafened = False
    is_streaming = False
    is_camera_on = False
    
    # UI references (will be set during UI creation)
    ui_refs = {}
    
    # ==================== DATA MANAGEMENT ====================
    def load_data():
        """Load VC data from JSON file"""
        try:
            if VC_DATA_PATH.exists():
                with open(VC_DATA_PATH, 'r') as f:
                    return json.load(f)
            else:
                save_data(DEFAULT_DATA)
                return DEFAULT_DATA
        except Exception as e:
            print(f"Error loading VC data: {e}", type_="ERROR")
            return DEFAULT_DATA
    
    def save_data(data):
        """Save VC data to JSON file"""
        try:
            with open(VC_DATA_PATH, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving VC data: {e}", type_="ERROR")
    
    # ==================== UTILITY FUNCTIONS ====================
    def delete_after():
        """Get delete timer from config"""
        return getConfigData().get('deletetimer', 10)
    
    def format_duration(seconds):
        """Format seconds into readable duration"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours}h {minutes}m {secs}s"
    
    def get_current_session_duration():
        """Get duration of current VC session"""
        if connection_start_time is None:
            return 0
        return (datetime.now() - connection_start_time).total_seconds()
    
    def update_session_stats():
        """Update session statistics in data file"""
        if connection_start_time is None:
            return
        
        data = load_data()
        session_duration = get_current_session_duration()
        
        # Add to total time
        data["total_vc_time_seconds"] += session_duration
        
        # Record session
        session_record = {
            "channel_id": str(active_channel.id) if active_channel else "unknown",
            "channel_name": active_channel.name if active_channel else "Unknown",
            "guild_name": active_channel.guild.name if active_channel and active_channel.guild else "Unknown",
            "start_time": connection_start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": session_duration
        }
        
        data["sessions"].append(session_record)
        
        # Keep only last 100 sessions
        if len(data["sessions"]) > 100:
            data["sessions"] = data["sessions"][-100:]
        
        save_data(data)
    
    async def schedule_disconnect(minutes):
        """Schedule automatic disconnect after specified minutes"""
        nonlocal disconnect_task
        
        if disconnect_task:
            disconnect_task.cancel()
        
        if minutes is None or minutes <= 0:
            return
        
        async def disconnect_timer():
            try:
                await asyncio.sleep(minutes * 60)
                if active_channel:
                    print(f"Auto-disconnect timer expired, leaving VC", type_="INFO")
                    await connect(None, None)
            except asyncio.CancelledError:
                pass
        
        disconnect_task = asyncio.create_task(disconnect_timer())
    
    # ==================== UI UPDATE FUNCTIONS ====================
    def update_all_ui():
        """Update all UI elements to reflect current state"""
        try:
            # Update connection status
            if active_channel:
                ui_refs['status_text'].content = "Status: 🟢 Connected"
                ui_refs['status_text'].color = "#00FF00"
                ui_refs['channel_name_text'].content = f"Channel: {active_channel.name}"
                ui_refs['channel_id_text'].content = f"Channel ID: {active_channel.id}"
                ui_refs['guild_name_text'].content = f"Server: {active_channel.guild.name if active_channel.guild else 'Unknown'}"
                
                session_duration = get_current_session_duration()
                ui_refs['session_time_text'].content = f"Session Time: {format_duration(session_duration)}"
                
                # Enable voice controls
                ui_refs['mute_toggle'].disabled = False
                ui_refs['deafen_toggle'].disabled = False
                ui_refs['stream_toggle'].disabled = False
                ui_refs['camera_toggle'].disabled = False
            else:
                ui_refs['status_text'].content = "Status: 🔴 Disconnected"
                ui_refs['status_text'].color = "#FF0000"
                ui_refs['channel_name_text'].content = "Channel: None"
                ui_refs['channel_id_text'].content = "Channel ID: None"
                ui_refs['guild_name_text'].content = "Server: None"
                ui_refs['session_time_text'].content = "Session Time: 0s"
                
                # Disable voice controls and reset to OFF
                ui_refs['mute_toggle'].disabled = True
                ui_refs['deafen_toggle'].disabled = True
                ui_refs['stream_toggle'].disabled = True
                ui_refs['camera_toggle'].disabled = True
                ui_refs['mute_toggle'].checked = False
                ui_refs['deafen_toggle'].checked = False
                ui_refs['stream_toggle'].checked = False
                ui_refs['camera_toggle'].checked = False
                
                # Reset dropdown selections
                ui_refs['server_select'].selected_items = []
                ui_refs['channel_select'].selected_items = []
                ui_refs['channel_select'].visible = False
                ui_refs['channel_id_input'].value = ""
            
            # Update voice state toggles when connected
            if active_channel:
                ui_refs['mute_toggle'].checked = is_muted
                ui_refs['deafen_toggle'].checked = is_deafened
                ui_refs['stream_toggle'].checked = is_streaming
                ui_refs['camera_toggle'].checked = is_camera_on
            
            # Update total stats
            data = load_data()
            ui_refs['total_time_text'].content = f"Total VC Time: {format_duration(data['total_vc_time_seconds'])}"
            ui_refs['session_count_text'].content = f"Total Sessions: {len(data['sessions'])}"
            
        except Exception as e:
            print(f"Error updating UI: {e}", type_="ERROR")
    
    async def refresh_server_list():
        """Refresh the server dropdown with current guilds"""
        try:
            servers_list = []
            
            for guild in bot.guilds:
                try:
                    icon_url = guild.icon.url if guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png"
                    servers_list.append({
                        "id": str(guild.id),
                        "title": guild.name,
                        "iconUrl": icon_url
                    })
                except Exception as e:
                    print(f"Error processing guild {guild.name}: {e}", type_="ERROR")
            
            if servers_list:
                ui_refs['server_select'].items = servers_list
                print(f"Loaded {len(servers_list)} servers", type_="INFO")
            else:
                ui_refs['server_select'].items = [{"id": "none", "title": "No servers available"}]
            
        except Exception as e:
            print(f"Error refreshing server list: {e}", type_="ERROR")
            ui_refs['server_select'].items = [{"id": "error", "title": "Error loading servers"}]
    
    async def refresh_channel_list(guild_id):
        """Refresh the channel dropdown for selected guild"""
        try:
            if not guild_id or guild_id == "none":
                ui_refs['channel_select'].items = [{"id": "none", "title": "Select a server first"}]
                ui_refs['channel_select'].visible = False
                return
            
            guild = bot.get_guild(int(guild_id))
            if not guild:
                ui_refs['channel_select'].items = [{"id": "none", "title": "Guild not found"}]
                ui_refs['channel_select'].visible = False
                return
            
            voice_channels = [ch for ch in guild.channels if hasattr(ch, 'user_limit')]
            channel_items = []
            
            for channel in voice_channels:
                try:
                    member_count = len(channel.members) if hasattr(channel, 'members') else 0
                    user_limit = channel.user_limit if channel.user_limit > 0 else "∞"
                    
                    channel_items.append({
                        "id": str(channel.id),
                        "title": f"{channel.name} ({member_count}/{user_limit})"
                    })
                except Exception as e:
                    print(f"Error processing channel {channel.name}: {e}", type_="ERROR")
            
            if channel_items:
                ui_refs['channel_select'].items = channel_items
                ui_refs['channel_select'].visible = True
            else:
                ui_refs['channel_select'].items = [{"id": "none", "title": "No voice channels available"}]
                ui_refs['channel_select'].visible = True
            
        except Exception as e:
            print(f"Error refreshing channel list: {e}", type_="ERROR")
            ui_refs['channel_select'].items = [{"id": "none", "title": "Error loading channels"}]
            ui_refs['channel_select'].visible = False
    
    # ==================== VOICE CONNECTION ====================
    async def connect(guild_id, channel_id):
        """Connect to voice channel"""
        payload = {
            "op": 4,
            "d": {
                "guild_id": guild_id,
                "channel_id": channel_id,
                "self_mute": is_muted,
                "self_deaf": is_deafened
            }
        }
        await bot.ws.send(json.dumps(payload))
    
    async def update_voice_state(mute=None, deafen=None, stream=None, camera=None):
        """Update voice state (mute/deafen/stream/camera)"""
        nonlocal is_muted, is_deafened, is_streaming, is_camera_on
        
        if not active_channel:
            return False
        
        if mute is not None:
            is_muted = mute
        if deafen is not None:
            is_deafened = deafen
        if stream is not None:
            is_streaming = stream
        if camera is not None:
            is_camera_on = camera
        
        payload = {
            "op": 4,
            "d": {
                "guild_id": str(active_channel.guild.id),
                "channel_id": str(active_channel.id),
                "self_mute": is_muted,
                "self_deaf": is_deafened,
                "self_video": is_camera_on
            }
        }
        await bot.ws.send(json.dumps(payload))
        
        # Handle streaming separately if needed
        if stream is not None:
            stream_payload = {
                "op": 18,
                "d": {
                    "type": "guild",
                    "guild_id": str(active_channel.guild.id),
                    "channel_id": str(active_channel.id),
                    "preferred_region": None
                }
            }
            if is_streaming:
                await bot.ws.send(json.dumps(stream_payload))
        
        # Update saved settings
        data = load_data()
        data["settings"]["muted"] = is_muted
        data["settings"]["deafened"] = is_deafened
        save_data(data)
        
        # Update UI
        update_all_ui()
        
        return True
    
    async def check_if_connect_success(msg, delay, error_message):
        """Check if connection was successful"""
        await asyncio.sleep(delay)
        if temp.get('from', None):
            await msg.edit(f"> {error_message}", delete_after=delete_after())
    
    # ==================== EVENT LISTENERS ====================
    @bot.listen("on_voice_state_update")
    async def on_voice_state_update(member, before, after):
        nonlocal active_channel, temp, connection_start_time, stats_update_task
        
        if member.id != bot.user.id:
            return
        
        # Filter if this is the selfbot
        if active_channel:
            if before.channel and active_channel.id != before.channel.id:
                return
        else:
            if not temp.get('from', None):
                return
        
        channel_id = after.channel.id if after.channel else None
        
        try:
            # Update session stats before leaving
            if before.channel and not after.channel:
                update_session_stats()
            
            active_channel = await bot.fetch_channel(channel_id) if channel_id else None
            message = temp.get('msg')
            _type = temp.get('type')
            _from = temp.get('from')
            
            if _type == 'join':
                connection_start_time = datetime.now()
                
                # Schedule auto-disconnect if configured
                data = load_data()
                auto_disconnect = data["settings"].get("auto_disconnect_minutes")
                if auto_disconnect:
                    await schedule_disconnect(auto_disconnect)
                
                # Start live stats update
                if stats_update_task:
                    stats_update_task.cancel()
                stats_update_task = asyncio.create_task(live_update_stats())
                
                # Update UI
                update_all_ui()
                
                if _from == 'command' and message is not None:
                    # Disable private mode temporarily for embed
                    current_private = getConfigData().get("private")
                    updateConfigData("private", False)
                    
                    try:
                        await forwardEmbedMethod(
                            channel_id=message.channel.id,
                            content=f"# Voice Connected\n\n**Channel:** {after.channel.name}\n**Server:** {after.channel.guild.name}\n**Status:** {'Deafened' if is_deafened else 'Listening'} | {'Muted' if is_muted else 'Unmuted'}",
                            title="VC Manager"
                        )
                    finally:
                        updateConfigData("private", current_private)
                    
                    await message.delete()
                
                temp = {}
                
            elif _type == 'leave':
                connection_start_time = None
                channel_name = before.channel.name if before.channel else "voice channel"
                
                # Reset all voice states to OFF
                is_muted = False
                is_deafened = False
                is_streaming = False
                is_camera_on = False
                
                # Cancel disconnect timer and stats update
                if disconnect_task:
                    disconnect_task.cancel()
                if stats_update_task:
                    stats_update_task.cancel()
                
                # Update UI
                update_all_ui()
                
                if _from == 'command' and message is not None:
                    # Disable private mode temporarily for embed
                    current_private = getConfigData().get("private")
                    updateConfigData("private", False)
                    
                    try:
                        await forwardEmbedMethod(
                            channel_id=message.channel.id,
                            content=f"# ❌ Voice Disconnected\n\n**Channel:** {channel_name}\n**Session Duration:** {format_duration(get_current_session_duration())}",
                            title="VC Manager"
                        )
                    finally:
                        updateConfigData("private", current_private)
                    
                    await message.delete()
                
                temp = {}
                
        except Exception as e:
            print(f"Error in voice state update: {e}", type_="ERROR")
    
    # ==================== COMMANDS ====================
    @bot.command(
        name="vcstream",
        description="Toggle fake screen share/stream"
    )
    async def vc_stream(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not active_channel:
            await ctx.send('> ❌ Not connected to any voice channel', delete_after=delete_after())
            return
        
        nonlocal is_streaming
        is_streaming = not is_streaming
        
        success = await update_voice_state(stream=is_streaming)
        if success:
            await ctx.send(f'> {"📺 Started streaming" if is_streaming else "⏹️ Stopped streaming"}', delete_after=delete_after())
        else:
            await ctx.send('> ❌ Failed to toggle stream', delete_after=delete_after())
    
    @bot.command(
        name="vccamera",
        description="Toggle fake camera"
    )
    async def vc_camera(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not active_channel:
            await ctx.send('> ❌ Not connected to any voice channel', delete_after=delete_after())
            return
        
        nonlocal is_camera_on
        is_camera_on = not is_camera_on
        
        success = await update_voice_state(camera=is_camera_on)
        if success:
            await ctx.send(f'> {"📹 Camera enabled" if is_camera_on else "📷 Camera disabled"}', delete_after=delete_after())
        else:
            await ctx.send('> ❌ Failed to toggle camera', delete_after=delete_after())
    
    @bot.command(
        name="fakejoinvc",
        description="Join a voice channel by channel ID"
    )
    async def fake_join_vc(ctx, *, args: str):
        await ctx.message.delete()
        
        if not args.strip():
            await ctx.send(f'> Usage: `{await bot.get_prefix(ctx.message)}fakejoinvc <channel_id>`', delete_after=delete_after())
            return
        
        channel_id = args.strip()
        try:
            channel = await bot.fetch_channel(int(channel_id))
        except:
            await ctx.send('> ❌ Invalid channel ID', delete_after=delete_after())
            return
        
        if not isinstance(channel, discord.VoiceChannel):
            await ctx.send('> ❌ Channel is not a voice channel', delete_after=delete_after())
            return
        
        temp['type'] = 'join'
        temp['from'] = 'command'
        temp['msg'] = await ctx.send(f'> 🔄 Connecting to `{channel.name}`...')
        
        await connect(str(channel.guild.id), str(channel.id))
        asyncio.create_task(check_if_connect_success(temp['msg'], 10, "❌ Failed to connect"))
    
    @bot.command(
        name="fakeleavevc",
        description="Leave current voice channel"
    )
    async def fake_leave_vc(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not active_channel:
            await ctx.send('> ❌ Not connected to any voice channel', delete_after=delete_after())
            return
        
        temp['type'] = 'leave'
        temp['from'] = 'command'
        temp['msg'] = await ctx.send('> 🔄 Disconnecting from voice channel...')
        
        await connect(None, None)
        asyncio.create_task(check_if_connect_success(temp['msg'], 10, "❌ Failed to disconnect"))
    
    @bot.command(
        name="vcdeafen",
        description="Deafen yourself in voice channel"
    )
    async def vc_deafen(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not active_channel:
            await ctx.send('> ❌ Not connected to any voice channel', delete_after=delete_after())
            return
        
        success = await update_voice_state(deafen=True)
        if success:
            await ctx.send('> 🔇 Deafened', delete_after=delete_after())
        else:
            await ctx.send('> ❌ Failed to deafen', delete_after=delete_after())
    
    @bot.command(
        name="vcundeafen",
        description="Undeafen yourself in voice channel"
    )
    async def vc_undeafen(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not active_channel:
            await ctx.send('> ❌ Not connected to any voice channel', delete_after=delete_after())
            return
        
        success = await update_voice_state(deafen=False)
        if success:
            await ctx.send('> 🔊 Undeafened', delete_after=delete_after())
        else:
            await ctx.send('> ❌ Failed to undeafen', delete_after=delete_after())
    
    @bot.command(
        name="vcmute",
        description="Mute yourself in voice channel"
    )
    async def vc_mute(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not active_channel:
            await ctx.send('> ❌ Not connected to any voice channel', delete_after=delete_after())
            return
        
        success = await update_voice_state(mute=True)
        if success:
            await ctx.send('> 🔇 Muted', delete_after=delete_after())
        else:
            await ctx.send('> ❌ Failed to mute', delete_after=delete_after())
    
    @bot.command(
        name="vcunmute",
        description="Unmute yourself in voice channel"
    )
    async def vc_unmute(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not active_channel:
            await ctx.send('> ❌ Not connected to any voice channel', delete_after=delete_after())
            return
        
        success = await update_voice_state(mute=False)
        if success:
            await ctx.send('> 🎤 Unmuted', delete_after=delete_after())
        else:
            await ctx.send('> ❌ Failed to unmute', delete_after=delete_after())
    
    @bot.command(
        name="vchelp",
        description="Show voice manager help menu"
    )
    async def voice_help(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        prefix = await bot.get_prefix(ctx.message)
        
        # Get current status
        current_channel = f"`{active_channel.name}`" if active_channel else "None"
        connection_duration = format_duration(get_current_session_duration()) if connection_start_time else "Not connected"
        
        # Get statistics
        data = load_data()
        total_time = format_duration(data["total_vc_time_seconds"])
        session_count = len(data["sessions"])
        
        # Voice state
        voice_state = []
        if active_channel:
            if is_deafened:
                voice_state.append("🔇 Deafened")
            else:
                voice_state.append("🔊 Listening")
            
            if is_muted:
                voice_state.append("🔇 Muted")
            else:
                voice_state.append("🎤 Unmuted")
        
        voice_status = " | ".join(voice_state) if voice_state else "N/A"
        
        help_text = f"""> **Voice Manager & Farm Help**
> 
> **Commands:**
> `{prefix}fakejoinvc <channel_id>` - Join a voice channel
> `{prefix}fakeleavevc` - Leave current voice channel
> `{prefix}vcdeafen` - Deafen yourself
> `{prefix}vcundeafen` - Undeafen yourself
> `{prefix}vcmute` - Mute yourself
> `{prefix}vcunmute` - Unmute yourself
> `{prefix}vcstream` - Toggle fake screen share
> `{prefix}vccamera` - Toggle fake camera
> `{prefix}vchelp` - Show this help menu
> 
> **Current Status:**
> Connected to: {current_channel}
> Session Duration: {connection_duration}
> Voice State: {voice_status}
> 
> **Statistics:**
> Total VC Time: {total_time}
> Total Sessions: {session_count}"""
        
        await ctx.send(help_text, delete_after=delete_after())
    
    # ==================== UI TAB ====================
    tab = Tab(
        title="VC Manager",
        name="VC Manager", 
        icon="users", 
        gap=6
    )
    
    # Main container (columns layout)
    main_container = tab.create_container(type="columns", gap=6)
    
    # Left column - Connection & Browser
    left_container = main_container.create_container(type="rows", width="auto", gap=6)
    
    # Connection Card
    connection_card = left_container.create_card(type="rows", gap=4)
    connection_card.create_ui_element(UI.Text, content="Voice Connection", size="xl", weight="bold")
    
    # Connection mode toggle
    connection_mode_group = connection_card.create_group(type="columns", gap=2)
    connection_mode_group.create_ui_element(UI.Text, content="Connection Method:", size="sm", weight="medium")
    
    use_channel_id_toggle = connection_card.create_ui_element(
        UI.Toggle,
        label="Use Channel ID directly",
        checked=False
    )
    ui_refs['use_channel_id_toggle'] = use_channel_id_toggle
    
    # Server selection dropdown
    server_select = connection_card.create_ui_element(
        UI.Select,
        label="Select Server",
        items=[{"id": "loading", "title": "Loading servers..."}],
        mode="single",
        full_width=True
    )
    ui_refs['server_select'] = server_select
    
    # Channel selection dropdown (hidden by default)
    channel_select = connection_card.create_ui_element(
        UI.Select,
        label="Select Voice Channel",
        items=[{"id": "none", "title": "Select a server first"}],
        mode="single",
        full_width=True,
        visible=False
    )
    ui_refs['channel_select'] = channel_select
    
    # Channel ID input (hidden by default)
    channel_id_input = connection_card.create_ui_element(
        UI.Input,
        label="Channel ID",
        placeholder="Enter voice channel ID...",
        full_width=True,
        visible=False
    )
    ui_refs['channel_id_input'] = channel_id_input
    
    # Connection buttons
    button_group = connection_card.create_group(type="columns", gap=2)
    join_button = button_group.create_ui_element(
        UI.Button,
        label="Connect",
        variant="cta",
        color="success"
    )
    leave_button = button_group.create_ui_element(
        UI.Button,
        label="Disconnect",
        variant="bordered",
        color="danger"
    )
    refresh_list_button = button_group.create_ui_element(
        UI.Button,
        label="↻",
        variant="ghost",
        color="default"
    )
    
    # Status Card
    status_card = left_container.create_card(type="rows", gap=3)
    status_card.create_ui_element(UI.Text, content="Connection Status", size="lg", weight="bold")
    
    status_text = status_card.create_ui_element(
        UI.Text,
        content="Status: 🔴 Disconnected",
        size="base",
        color="#FF0000"
    )
    ui_refs['status_text'] = status_text
    
    guild_name_text = status_card.create_ui_element(
        UI.Text,
        content="Server: None",
        size="sm",
        color="#888888"
    )
    ui_refs['guild_name_text'] = guild_name_text
    
    channel_name_text = status_card.create_ui_element(
        UI.Text,
        content="Channel: None",
        size="sm",
        color="#888888"
    )
    ui_refs['channel_name_text'] = channel_name_text
    
    channel_id_text = status_card.create_ui_element(
        UI.Text,
        content="Channel ID: None",
        size="sm",
        color="#888888"
    )
    ui_refs['channel_id_text'] = channel_id_text
    
    # Right column - Settings & Stats
    right_container = main_container.create_container(type="rows", gap=6)
    
    # Voice Settings Card
    settings_card = right_container.create_card(type="rows", gap=2)
    settings_card.create_ui_element(UI.Text, content="Voice Settings", size="lg", weight="bold")
    settings_card.create_ui_element(UI.Text, content="(Available when connected)", size="sm", color="#888888")
    
    # Create a compact group for toggles
    settings_group = settings_card.create_group(type="rows", gap=2)
    
    mute_toggle = settings_group.create_ui_element(
        UI.Toggle,
        label="Mute Microphone",
        checked=False,
        disabled=True
    )
    ui_refs['mute_toggle'] = mute_toggle
    
    deafen_toggle = settings_group.create_ui_element(
        UI.Toggle,
        label="Deafen Audio",
        checked=False,
        disabled=True
    )
    ui_refs['deafen_toggle'] = deafen_toggle
    
    stream_toggle = settings_group.create_ui_element(
        UI.Toggle,
        label="Screen Share / Stream",
        checked=False,
        disabled=True
    )
    ui_refs['stream_toggle'] = stream_toggle
    
    camera_toggle = settings_group.create_ui_element(
        UI.Toggle,
        label="Camera / Video",
        checked=False,
        disabled=True
    )
    ui_refs['camera_toggle'] = camera_toggle
    
    # Auto-Disconnect Timer Card
    timer_card = right_container.create_card(type="rows", gap=3)
    timer_card.create_ui_element(UI.Text, content="Auto-Disconnect Timer", size="lg", weight="bold")
    
    # Timer mode selection
    timer_mode_select = timer_card.create_ui_element(
        UI.Select,
        label="Timer Mode",
        items=[
            {"id": "none", "title": "None (Never disconnect)"},
            {"id": "minutes", "title": "Minutes"},
            {"id": "hours", "title": "Hours"},
            {"id": "days", "title": "Days"},
            {"id": "custom", "title": "Custom (seconds)"}
        ],
        selected_items=["none"],
        mode="single",
        full_width=True
    )
    ui_refs['timer_mode_select'] = timer_mode_select
    
    # Timer value selection (visible based on mode)
    timer_value_select = timer_card.create_ui_element(
        UI.Select,
        label="Select Time",
        items=[{"id": "1", "title": "1 minute"}],
        mode="single",
        full_width=True,
        visible=False
    )
    ui_refs['timer_value_select'] = timer_value_select
    
    # Custom time input (for custom mode)
    custom_time_input = timer_card.create_ui_element(
        UI.Input,
        label="Custom Time (seconds)",
        placeholder="Enter seconds...",
        full_width=True,
        visible=False
    )
    ui_refs['custom_time_input'] = custom_time_input
    
    # Apply timer button
    apply_timer_button = timer_card.create_ui_element(
        UI.Button,
        label="Apply Timer",
        variant="solid",
        color="primary",
        full_width=True
    )
    
    # Statistics Card
    stats_card = right_container.create_card(type="rows", gap=3)
    stats_card.create_ui_element(UI.Text, content="Statistics", size="xl", weight="bold")
    
    session_time_text = stats_card.create_ui_element(
        UI.Text,
        content="Session Time: 0s",
        size="base"
    )
    ui_refs['session_time_text'] = session_time_text
    
    total_time_text = stats_card.create_ui_element(
        UI.Text,
        content="Total VC Time: 0s",
        size="base"
    )
    ui_refs['total_time_text'] = total_time_text
    
    session_count_text = stats_card.create_ui_element(
        UI.Text,
        content="Total Sessions: 0",
        size="base"
    )
    ui_refs['session_count_text'] = session_count_text
    
    refresh_stats_button = stats_card.create_ui_element(
        UI.Button,
        label="Refresh Stats",
        variant="ghost",
        full_width=True,
        margin="mt-2"
    )
    
    # ==================== UI EVENT HANDLERS ====================
    async def live_update_stats():
        """Continuously update stats while connected"""
        while active_channel:
            try:
                await asyncio.sleep(1)  # Update every second
                if active_channel:
                    session_duration = get_current_session_duration()
                    ui_refs['session_time_text'].content = f"Session Time: {format_duration(session_duration)}"
                    
                    # Also update total time (includes current session)
                    data = load_data()
                    total_with_current = data["total_vc_time_seconds"] + session_duration
                    ui_refs['total_time_text'].content = f"Total VC Time: {format_duration(total_with_current)}"
            except Exception as e:
                print(f"Error in live stats update: {e}", type_="ERROR")
                break
    
    async def handle_connection_mode_toggle(checked):
        """Handle toggle between server/channel selection and channel ID input"""
        try:
            if checked:
                # Use channel ID mode
                ui_refs['server_select'].visible = False
                ui_refs['channel_select'].visible = False
                ui_refs['channel_id_input'].visible = True
            else:
                # Use server/channel selection mode
                ui_refs['server_select'].visible = True
                ui_refs['channel_id_input'].visible = False
                # Show channel select if server is selected
                if ui_refs['server_select'].selected_items and ui_refs['server_select'].selected_items[0] not in ["loading", "none", "error"]:
                    ui_refs['channel_select'].visible = True
        except Exception as e:
            print(f"Error handling connection mode toggle: {e}", type_="ERROR")
    
    async def handle_server_select(selected_items):
        """Handle server selection from dropdown"""
        try:
            if not selected_items or selected_items[0] in ["loading", "none", "error"]:
                ui_refs['channel_select'].visible = False
                return
            
            guild_id = selected_items[0]
            await refresh_channel_list(guild_id)
            
        except Exception as e:
            print(f"Error handling server selection: {e}", type_="ERROR")
            tab.toast("Error", "Failed to load channels", "ERROR")
    
    async def handle_join():
        """Handle join button click"""
        nonlocal active_channel, connection_start_time, temp, stats_update_task
        
        # Check which mode we're in
        use_id_mode = ui_refs['use_channel_id_toggle'].checked
        
        if use_id_mode:
            # Use channel ID input
            channel_id = ui_refs['channel_id_input'].value
            if not channel_id or not channel_id.strip():
                tab.toast("Error", "Please enter a channel ID", "ERROR")
                return
            channel_id = channel_id.strip()
        else:
            # Use dropdown selection
            selected_channels = ui_refs['channel_select'].selected_items
            if not selected_channels or selected_channels[0] == "none":
                tab.toast("Error", "Please select a voice channel", "ERROR")
                return
            channel_id = selected_channels[0]
        
        join_button.loading = True
        
        try:
            channel = await bot.fetch_channel(int(channel_id))
            
            if not isinstance(channel, discord.VoiceChannel):
                tab.toast("Error", "Selected channel is not a voice channel", "ERROR")
                join_button.loading = False
                return
            
            temp['type'] = 'join'
            temp['from'] = 'ui'
            
            await connect(str(channel.guild.id), str(channel.id))
            
            # Wait for connection
            await asyncio.sleep(2)
            
            if active_channel:
                connection_start_time = datetime.now()
                
                # Schedule auto-disconnect if configured
                data = load_data()
                auto_disconnect = data["settings"].get("auto_disconnect_minutes")
                if auto_disconnect:
                    await schedule_disconnect(auto_disconnect)
                
                # Start live stats update
                if stats_update_task:
                    stats_update_task.cancel()
                stats_update_task = asyncio.create_task(live_update_stats())
                
                update_all_ui()
                tab.toast("Success", f"Connected to {channel.name}", "SUCCESS")
            else:
                tab.toast("Error", "Failed to connect to voice channel", "ERROR")
            
        except Exception as e:
            tab.toast("Error", f"Failed to join: {str(e)}", "ERROR")
            print(f"Error joining VC from UI: {e}", type_="ERROR")
        finally:
            join_button.loading = False
            temp = {}
    
    async def handle_leave():
        """Handle leave button click"""
        nonlocal active_channel, connection_start_time, temp, stats_update_task, is_muted, is_deafened, is_streaming, is_camera_on
        
        if not active_channel:
            tab.toast("Error", "Not connected to any voice channel", "ERROR")
            return
        
        leave_button.loading = True
        
        try:
            temp['type'] = 'leave'
            temp['from'] = 'ui'
            
            # Update stats before leaving
            update_session_stats()
            
            await connect(None, None)
            
            # Wait for disconnection
            await asyncio.sleep(2)
            
            active_channel = None
            connection_start_time = None
            
            # Reset all voice states to OFF
            is_muted = False
            is_deafened = False
            is_streaming = False
            is_camera_on = False
            
            # Cancel disconnect timer and stats update
            if disconnect_task:
                disconnect_task.cancel()
            if stats_update_task:
                stats_update_task.cancel()
            
            update_all_ui()
            tab.toast("Success", "Disconnected from voice channel", "SUCCESS")
            
        except Exception as e:
            tab.toast("Error", f"Failed to leave: {str(e)}", "ERROR")
            print(f"Error leaving VC from UI: {e}", type_="ERROR")
        finally:
            leave_button.loading = False
            temp = {}
    
    async def handle_refresh_list():
        """Handle refresh button click"""
        refresh_list_button.loading = True
        try:
            await refresh_server_list()
            tab.toast("Success", "Server list refreshed", "SUCCESS")
        except Exception as e:
            tab.toast("Error", f"Failed to refresh: {str(e)}", "ERROR")
        finally:
            refresh_list_button.loading = False
    
    async def handle_mute_toggle(checked):
        """Handle mute toggle"""
        if not active_channel:
            ui_refs['mute_toggle'].checked = not checked
            tab.toast("Error", "Not connected to any voice channel", "ERROR")
            return
        
        success = await update_voice_state(mute=checked)
        if success:
            tab.toast("Success", f"{'Muted' if checked else 'Unmuted'} microphone", "SUCCESS")
        else:
            ui_refs['mute_toggle'].checked = not checked
            tab.toast("Error", "Failed to update mute state", "ERROR")
    
    async def handle_deafen_toggle(checked):
        """Handle deafen toggle"""
        if not active_channel:
            ui_refs['deafen_toggle'].checked = not checked
            tab.toast("Error", "Not connected to any voice channel", "ERROR")
            return
        
        success = await update_voice_state(deafen=checked)
        if success:
            tab.toast("Success", f"{'Deafened' if checked else 'Undeafened'} audio", "SUCCESS")
        else:
            ui_refs['deafen_toggle'].checked = not checked
            tab.toast("Error", "Failed to update deafen state", "ERROR")
    
    async def handle_stream_toggle(checked):
        """Handle stream toggle"""
        if not active_channel:
            ui_refs['stream_toggle'].checked = not checked
            tab.toast("Error", "Not connected to any voice channel", "ERROR")
            return
        
        success = await update_voice_state(stream=checked)
        if success:
            tab.toast("Success", f"{'Started' if checked else 'Stopped'} screen share", "SUCCESS")
        else:
            ui_refs['stream_toggle'].checked = not checked
            tab.toast("Error", "Failed to toggle stream", "ERROR")
    
    async def handle_camera_toggle(checked):
        """Handle camera toggle"""
        if not active_channel:
            ui_refs['camera_toggle'].checked = not checked
            tab.toast("Error", "Not connected to any voice channel", "ERROR")
            return
        
        success = await update_voice_state(camera=checked)
        if success:
            tab.toast("Success", f"Camera {'enabled' if checked else 'disabled'}", "SUCCESS")
        else:
            ui_refs['camera_toggle'].checked = not checked
            tab.toast("Error", "Failed to toggle camera", "ERROR")
    
    async def handle_timer_mode_change(selected_items):
        """Handle timer mode selection"""
        try:
            if not selected_items:
                return
            
            mode = selected_items[0]
            
            # Hide all timer inputs first
            ui_refs['timer_value_select'].visible = False
            ui_refs['custom_time_input'].visible = False
            
            if mode == "none":
                # No timer - disable auto-disconnect
                pass
            elif mode == "minutes":
                # Show minute options
                ui_refs['timer_value_select'].label = "Select Minutes"
                ui_refs['timer_value_select'].items = [
                    {"id": "1", "title": "1 minute"},
                    {"id": "5", "title": "5 minutes"},
                    {"id": "10", "title": "10 minutes"},
                    {"id": "15", "title": "15 minutes"},
                    {"id": "20", "title": "20 minutes"},
                    {"id": "25", "title": "25 minutes"},
                    {"id": "30", "title": "30 minutes"},
                    {"id": "45", "title": "45 minutes"},
                    {"id": "60", "title": "60 minutes"}
                ]
                ui_refs['timer_value_select'].visible = True
            elif mode == "hours":
                # Show hour options
                ui_refs['timer_value_select'].label = "Select Hours"
                ui_refs['timer_value_select'].items = [
                    {"id": "60", "title": "1 hour"},
                    {"id": "120", "title": "2 hours"},
                    {"id": "180", "title": "3 hours"},
                    {"id": "240", "title": "4 hours"},
                    {"id": "300", "title": "5 hours"},
                    {"id": "360", "title": "6 hours"},
                    {"id": "480", "title": "8 hours"},
                    {"id": "720", "title": "12 hours"}
                ]
                ui_refs['timer_value_select'].visible = True
            elif mode == "days":
                # Show day options
                ui_refs['timer_value_select'].label = "Select Days"
                ui_refs['timer_value_select'].items = [
                    {"id": "1440", "title": "1 day"},
                    {"id": "2880", "title": "2 days"},
                    {"id": "4320", "title": "3 days"},
                    {"id": "5760", "title": "4 days"},
                    {"id": "7200", "title": "5 days"},
                    {"id": "8640", "title": "6 days"},
                    {"id": "10080", "title": "7 days"}
                ]
                ui_refs['timer_value_select'].visible = True
            elif mode == "custom":
                # Show custom input
                ui_refs['custom_time_input'].visible = True
            
        except Exception as e:
            print(f"Error handling timer mode change: {e}", type_="ERROR")
            tab.toast("Error", "Failed to update timer options", "ERROR")
    
    async def handle_apply_timer():
        """Handle apply timer button"""
        apply_timer_button.loading = True
        
        try:
            selected_mode = ui_refs['timer_mode_select'].selected_items
            if not selected_mode:
                tab.toast("Error", "Please select a timer mode", "ERROR")
                apply_timer_button.loading = False
                return
            
            mode = selected_mode[0]
            
            if mode == "none":
                # Disable timer
                data = load_data()
                data["settings"]["auto_disconnect_minutes"] = None
                save_data(data)
                
                if disconnect_task:
                    disconnect_task.cancel()
                
                tab.toast("Success", "Auto-disconnect disabled", "SUCCESS")
            
            elif mode == "custom":
                # Get custom seconds
                custom_value = ui_refs['custom_time_input'].value
                if not custom_value or not custom_value.strip():
                    tab.toast("Error", "Please enter a time in seconds", "ERROR")
                    apply_timer_button.loading = False
                    return
                
                try:
                    seconds = int(custom_value.strip())
                    if seconds <= 0:
                        tab.toast("Error", "Time must be greater than 0", "ERROR")
                        apply_timer_button.loading = False
                        return
                    
                    minutes = seconds / 60
                    
                    # Save timer setting
                    data = load_data()
                    data["settings"]["auto_disconnect_minutes"] = minutes
                    save_data(data)
                    
                    # Schedule if currently connected
                    if active_channel:
                        await schedule_disconnect(minutes)
                    
                    tab.toast("Success", f"Auto-disconnect set to {seconds} seconds", "SUCCESS")
                
                except ValueError:
                    tab.toast("Error", "Invalid number format", "ERROR")
            
            else:
                # Get value from dropdown
                selected_value = ui_refs['timer_value_select'].selected_items
                if not selected_value:
                    tab.toast("Error", "Please select a time value", "ERROR")
                    apply_timer_button.loading = False
                    return
                
                minutes = float(selected_value[0])
                
                # Save timer setting
                data = load_data()
                data["settings"]["auto_disconnect_minutes"] = minutes
                save_data(data)
                
                # Schedule if currently connected
                if active_channel:
                    await schedule_disconnect(minutes)
                
                # Format display message
                if minutes < 60:
                    time_str = f"{int(minutes)} minute{'s' if minutes != 1 else ''}"
                elif minutes < 1440:
                    hours = int(minutes / 60)
                    time_str = f"{hours} hour{'s' if hours != 1 else ''}"
                else:
                    days = int(minutes / 1440)
                    time_str = f"{days} day{'s' if days != 1 else ''}"
                
                tab.toast("Success", f"Auto-disconnect set to {time_str}", "SUCCESS")
        
        except Exception as e:
            tab.toast("Error", f"Failed to set timer: {str(e)}", "ERROR")
            print(f"Error setting timer: {e}", type_="ERROR")
        finally:
            apply_timer_button.loading = False
    
    def handle_refresh_stats():
        """Handle refresh stats button"""
        update_all_ui()
        tab.toast("Success", "Statistics refreshed", "SUCCESS")
    
    # Assign event handlers
    use_channel_id_toggle.onChange = handle_connection_mode_toggle
    server_select.onChange = handle_server_select
    join_button.onClick = handle_join
    leave_button.onClick = handle_leave
    refresh_list_button.onClick = handle_refresh_list
    mute_toggle.onChange = handle_mute_toggle
    deafen_toggle.onChange = handle_deafen_toggle
    stream_toggle.onChange = handle_stream_toggle
    camera_toggle.onChange = handle_camera_toggle
    timer_mode_select.onChange = handle_timer_mode_change
    apply_timer_button.onClick = handle_apply_timer
    refresh_stats_button.onClick = handle_refresh_stats
    
    # Initialize UI with current state (sync function)
    def initialize_ui_sync():
        """Initialize UI with current data synchronously"""
        try:
            # Update all UI elements with current state
            update_all_ui()
            
            print("VC Manager Enhanced UI initialized successfully", type_="SUCCESS")
        except Exception as e:
            print(f"Error initializing UI: {e}", type_="ERROR")
    
    # Add event listener to refresh server list when ready
    @bot.listen("on_ready")
    async def on_bot_ready():
        """Load server list once bot is ready"""
        try:
            # Small delay to ensure bot is fully ready
            await asyncio.sleep(2)
            await refresh_server_list()
            update_all_ui()
            print("Server list loaded successfully", type_="SUCCESS")
        except Exception as e:
            print(f"Error loading initial server list: {e}", type_="ERROR")
    
    # Initialize UI synchronously
    initialize_ui_sync()
    
    # Load server list immediately (synchronously)
    servers_list = []
    for guild in bot.guilds:
        try:
            icon_url = guild.icon.url if guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png"
            servers_list.append({
                "id": str(guild.id),
                "title": guild.name,
                "iconUrl": icon_url
            })
        except Exception as e:
            print(f"Error processing guild {guild.name}: {e}", type_="ERROR")
    
    if servers_list:
        server_select.items = servers_list
        print(f"Loaded {len(servers_list)} servers on initialization", type_="INFO")
    else:
        server_select.items = [{"id": "none", "title": "No servers available"}]
    
    # Render the tab
    tab.render()
    
    print("VC Manager & Farm script loaded successfully", type_="SUCCESS")

# Initialize the script
vc_manager_farm_script()
