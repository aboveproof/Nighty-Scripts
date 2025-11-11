import json
import asyncio
from pathlib import Path
from datetime import datetime

def vc_manager_script():
    
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
    
    active_channel = None
    connection_start_time = None
    disconnect_task = None
    stats_update_task = None
    temp = {}
    is_muted = False
    is_deafened = False
    is_streaming = False
    is_camera_on = False
    
    ui_refs = {}
    
    # ==================== DATA MANAGEMENT ====================
    def load_data():
        try:
            if VC_DATA_PATH.exists():
                with open(VC_DATA_PATH, 'r') as f:
                    return json.load(f)
            else:
                save_data(DEFAULT_DATA)
                return DEFAULT_DATA
        except Exception as e:
            print(f"[VC Manager] Error loading data: {e}", type_="ERROR")
            return DEFAULT_DATA
    
    def save_data(data):
        try:
            with open(VC_DATA_PATH, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[VC Manager] Error saving data: {e}", type_="ERROR")
    
    # ==================== UTILITY FUNCTIONS ====================
    def format_duration(seconds):
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
        if connection_start_time is None:
            return 0
        return (datetime.now() - connection_start_time).total_seconds()
    
    def is_actually_connected():
        nonlocal active_channel
        
        if not active_channel:
            return False
        
        try:
            guild = active_channel.guild
            if not guild:
                return False
            
            member = guild.get_member(bot.user.id)
            if not member:
                return False
            
            if not member.voice:
                return False
            
            if not member.voice.channel:
                return False
            
            return member.voice.channel.id == active_channel.id
            
        except Exception as e:
            print(f"[VC Manager] Error checking connection: {e}", type_="ERROR")
            return False
    
    def update_session_stats():
        nonlocal connection_start_time, active_channel
        
        if connection_start_time is None or not active_channel:
            return
        
        data = load_data()
        session_duration = get_current_session_duration()
        
        data["total_vc_time_seconds"] += session_duration
        
        session_record = {
            "channel_id": str(active_channel.id),
            "channel_name": active_channel.name,
            "guild_name": active_channel.guild.name if active_channel.guild else "Unknown",
            "start_time": connection_start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": session_duration
        }
        
        data["sessions"].append(session_record)
        
        if len(data["sessions"]) > 100:
            data["sessions"] = data["sessions"][-100:]
        
        save_data(data)
    
    async def schedule_disconnect(minutes):
        nonlocal disconnect_task
        
        if disconnect_task:
            disconnect_task.cancel()
        
        if minutes is None or minutes <= 0:
            return
        
        async def disconnect_timer():
            try:
                await asyncio.sleep(minutes * 60)
                if active_channel:
                    print(f"[VC Manager] Auto-disconnect timer expired", type_="INFO")
                    await connect(None, None)
            except asyncio.CancelledError:
                pass
        
        disconnect_task = asyncio.create_task(disconnect_timer())
    
    # ==================== UI UPDATE FUNCTIONS ====================
    def update_all_ui():
        nonlocal active_channel, connection_start_time, is_muted, is_deafened, is_streaming, is_camera_on
        
        try:
            actually_connected = is_actually_connected()
            
            if actually_connected and active_channel:
                ui_refs['status_text'].content = "Status: 🟢 Connected"
                ui_refs['status_text'].color = "#00FF00"
                ui_refs['channel_name_text'].content = f"Channel: {active_channel.name}"
                ui_refs['channel_id_text'].content = f"Channel ID: {active_channel.id}"
                ui_refs['guild_name_text'].content = f"Server: {active_channel.guild.name if active_channel.guild else 'Unknown'}"
                
                session_duration = get_current_session_duration()
                ui_refs['session_time_text'].content = f"Session Time: {format_duration(session_duration)}"
                
                ui_refs['mute_toggle'].disabled = False
                ui_refs['deafen_toggle'].disabled = False
                ui_refs['stream_toggle'].disabled = False
                ui_refs['camera_toggle'].disabled = False
                
                ui_refs['mute_toggle'].checked = is_muted
                ui_refs['deafen_toggle'].checked = is_deafened
                ui_refs['stream_toggle'].checked = is_streaming
                ui_refs['camera_toggle'].checked = is_camera_on
            else:
                ui_refs['status_text'].content = "Status: 🔴 Disconnected"
                ui_refs['status_text'].color = "#FF0000"
                ui_refs['channel_name_text'].content = "Channel: None"
                ui_refs['channel_id_text'].content = "Channel ID: None"
                ui_refs['guild_name_text'].content = "Server: None"
                ui_refs['session_time_text'].content = "Session Time: 0s"
                
                ui_refs['mute_toggle'].disabled = True
                ui_refs['deafen_toggle'].disabled = True
                ui_refs['stream_toggle'].disabled = True
                ui_refs['camera_toggle'].disabled = True
                ui_refs['mute_toggle'].checked = False
                ui_refs['deafen_toggle'].checked = False
                ui_refs['stream_toggle'].checked = False
                ui_refs['camera_toggle'].checked = False
            
            data = load_data()
            ui_refs['total_time_text'].content = f"Total VC Time: {format_duration(data['total_vc_time_seconds'])}"
            ui_refs['session_count_text'].content = f"Total Sessions: {len(data['sessions'])}"
            
        except Exception as e:
            print(f"[VC Manager] Error updating UI: {e}", type_="ERROR")
    
    async def refresh_server_list():
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
                    print(f"[VC Manager] Error processing guild {guild.name}: {e}", type_="ERROR")
            
            if servers_list:
                ui_refs['server_select'].items = servers_list
                print(f"[VC Manager] Loaded {len(servers_list)} servers", type_="INFO")
            else:
                ui_refs['server_select'].items = [{"id": "none", "title": "No servers available"}]
            
        except Exception as e:
            print(f"[VC Manager] Error refreshing server list: {e}", type_="ERROR")
            ui_refs['server_select'].items = [{"id": "error", "title": "Error loading servers"}]
    
    async def refresh_channel_list(guild_id):
        try:
            ui_refs['channel_select'].selected_items = []
            
            if not guild_id or guild_id in ["none", "loading", "error"]:
                ui_refs['channel_select'].items = [{"id": "none", "title": "Select a server first"}]
                ui_refs['channel_select'].visible = False
                return
            
            guild = bot.get_guild(int(guild_id))
            if not guild:
                ui_refs['channel_select'].items = [{"id": "none", "title": "Guild not found"}]
                ui_refs['channel_select'].visible = False
                return

            member = guild.get_member(bot.user.id)
            if not member:
                ui_refs['channel_select'].items = [{"id": "none", "title": "Perms check failed"}]
                ui_refs['channel_select'].visible = True
                print(f"[VC Manager] Could not find member in guild {guild.id} to check perms.", type_="ERROR")
                return
            
            voice_channels = [ch for ch in guild.channels if hasattr(ch, 'user_limit')]
            channel_items = []
            
            for channel in voice_channels:
                try:
                    permissions = channel.permissions_for(member)
                    if not permissions.connect:
                        continue

                    member_count = len(channel.members) if hasattr(channel, 'members') else 0
                    user_limit = channel.user_limit if channel.user_limit > 0 else "∞"
                    
                    channel_items.append({
                        "id": str(channel.id),
                        "title": f"{channel.name} ({member_count}/{user_limit})"
                    })
                except Exception as e:
                    print(f"[VC Manager] Error processing channel {channel.name}: {e}", type_="ERROR")
            
            if channel_items:
                ui_refs['channel_select'].items = channel_items
                ui_refs['channel_select'].visible = True
            else:
                ui_refs['channel_select'].items = [{"id": "none", "title": "No accessible VCs"}]
                ui_refs['channel_select'].visible = True
            
        except Exception as e:
            print(f"[VC Manager] Error refreshing channels: {e}", type_="ERROR")
            ui_refs['channel_select'].items = [{"id": "error", "title": "Error loading channels"}]
            ui_refs['channel_select'].visible = False
    
    # ==================== VOICE CONNECTION ====================
    async def connect(guild_id, channel_id):
        nonlocal is_muted, is_deafened
        
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
        nonlocal is_muted, is_deafened, is_streaming, is_camera_on, active_channel
        
        if not active_channel or not is_actually_connected():
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
        
        data = load_data()
        data["settings"]["muted"] = is_muted
        data["settings"]["deafened"] = is_deafened
        save_data(data)
        
        update_all_ui()
        return True
    
    # ==================== EVENT LISTENERS ====================
    async def handle_external_disconnect():
        nonlocal active_channel, connection_start_time, stats_update_task
        nonlocal is_muted, is_deafened, is_streaming, is_camera_on

        if not active_channel:
            return

        print("[VC Manager] Handling external disconnect. Resetting state.", type_="INFO")
        
        update_session_stats()

        active_channel = None
        connection_start_time = None
        is_muted = False
        is_deafened = False
        is_streaming = False
        is_camera_on = False
        
        if disconnect_task:
            disconnect_task.cancel()
        
        update_all_ui()
        temp.clear()

    @bot.listen("on_voice_state_update")
    async def on_voice_state_update(member, before, after):
        nonlocal active_channel, temp, connection_start_time, stats_update_task
        nonlocal is_muted, is_deafened, is_streaming, is_camera_on
        
        if member.id != bot.user.id:
            return
        
        if not temp.get('from') and not active_channel:
            return
        
        if active_channel and before.channel:
            if before.channel.id != active_channel.id and (not after.channel or after.channel.id != active_channel.id):
                return
        
        channel_id = after.channel.id if after.channel else None
        
        try:
            if before.channel and not after.channel and active_channel:
                update_session_stats()
            
            if channel_id:
                active_channel = await bot.fetch_channel(channel_id)
            else:
                active_channel = None
            
            _type = temp.get('type')
            _from = temp.get('from')
            
            if _type == 'join' and after.channel:
                connection_start_time = datetime.now()
                

                data = load_data()
                auto_disconnect = data["settings"].get("auto_disconnect_minutes")
                if auto_disconnect:
                    await schedule_disconnect(auto_disconnect)
                
                if stats_update_task:
                    stats_update_task.cancel()
                stats_update_task = asyncio.create_task(live_update_stats())
                
                update_all_ui()
                temp = {}
                
            elif _type == 'leave' and not after.channel:
                connection_start_time = None
                
                is_muted = False
                is_deafened = False
                is_streaming = False
                is_camera_on = False
                
                if disconnect_task:
                    disconnect_task.cancel()
                if stats_update_task:
                    stats_update_task.cancel()
                
                update_all_ui()
                temp = {}
                
        except Exception as e:
            print(f"[VC Manager] Error in voice state update: {e}", type_="ERROR")
    
    # ==================== UI EVENT HANDLERS ====================
    async def live_update_stats():
        nonlocal active_channel
        
        while active_channel and is_actually_connected():
            try:
                await asyncio.sleep(1)
                if active_channel and is_actually_connected():
                    session_duration = get_current_session_duration()
                    ui_refs['session_time_text'].content = f"Session Time: {format_duration(session_duration)}"
                    
                    data = load_data()
                    total_with_current = data["total_vc_time_seconds"] + session_duration
                    ui_refs['total_time_text'].content = f"Total VC Time: {format_duration(total_with_current)}"
            except Exception as e:
                print(f"[VC Manager] Error updating stats: {e}", type_="ERROR")
                break
        
        if active_channel:
            print("[VC Manager] Live stats loop detected an inconsistency. Resetting state.", type_="INFO")
            await handle_external_disconnect()
    
    async def handle_connection_mode_toggle(checked):
        try:
            if checked:
                ui_refs['server_select'].visible = False
                ui_refs['channel_select'].visible = False
                ui_refs['channel_id_input'].visible = True
            else:
                ui_refs['server_select'].visible = True
                ui_refs['channel_id_input'].visible = False
                if ui_refs['server_select'].selected_items and ui_refs['server_select'].selected_items[0] not in ["loading", "none", "error"]:
                    ui_refs['channel_select'].visible = True
        except Exception as e:
            print(f"[VC Manager] Error toggling mode: {e}", type_="ERROR")
    
    async def handle_server_select(selected_items):
        try:
            ui_refs['channel_select'].selected_items = []
            ui_refs['channel_select'].items = []
            ui_refs['channel_select'].visible = False
            
            if not selected_items or selected_items[0] in ["loading", "none", "error"]:
                ui_refs['channel_select'].items = [{"id": "none", "title": "Select a server first"}]
                return
            
            guild_id = selected_items[0]
            
            ui_refs['channel_select'].items = [{"id": "loading", "title": "Loading channels..."}]
            ui_refs['channel_select'].selected_items = []
            ui_refs['channel_select'].visible = True
            
            await refresh_channel_list(guild_id)
            
        except Exception as e:
            print(f"[VC Manager] Error handling server select: {e}", type_="ERROR")
            tab.toast("Error", "Failed to load channels", "ERROR")
    
    async def handle_join():
        nonlocal active_channel, connection_start_time, temp, stats_update_task
        
        use_id_mode = ui_refs['use_channel_id_toggle'].checked
        
        if use_id_mode:
            channel_id = ui_refs['channel_id_input'].value
            if not channel_id or not channel_id.strip():
                tab.toast("Error", "Enter a channel ID", "ERROR")
                return
            channel_id = channel_id.strip()
        else:
            selected_channels = ui_refs['channel_select'].selected_items
            if not selected_channels or selected_channels[0] in ["none", "loading"]:
                tab.toast("Error", "Select a voice channel", "ERROR")
                return
            channel_id = selected_channels[0]
        
        join_button.loading = True
        
        try:
            channel = await bot.fetch_channel(int(channel_id))
            
            if not hasattr(channel, 'user_limit'):
                tab.toast("Error", "Not a voice channel", "ERROR")
                join_button.loading = False
                return
            
            temp['type'] = 'join'
            temp['from'] = 'ui'
            
            await connect(str(channel.guild.id), str(channel.id))
            await asyncio.sleep(2)
            
            if active_channel and is_actually_connected():
                connection_start_time = datetime.now()
                
                data = load_data()
                auto_disconnect = data["settings"].get("auto_disconnect_minutes")
                if auto_disconnect:
                    await schedule_disconnect(auto_disconnect)
                
                if stats_update_task:
                    stats_update_task.cancel()
                stats_update_task = asyncio.create_task(live_update_stats())
                
                update_all_ui()
                tab.toast("Success", f"Connected to {channel.name}", "SUCCESS")
            else:
                tab.toast("Error", "Failed to connect", "ERROR")
            
        except Exception as e:
            tab.toast("Error", f"Connection failed: {str(e)}", "ERROR")
            print(f"[VC Manager] Join error: {e}", type_="ERROR")
        finally:
            join_button.loading = False
            temp = {}
    
    async def handle_leave():
        nonlocal active_channel, connection_start_time, temp, stats_update_task
        nonlocal is_muted, is_deafened, is_streaming, is_camera_on
        
        if not active_channel or not is_actually_connected():
            tab.toast("Error", "Not connected", "ERROR")
            return
        
        leave_button.loading = True
        
        try:
            temp['type'] = 'leave'
            temp['from'] = 'ui'
            
            update_session_stats()
            await connect(None, None)
            await asyncio.sleep(2)
            
            active_channel = None
            connection_start_time = None
            is_muted = False
            is_deafened = False
            is_streaming = False
            is_camera_on = False
            
            if disconnect_task:
                disconnect_task.cancel()
            if stats_update_task:
                stats_update_task.cancel()
            
            update_all_ui()
            tab.toast("Success", "Disconnected", "SUCCESS")
            
        except Exception as e:
            tab.toast("Error", f"Failed to leave: {str(e)}", "ERROR")
            print(f"[VC Manager] Leave error: {e}", type_="ERROR")
        finally:
            leave_button.loading = False
            temp = {}
    
    async def handle_refresh_list():
        refresh_list_button.loading = True
        try:
            await refresh_server_list()
            ui_refs['channel_select'].selected_items = []
            ui_refs['channel_select'].visible = False
            ui_refs['server_select'].selected_items = []
            tab.toast("Success", "Server list refreshed", "SUCCESS")
        except Exception as e:
            tab.toast("Error", f"Refresh failed: {str(e)}", "ERROR")
        finally:
            refresh_list_button.loading = False
    
    async def handle_mute_toggle(checked):
        if not active_channel or not is_actually_connected():
            ui_refs['mute_toggle'].checked = not checked
            tab.toast("Error", "Not connected", "ERROR")
            return
        
        success = await update_voice_state(mute=checked)
        if success:
            tab.toast("Success", f"{'Muted' if checked else 'Unmuted'}", "SUCCESS")
        else:
            ui_refs['mute_toggle'].checked = not checked
            tab.toast("Error", "Failed to toggle mute", "ERROR")
    
    async def handle_deafen_toggle(checked):
        if not active_channel or not is_actually_connected():
            ui_refs['deafen_toggle'].checked = not checked
            tab.toast("Error", "Not connected", "ERROR")
            return
        
        success = await update_voice_state(deafen=checked)
        if success:
            tab.toast("Success", f"{'Deafened' if checked else 'Undeafened'}", "SUCCESS")
        else:
            ui_refs['deafen_toggle'].checked = not checked
            tab.toast("Error", "Failed to toggle deafen", "ERROR")
    
    async def handle_stream_toggle(checked):
        if not active_channel or not is_actually_connected():
            ui_refs['stream_toggle'].checked = not checked
            tab.toast("Error", "Not connected", "ERROR")
            return
        
        success = await update_voice_state(stream=checked)
        if success:
            tab.toast("Success", f"Stream {'started' if checked else 'stopped'}", "SUCCESS")
        else:
            ui_refs['stream_toggle'].checked = not checked
            tab.toast("Error", "Failed to toggle stream", "ERROR")
    
    async def handle_camera_toggle(checked):
        if not active_channel or not is_actually_connected():
            ui_refs['camera_toggle'].checked = not checked
            tab.toast("Error", "Not connected", "ERROR")
            return
        
        success = await update_voice_state(camera=checked)
        if success:
            tab.toast("Success", f"Camera {'enabled' if checked else 'disabled'}", "SUCCESS")
        else:
            ui_refs['camera_toggle'].checked = not checked
            tab.toast("Error", "Failed to toggle camera", "ERROR")
    
    async def handle_timer_mode_change(selected_items):
        try:
            if not selected_items:
                return
            
            mode = selected_items[0]
            
            ui_refs['timer_value_select'].visible = False
            ui_refs['custom_time_input'].visible = False
            
            if mode == "minutes":
                ui_refs['timer_value_select'].label = "Select Minutes"
                ui_refs['timer_value_select'].items = [
                    {"id": "1", "title": "1 minute"},
                    {"id": "5", "title": "5 minutes"},
                    {"id": "10", "title": "10 minutes"},
                    {"id": "15", "title": "15 minutes"},
                    {"id": "30", "title": "30 minutes"},
                    {"id": "45", "title": "45 minutes"},
                    {"id": "60", "title": "60 minutes"}
                ]
                ui_refs['timer_value_select'].visible = True
            elif mode == "hours":
                ui_refs['timer_value_select'].label = "Select Hours"
                ui_refs['timer_value_select'].items = [
                    {"id": "60", "title": "1 hour"},
                    {"id": "120", "title": "2 hours"},
                    {"id": "180", "title": "3 hours"},
                    {"id": "240", "title": "4 hours"},
                    {"id": "360", "title": "6 hours"},
                    {"id": "480", "title": "8 hours"},
                    {"id": "720", "title": "12 hours"}
                ]
                ui_refs['timer_value_select'].visible = True
            elif mode == "custom":
                ui_refs['custom_time_input'].visible = True
            
        except Exception as e:
            print(f"[VC Manager] Timer mode error: {e}", type_="ERROR")
    
    async def handle_apply_timer():
        apply_timer_button.loading = True
        
        try:
            selected_mode = ui_refs['timer_mode_select'].selected_items
            if not selected_mode:
                tab.toast("Error", "Select timer mode", "ERROR")
                apply_timer_button.loading = False
                return
            
            mode = selected_mode[0]
            
            if mode == "none":
                data = load_data()
                data["settings"]["auto_disconnect_minutes"] = None
                save_data(data)
                
                if disconnect_task:
                    disconnect_task.cancel()
                
                tab.toast("Success", "Timer disabled", "SUCCESS")
            elif mode == "custom":
                custom_value = ui_refs['custom_time_input'].value
                if not custom_value or not custom_value.strip():
                    tab.toast("Error", "Enter time in seconds", "ERROR")
                    apply_timer_button.loading = False
                    return
                
                try:
                    seconds = int(custom_value.strip())
                    if seconds <= 0:
                        tab.toast("Error", "Time must be > 0", "ERROR")
                        apply_timer_button.loading = False
                        return
                    
                    minutes = seconds / 60
                    data = load_data()
                    data["settings"]["auto_disconnect_minutes"] = minutes
                    save_data(data)
                    
                    if active_channel and is_actually_connected():
                        await schedule_disconnect(minutes)
                    
                    tab.toast("Success", f"Timer set to {seconds}s", "SUCCESS")
                except ValueError:
                    tab.toast("Error", "Invalid number", "ERROR")
            else:
                selected_value = ui_refs['timer_value_select'].selected_items
                if not selected_value:
                    tab.toast("Error", "Select time value", "ERROR")
                    apply_timer_button.loading = False
                    return
                
                minutes = float(selected_value[0])
                data = load_data()
                data["settings"]["auto_disconnect_minutes"] = minutes
                save_data(data)
                
                if active_channel and is_actually_connected():
                    await schedule_disconnect(minutes)
                
                if minutes < 60:
                    time_str = f"{int(minutes)} min"
                else:
                    hours = int(minutes / 60)
                    time_str = f"{hours} hr"
                
                tab.toast("Success", f"Timer set to {time_str}", "SUCCESS")
        
        except Exception as e:
            tab.toast("Error", f"Timer failed: {str(e)}", "ERROR")
            print(f"[VC Manager] Timer error: {e}", type_="ERROR")
        finally:
            apply_timer_button.loading = False
    
    def handle_refresh_stats():
        update_all_ui()
        tab.toast("Success", "Stats refreshed", "SUCCESS")
    
    # ==================== UI TAB ====================
    tab = Tab(
        name="VCManager",
        title="Voice Channel Manager",
        icon="users",
        gap=6
    )
    
    main_container = tab.create_container(type="columns", gap=6)
    
    left_container = main_container.create_container(type="rows", width="auto", gap=6)
    
    connection_card = left_container.create_card(type="rows", gap=1)
    connection_card.create_ui_element(UI.Text, content="Voice Connection", size="xl", weight="bold")
    
    use_channel_id_toggle = connection_card.create_ui_element(
        UI.Toggle,
        label="Use Channel ID directly",
        checked=False
    )
    ui_refs['use_channel_id_toggle'] = use_channel_id_toggle
    
    server_select = connection_card.create_ui_element(
        UI.Select,
        label="Select Server",
        items=[{"id": "loading", "title": "Loading servers..."}],
        mode="single",
        full_width=True
    )
    ui_refs['server_select'] = server_select
    
    channel_select = connection_card.create_ui_element(
        UI.Select,
        label="Select Voice Channel",
        items=[{"id": "none", "title": "Select a server first"}],
        mode="single",
        full_width=True,
        visible=False
    )
    ui_refs['channel_select'] = channel_select
    
    channel_id_input = connection_card.create_ui_element(
        UI.Input,
        label="Channel ID",
        placeholder="Enter voice channel ID...",
        full_width=True,
        visible=False
    )
    ui_refs['channel_id_input'] = channel_id_input
    
    button_group = connection_card.create_group(type="columns", gap=0)
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
    
    status_card = left_container.create_card(type="rows", gap=1)
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
    
    right_container = main_container.create_container(type="rows", gap=6)
    
    settings_card = right_container.create_card(type="rows", gap=2)
    settings_card.create_ui_element(UI.Text, content="Voice Settings", size="lg", weight="bold")
    settings_card.create_ui_element(UI.Text, content="(Available when connected)", size="sm", color="#888888")
    
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
    
    timer_card = right_container.create_card(type="rows", gap=3)
    timer_card.create_ui_element(UI.Text, content="Auto-Disconnect Timer", size="lg", weight="bold")
    
    timer_mode_select = timer_card.create_ui_element(
        UI.Select,
        label="Timer Mode",
        items=[
            {"id": "none", "title": "None (Never disconnect)"},
            {"id": "minutes", "title": "Minutes"},
            {"id": "hours", "title": "Hours"},
            {"id": "custom", "title": "Custom (seconds)"}
        ],
        selected_items=["none"],
        mode="single",
        full_width=True
    )
    ui_refs['timer_mode_select'] = timer_mode_select
    
    timer_value_select = timer_card.create_ui_element(
        UI.Select,
        label="Select Time",
        items=[{"id": "1", "title": "1 minute"}],
        mode="single",
        full_width=True,
        visible=False
    )
    ui_refs['timer_value_select'] = timer_value_select
    
    custom_time_input = timer_card.create_ui_element(
        UI.Input,
        label="Custom Time (seconds)",
        placeholder="Enter seconds...",
        full_width=True,
        visible=False
    )
    ui_refs['custom_time_input'] = custom_time_input
    
    apply_timer_button = timer_card.create_ui_element(
        UI.Button,
        label="Apply Timer",
        variant="solid",
        color="primary",
        full_width=True
    )
    
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
    
    # ==================== ASSIGN EVENT HANDLERS ====================
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
    
    # ==================== INITIALIZATION ====================
    def initialize_ui():
        try:
            update_all_ui()
        except Exception as e:
            print(f"[VC Manager] UI init error: {e}", type_="ERROR")
    
    @bot.listen("on_ready")
    async def on_bot_ready():
        try:
            await asyncio.sleep(2)
            await refresh_server_list()
            update_all_ui()
            print("[VC Manager] Server list loaded", type_="SUCCESS")
        except Exception as e:
            print(f"[VC Manager] Server list error: {e}", type_="ERROR")
    
    initialize_ui()
    
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
            print(f"[VC Manager] Error processing guild: {e}", type_="ERROR")
    
    if servers_list:
        server_select.items = servers_list
        print(f"[VC Manager] Loaded {len(servers_list)} servers initially", type_="INFO")
    else:
        server_select.items = [{"id": "none", "title": "No servers available"}]
    
    tab.render()
    
    print("[VC Manager] Script loaded successfully", type_="SUCCESS")

vc_manager_script()
