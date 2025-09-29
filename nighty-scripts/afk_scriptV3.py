def ping_afk_system():
    CONFIG_PREFIX = "ping_afk_"
    
    # Initialize default configuration
    defaults = {
        f"{CONFIG_PREFIX}afk_enabled": False,
        f"{CONFIG_PREFIX}afk_message": "I'm currently AFK",
        f"{CONFIG_PREFIX}afk_delay": 0,
        f"{CONFIG_PREFIX}afk_typing": True,
        f"{CONFIG_PREFIX}afk_typing_length": 2,
        f"{CONFIG_PREFIX}afk_reply": True,
        f"{CONFIG_PREFIX}afk_server": True,
        f"{CONFIG_PREFIX}afk_cooldown": 60
    }
    
    for key, value in defaults.items():
        if getConfigData().get(key) is None:
            updateConfigData(key, value)
    
    # JSON storage for ping tracking
    BASE_DIR = Path(getScriptsPath()) / "json"
    PINGS_FILE = BASE_DIR / "ping_tracker.json"
    COOLDOWNS_FILE = BASE_DIR / "afk_cooldowns.json"
    
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize JSON files
    if not PINGS_FILE.exists():
        with open(PINGS_FILE, "w") as f:
            json.dump({}, f, indent=4)
    
    if not COOLDOWNS_FILE.exists():
        with open(COOLDOWNS_FILE, "w") as f:
            json.dump({}, f, indent=4)
    
    def load_pings():
        """Load ping data from JSON file."""
        try:
            with open(PINGS_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Warning: ping_tracker.json not found or invalid.", type_="ERROR")
            return {}
    
    def save_pings(data):
        """Save ping data to JSON file."""
        try:
            with open(PINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            print(f"Error saving pings: {e}", type_="ERROR")
    
    def load_cooldowns():
        """Load cooldown data from JSON file."""
        try:
            with open(COOLDOWNS_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_cooldowns(data):
        """Save cooldown data to JSON file."""
        try:
            with open(COOLDOWNS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            print(f"Error saving cooldowns: {e}", type_="ERROR")
    
    def is_on_cooldown(user_id: str) -> bool:
        """Check if a user is on cooldown."""
        cooldowns = load_cooldowns()
        cooldown_time = getConfigData().get(f"{CONFIG_PREFIX}afk_cooldown", 60)
        
        if user_id in cooldowns:
            last_response = datetime.fromisoformat(cooldowns[user_id])
            if datetime.now() < last_response + timedelta(seconds=cooldown_time):
                return True
        
        return False
    
    def set_cooldown(user_id: str):
        """Set cooldown for a user."""
        cooldowns = load_cooldowns()
        cooldowns[user_id] = datetime.now().isoformat()
        save_cooldowns(cooldowns)
    
    # Command: Display recent pings
    @bot.command(
        name="pings",
        description="Display the most recent pings in the current channel"
    )
    async def show_pings(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        channel_id = str(ctx.channel.id)
        pings_data = load_pings()
        
        if channel_id not in pings_data or not pings_data[channel_id]:
            await ctx.send("> No pings found in this channel.", delete_after=5)
            return
        
        # Build embed content
        ping_list = []
        for ping in pings_data[channel_id][-10:]:
            timestamp = datetime.fromisoformat(ping["timestamp"])
            time_str = timestamp.strftime("%I:%M %p")
            username = ping["username"]
            user_id = ping["user_id"]
            message_link = ping["message_link"]
            
            ping_list.append(f"> {time_str} **{username}** ({user_id}) [Jump]({message_link})")
        
        content = "# Pings\n\n" + "\n".join(reversed(ping_list))
        
        try:
            await forwardEmbedMethod(
                channel_id=ctx.channel.id,
                content=content,
                title="Recent Pings"
            )
        except Exception as e:
            print(f"Error sending pings embed: {e}", type_="ERROR")
            await ctx.send(f"> Error displaying pings: {e}", delete_after=5)
    
    # Command: Toggle AFK
    @bot.command(
        name="afk",
        description="Toggle AFK mode on/off"
    )
    async def toggle_afk(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        current_status = getConfigData().get(f"{CONFIG_PREFIX}afk_enabled", False)
        new_status = not current_status
        
        if new_status:
            # Going AFK - store the timestamp
            updateConfigData(f"{CONFIG_PREFIX}afk_start_time", datetime.now().isoformat())
            updateConfigData(f"{CONFIG_PREFIX}afk_enabled", new_status)
            msg = await ctx.send("> You are now AFK, deleting in 3 seconds...")
            await asyncio.sleep(3)
            await msg.delete()
            print("AFK mode enabled", type_="SUCCESS")
        else:
            # Going un-AFK - show pings received during AFK
            updateConfigData(f"{CONFIG_PREFIX}afk_enabled", new_status)
            afk_start = getConfigData().get(f"{CONFIG_PREFIX}afk_start_time")
            
            if afk_start:
                afk_start_time = datetime.fromisoformat(afk_start)
                afk_end_time = datetime.now()
                
                # Calculate how long they were AFK
                afk_duration = afk_end_time - afk_start_time
                hours = int(afk_duration.total_seconds() // 3600)
                minutes = int((afk_duration.total_seconds() % 3600) // 60)
                seconds = int(afk_duration.total_seconds() % 60)
                
                if hours > 0:
                    duration_str = f"{hours}h {minutes}m {seconds}s"
                elif minutes > 0:
                    duration_str = f"{minutes}m {seconds}s"
                else:
                    duration_str = f"{seconds}s"
                
                channel_id = str(ctx.channel.id)
                pings_data = load_pings()
                
                # Collect all pings from all channels during AFK period
                all_afk_pings = []
                for ch_id, pings in pings_data.items():
                    for ping in pings:
                        ping_time = datetime.fromisoformat(ping["timestamp"])
                        if ping_time >= afk_start_time:
                            ping["channel_id"] = ch_id
                            all_afk_pings.append(ping)
                
                # Sort by timestamp
                all_afk_pings.sort(key=lambda x: x["timestamp"])
                
                if all_afk_pings:
                    # Build embed content with all AFK pings
                    ping_list = []
                    for ping in all_afk_pings:
                        timestamp = datetime.fromisoformat(ping["timestamp"])
                        time_str = timestamp.strftime("%I:%M %p")
                        username = ping["username"]
                        user_id = ping["user_id"]
                        message_link = ping["message_link"]
                        
                        ping_list.append(f"> {time_str} **{username}** ({user_id}) [Jump]({message_link})")
                    
                    content = f"# Pings While AFK\n\n> **Duration:** {duration_str}\n> **Total Pings:** {len(all_afk_pings)}\n\n" + "\n".join(ping_list)
                    
                    try:
                        await forwardEmbedMethod(
                            channel_id=ctx.channel.id,
                            content=content,
                            title="AFK Pings"
                        )
                    except Exception as e:
                        print(f"Error sending AFK pings embed: {e}", type_="ERROR")
                        await ctx.send(f"> You received {len(all_afk_pings)} pings while AFK for {duration_str}. Error displaying: {e}", delete_after=10)
                else:
                    await ctx.send(f"> You are no longer AFK. No pings received during {duration_str}.", delete_after=5)
            else:
                await ctx.send("> You are no longer AFK.", delete_after=3)
            
            print("AFK mode disabled", type_="SUCCESS")
            save_cooldowns({})
            # Clear the start time
            updateConfigData(f"{CONFIG_PREFIX}afk_start_time", None)
    
    # Command: Set AFK message
    @bot.command(
        name="afkm",
        aliases=["afkmessage"],
        description="Set your custom AFK message"
    )
    async def set_afk_message(ctx, *, message: str = ""):
        await ctx.message.delete()
        
        if not message:
            current = getConfigData().get(f"{CONFIG_PREFIX}afk_message", "I'm currently AFK")
            await ctx.send(f"> Current AFK message: **{current}**", delete_after=5)
            return
        
        updateConfigData(f"{CONFIG_PREFIX}afk_message", message)
        await ctx.send(f"> AFK message set to: **{message}**", delete_after=5)
        print(f"AFK message updated: {message}", type_="SUCCESS")
    
    # Command: Set AFK delay
    @bot.command(
        name="afkd",
        aliases=["afkdelay"],
        description="Set delay before AFK response (in seconds)"
    )
    async def set_afk_delay(ctx, *, delay: str = ""):
        await ctx.message.delete()
        
        if not delay:
            current = getConfigData().get(f"{CONFIG_PREFIX}afk_delay", 0)
            await ctx.send(f"> Current AFK delay: **{current} seconds**", delete_after=5)
            return
        
        try:
            delay_val = int(delay)
            if delay_val < 0:
                await ctx.send("> Delay must be 0 or positive.", delete_after=5)
                return
            
            updateConfigData(f"{CONFIG_PREFIX}afk_delay", delay_val)
            await ctx.send(f"> AFK delay set to: **{delay_val} seconds**", delete_after=5)
            print(f"AFK delay updated: {delay_val}s", type_="SUCCESS")
        except ValueError:
            await ctx.send("> Invalid number. Please provide a valid delay in seconds.", delete_after=5)
    
    # Command: Toggle AFK typing
    @bot.command(
        name="afkt",
        aliases=["afktyping"],
        description="Enable/disable typing indicator when AFK responding"
    )
    async def set_afk_typing(ctx, *, enabled: str = ""):
        await ctx.message.delete()
        
        if not enabled:
            current = getConfigData().get(f"{CONFIG_PREFIX}afk_typing", True)
            await ctx.send(f"> AFK typing indicator: **{'Enabled' if current else 'Disabled'}**", delete_after=5)
            return
        
        enabled_lower = enabled.lower()
        if enabled_lower in ["true", "yes", "on", "1"]:
            updateConfigData(f"{CONFIG_PREFIX}afk_typing", True)
            await ctx.send("> AFK typing indicator **enabled**", delete_after=5)
            print("AFK typing enabled", type_="SUCCESS")
        elif enabled_lower in ["false", "no", "off", "0"]:
            updateConfigData(f"{CONFIG_PREFIX}afk_typing", False)
            await ctx.send("> AFK typing indicator **disabled**", delete_after=5)
            print("AFK typing disabled", type_="SUCCESS")
        else:
            await ctx.send("> Invalid value. Use: true/false, yes/no, on/off, or 1/0", delete_after=5)
    
    # Command: Set AFK typing length
    @bot.command(
        name="afktl",
        aliases=["afktypinglength"],
        description="Set typing indicator duration (in seconds)"
    )
    async def set_afk_typing_length(ctx, *, length: str = ""):
        await ctx.message.delete()
        
        if not length:
            current = getConfigData().get(f"{CONFIG_PREFIX}afk_typing_length", 2)
            await ctx.send(f"> Current AFK typing length: **{current} seconds**", delete_after=5)
            return
        
        try:
            length_val = int(length)
            if length_val < 1:
                await ctx.send("> Typing length must be at least 1 second.", delete_after=5)
                return
            
            updateConfigData(f"{CONFIG_PREFIX}afk_typing_length", length_val)
            await ctx.send(f"> AFK typing length set to: **{length_val} seconds**", delete_after=5)
            print(f"AFK typing length updated: {length_val}s", type_="SUCCESS")
        except ValueError:
            await ctx.send("> Invalid number. Please provide a valid length in seconds.", delete_after=5)
    
    # Command: Toggle AFK reply
    @bot.command(
        name="afkr",
        aliases=["afkreply"],
        description="Enable/disable replying to pings when AFK"
    )
    async def set_afk_reply(ctx, *, enabled: str = ""):
        await ctx.message.delete()
        
        if not enabled:
            current = getConfigData().get(f"{CONFIG_PREFIX}afk_reply", True)
            await ctx.send(f"> AFK auto-reply: **{'Enabled' if current else 'Disabled'}**", delete_after=5)
            return
        
        enabled_lower = enabled.lower()
        if enabled_lower in ["true", "yes", "on", "1"]:
            updateConfigData(f"{CONFIG_PREFIX}afk_reply", True)
            await ctx.send("> AFK auto-reply **enabled**", delete_after=5)
            print("AFK reply enabled", type_="SUCCESS")
        elif enabled_lower in ["false", "no", "off", "0"]:
            updateConfigData(f"{CONFIG_PREFIX}afk_reply", False)
            await ctx.send("> AFK auto-reply **disabled**", delete_after=5)
            print("AFK reply disabled", type_="SUCCESS")
        else:
            await ctx.send("> Invalid value. Use: true/false, yes/no, on/off, or 1/0", delete_after=5)
    
    # Command: Toggle AFK in servers
    @bot.command(
        name="afks",
        aliases=["afkserver"],
        description="Enable/disable AFK responses in servers (DMs always work)"
    )
    async def set_afk_server(ctx, *, enabled: str = ""):
        await ctx.message.delete()
        
        if not enabled:
            current = getConfigData().get(f"{CONFIG_PREFIX}afk_server", True)
            await ctx.send(f"> AFK in servers: **{'Enabled' if current else 'Disabled'}**", delete_after=5)
            return
        
        enabled_lower = enabled.lower()
        if enabled_lower in ["true", "yes", "on", "1"]:
            updateConfigData(f"{CONFIG_PREFIX}afk_server", True)
            await ctx.send("> AFK in servers **enabled**", delete_after=5)
            print("AFK server responses enabled", type_="SUCCESS")
        elif enabled_lower in ["false", "no", "off", "0"]:
            updateConfigData(f"{CONFIG_PREFIX}afk_server", False)
            await ctx.send("> AFK in servers **disabled** (DMs/group chats still work)", delete_after=5)
            print("AFK server responses disabled", type_="SUCCESS")
        else:
            await ctx.send("> Invalid value. Use: true/false, yes/no, on/off, or 1/0", delete_after=5)
    
    # Command: Set AFK cooldown
    @bot.command(
        name="afkc",
        aliases=["afkcooldown"],
        description="Set cooldown between responses to same user (in seconds)"
    )
    async def set_afk_cooldown(ctx, *, cooldown: str = ""):
        await ctx.message.delete()
        
        if not cooldown:
            current = getConfigData().get(f"{CONFIG_PREFIX}afk_cooldown", 60)
            await ctx.send(f"> Current AFK cooldown: **{current} seconds**", delete_after=5)
            return
        
        try:
            cooldown_val = int(cooldown)
            if cooldown_val < 0:
                await ctx.send("> Cooldown must be 0 or positive.", delete_after=5)
                return
            
            updateConfigData(f"{CONFIG_PREFIX}afk_cooldown", cooldown_val)
            await ctx.send(f"> AFK cooldown set to: **{cooldown_val} seconds**", delete_after=5)
            print(f"AFK cooldown updated: {cooldown_val}s", type_="SUCCESS")
        except ValueError:
            await ctx.send("> Invalid number. Please provide a valid cooldown in seconds.", delete_after=5)
    
    # Command: Help
    @bot.command(
        name="pinghelp",
        aliases=["afkhelp"],
        description="Show all available commands and settings"
    )
    async def show_help(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        prefix = getConfigData().get("prefix", ".")
        
        afk_enabled = getConfigData().get(f"{CONFIG_PREFIX}afk_enabled", False)
        afk_message = getConfigData().get(f"{CONFIG_PREFIX}afk_message", "I'm currently AFK")
        afk_delay = getConfigData().get(f"{CONFIG_PREFIX}afk_delay", 0)
        afk_typing = getConfigData().get(f"{CONFIG_PREFIX}afk_typing", True)
        afk_typing_length = getConfigData().get(f"{CONFIG_PREFIX}afk_typing_length", 2)
        afk_reply = getConfigData().get(f"{CONFIG_PREFIX}afk_reply", True)
        afk_server = getConfigData().get(f"{CONFIG_PREFIX}afk_server", True)
        afk_cooldown = getConfigData().get(f"{CONFIG_PREFIX}afk_cooldown", 60)
        
        help_content = f"""

## Ping Commands

> **{prefix}pings** - Display the most recent pings in this channel
> Shows the last 10 pings with timestamps, usernames, and jump links

## Current Settings

> **AFK Status:** {'Enabled' if afk_enabled else 'Disabled'}
> **AFK Message:** {afk_message}
> **Response Delay:** {afk_delay} seconds
> **Typing Indicator:** {'Enabled' if afk_typing else 'Disabled'} ({afk_typing_length}s)
> **Auto-Reply:** {'Enabled' if afk_reply else 'Disabled'}
> **Server Responses:** {'Enabled' if afk_server else 'Disabled'}
> **Response Cooldown:** {afk_cooldown} seconds

## AFK Commands

> **{prefix}afk** - Toggle AFK mode on/off
> **{prefix}afkm <message>** - Set your custom AFK message
> **{prefix}afkd <seconds>** - Set delay before responding
> **{prefix}afkt <true/false>** - Enable/disable typing indicator
> **{prefix}afktl <seconds>** - Set typing indicator duration
> **{prefix}afkr <true/false>** - Enable/disable auto-replies
> **{prefix}afks <true/false>** - Enable/disable server responses
> **{prefix}afkc <seconds>** - Set cooldown between responses"""
        
        try:
            await forwardEmbedMethod(
                channel_id=ctx.channel.id,
                content=help_content,
                title="Help Menu"
            )
        except Exception as e:
            print(f"Error sending help embed: {e}", type_="ERROR")
            await ctx.send(f"> Error displaying help: {e}", delete_after=5)
    
    # Event listener: Track pings and handle AFK
    @bot.listen("on_message")
    async def ping_tracker(message):
        if message.author.id == bot.user.id or message.author.bot:
            return
        
        # Check if it's a DM (not a group DM, just a regular DM)
        is_dm = message.guild is None and len(message.channel.recipients) == 2
        
        bot_mentioned = False
        for mention in message.mentions:
            if mention.id == bot.user.id:
                bot_mentioned = True
                break
        
        # In DMs, we don't need a mention. In servers/group chats, we do.
        if not is_dm and not bot_mentioned:
            return
        
        channel_id = str(message.channel.id)
        pings_data = load_pings()
        
        if channel_id not in pings_data:
            pings_data[channel_id] = []
        
        ping_entry = {
            "timestamp": datetime.now().isoformat(),
            "username": str(message.author),
            "user_id": str(message.author.id),
            "message_link": message.jump_url
        }
        
        pings_data[channel_id].append(ping_entry)
        
        if len(pings_data[channel_id]) > 50:
            pings_data[channel_id] = pings_data[channel_id][-50:]
        
        save_pings(pings_data)
        print(f"Ping tracked from {message.author} in {message.channel}", type_="INFO")
        
        afk_enabled = getConfigData().get(f"{CONFIG_PREFIX}afk_enabled", False)
        if not afk_enabled:
            return
        
        if message.guild:
            afk_server = getConfigData().get(f"{CONFIG_PREFIX}afk_server", True)
            if not afk_server:
                return
        
        afk_reply = getConfigData().get(f"{CONFIG_PREFIX}afk_reply", True)
        if not afk_reply:
            return
        
        user_id = str(message.author.id)
        if is_on_cooldown(user_id):
            print(f"User {message.author} on cooldown, skipping AFK response", type_="INFO")
            return
        
        delay = getConfigData().get(f"{CONFIG_PREFIX}afk_delay", 0)
        if delay > 0:
            await asyncio.sleep(delay)
        
        typing_enabled = getConfigData().get(f"{CONFIG_PREFIX}afk_typing", True)
        if typing_enabled:
            typing_length = getConfigData().get(f"{CONFIG_PREFIX}afk_typing_length", 2)
            async with message.channel.typing():
                await asyncio.sleep(typing_length)
        
        afk_message = getConfigData().get(f"{CONFIG_PREFIX}afk_message", "I'm currently AFK")
        try:
            await message.reply(afk_message, mention_author=False)
            set_cooldown(user_id)
            print(f"AFK response sent to {message.author}", type_="SUCCESS")
        except Exception as e:
            print(f"Error sending AFK response: {e}", type_="ERROR")
    
    # Event listener: Disable AFK on user message
    @bot.listen("on_message")
    async def afk_auto_disable(message):
        if message.author.id != bot.user.id:
            return
        
        afk_enabled = getConfigData().get(f"{CONFIG_PREFIX}afk_enabled", False)
        if not afk_enabled:
            return
        
        prefix = getConfigData().get("prefix", ".")
        if message.content.startswith(prefix):
            return
        
        if message.content.startswith(">"):
            return
        
        # Check if this is an AFK auto-response by checking if it's a reply
        if message.reference is not None:
            # This is a reply, likely our AFK auto-response, so don't disable AFK
            return
        
        # Check if message matches the AFK message (it's our auto-response)
        afk_message = getConfigData().get(f"{CONFIG_PREFIX}afk_message", "I'm currently AFK")
        if message.content == afk_message:
            return
        
        updateConfigData(f"{CONFIG_PREFIX}afk_enabled", False)
        save_cooldowns({})
        print("AFK auto-disabled due to user activity", type_="INFO")
        
        try:
            await message.channel.send("> AFK mode automatically disabled.", delete_after=3)
        except Exception as e:
            print(f"Error sending AFK disable message: {e}", type_="ERROR")
    
    print("Ping Tracker & AFK System loaded successfully", type_="SUCCESS")

ping_afk_system()
