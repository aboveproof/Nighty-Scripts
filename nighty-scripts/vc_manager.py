import json
import asyncio
from pathlib import Path
from datetime import datetime

def voice_manager_script():
    VOICE_MANAGER_PATH = Path(getScriptsPath()) / "json" / "voice_manager.json"
    VOICE_MANAGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_CONFIG = {}
    active_channel = None
    temp = {}
    connection_start_time = None

    def delete_after():
        return getConfigData().get('deletetimer', 10)

    def create_config_if_not_exist():
        if not VOICE_MANAGER_PATH.exists():
            with open(VOICE_MANAGER_PATH, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
    
    create_config_if_not_exist()

    def get_config():
        if VOICE_MANAGER_PATH.exists():
            try:
                with open(VOICE_MANAGER_PATH, 'r') as f:
                    return json.load(f)
            except:
                return DEFAULT_CONFIG
        else:
            create_config_if_not_exist()
            return get_config()
    
    def get_connection_duration():
        if connection_start_time is None:
            return "Not connected"
        
        duration = datetime.now() - connection_start_time
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    async def check_if_connect_success(msg, delay, error_message):
        await asyncio.sleep(delay)
        if temp.get('from', None):
            await msg.edit(f"> {error_message}", delete_after=delete_after())
    
    async def connect(guild_id, channel_id):
        payload = {
            "op": 4,
            "d": {
                "guild_id": guild_id,
                "channel_id": channel_id,
                "self_mute": False,
                "self_deaf": False
            }
        }
        await bot.ws.send(json.dumps(payload))
    
    @bot.listen("on_voice_state_update")
    async def on_voice_state_update(member, before, after):
        nonlocal active_channel, temp, connection_start_time
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
            active_channel = await bot.fetch_channel(channel_id) if channel_id else None
            message = temp.get('msg')
            _type = temp['type']
            _from = temp['from']
            
            if _from == 'command' and message is not None:
                if _type == 'join':
                    connection_start_time = datetime.now()
                    await message.edit(f'> Successfully connected to `{after.channel.name}`', delete_after=delete_after())
                    temp = {}
                elif _type == 'leave':
                    connection_start_time = None
                    channel_name = before.channel.name if before.channel else "voice channel"
                    await message.edit(f'> Successfully disconnected from `{channel_name}`', delete_after=delete_after())
                    temp = {}
        except Exception as e:
            print(f"Error in voice state update: {e}", type_="ERROR")
    
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
            await ctx.send('> Invalid channel ID', delete_after=delete_after())
            return
            
        if not isinstance(channel, discord.VoiceChannel):
            await ctx.send('> Channel is not a voice channel', delete_after=delete_after())
            return
        
        temp['type'] = 'join'
        temp['from'] = 'command'
        temp['msg'] = await ctx.send(f'> Connecting to `{channel.name}`...')
        await connect(str(channel.guild.id), str(channel.id))

        asyncio.create_task(check_if_connect_success(temp['msg'], 10, "Failed to connect"))

    @bot.command(
        name="fakeleavevc", 
        description="Leave current voice channel"
    )
    async def fake_leave_vc(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        temp['type'] = 'leave'
        temp['from'] = 'command'
        temp['msg'] = await ctx.send('> Disconnecting from voice channel...')
        await connect(None, None)

        asyncio.create_task(check_if_connect_success(temp['msg'], 10, "Failed to disconnect"))

    @bot.command(
        name="vchelp",
        description="Show voice manager help menu"
    )
    async def voice_help(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        prefix = await bot.get_prefix(ctx.message)
        
        current_channel = f"`{active_channel.name}`" if active_channel else "None"
        connection_duration = get_connection_duration()
        
        help_text = f"""> **Voice Manager Help**
> 
> **Commands:**
> `{prefix}fakejoinvc <channel_id>` - Join a voice channel
> `{prefix}fakeleavevc` - Leave current voice channel
> `{prefix}vchelp` - Show this help menu
> 
> **Current Status:**
> Connected to: {current_channel}
> Connected for: {connection_duration}"""

        await ctx.send(help_text, delete_after=delete_after())

voice_manager_script()
