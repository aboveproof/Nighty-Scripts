def afk_script():
    """
    AFK SCRIPT
    ----------

    Automatically replies when you're pinged while AFK, logs every ping,
    and welcomes you back with elapsed time + ping count when you send a message.

    COMMANDS:
    <p>afk [reason]                  - Enable AFK mode (default reason: AFK)
    <p>afkm <message>                - Set your AFK auto-reply (use \\n for newlines)
    <p>afkp                          - View all pings from current/last AFK session
    <p>afksettings                   - View all settings and their current values
    <p>afksettings everyone on/off   - Toggle @everyone / @here ping responses
    <p>afksettings cooldown <secs>   - Set per-user reply cooldown in seconds (0 = reply once ever)
    """

    import json
    from pathlib import Path
    from datetime import datetime

    # --- Storage ---
    BASE_DIR   = Path(getScriptsPath()) / "json"
    PINGS_FILE = BASE_DIR / "afk_pings.json"
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # --- In-memory state ---
    _in_command      = [False]   # True while a command handler is executing
    _sending_reply   = [False]   # True while bot is sending an AFK auto-reply
    _user_cooldowns  = {}        # {user_id: last_reply_datetime}

    # --- Config defaults ---
    _defaults = {
        "afk_active":          False,
        "afk_message":         "I'm currently AFK. I'll be back soon!",
        "afk_reason":          "AFK",
        "afk_start_time":      None,
        "afk_everyone":        False,   # respond to @everyone / @here pings
        "afk_cooldown":        0,       # seconds; 0 = reply once per session (original behaviour)
    }
    for key, val in _defaults.items():
        if getConfigData().get(key) is None:
            updateConfigData(key, val)

    # =========================================================
    # HELPERS
    # =========================================================

    def load_pings():
        try:
            with open(PINGS_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_pings(pings):
        try:
            with open(PINGS_FILE, "w") as f:
                json.dump(pings, f, indent=4)
        except IOError as e:
            print(f"[AFK] Failed to save pings: {e}", type_="ERROR")

    def format_duration(total_seconds):
        total_seconds = int(total_seconds)
        days    = total_seconds // 86400;  total_seconds %= 86400
        hours   = total_seconds // 3600;   total_seconds %= 3600
        minutes = total_seconds // 60
        seconds = total_seconds % 60

        parts = []
        if days:    parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours:   parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes: parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds or not parts:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        if len(parts) == 1:
            return parts[0]
        return ", ".join(parts[:-1]) + " and " + parts[-1]

    def on_cooldown(author_id: int) -> bool:
        """
        Returns True if this user should NOT be replied to yet.
        cooldown=0 → reply once per session (never again once replied)
        cooldown>0 → reply once per N seconds
        """
        cooldown = getConfigData().get("afk_cooldown", 0)
        last     = _user_cooldowns.get(author_id)

        if last is None:
            return False   # Never replied → not on cooldown

        if cooldown == 0:
            return True    # 0 = once per session

        elapsed = (datetime.utcnow() - last).total_seconds()
        return elapsed < cooldown

    def set_cooldown(author_id: int):
        _user_cooldowns[author_id] = datetime.utcnow()

    # =========================================================
    # COMMANDS
    # =========================================================

    @bot.command(
        name="afk",
        usage="[reason]",
        description="Enable AFK mode with an optional reason."
    )
    async def afk_cmd(ctx, *, args: str = ""):
        await ctx.message.delete()
        _in_command[0] = True
        try:
            reason = args.strip() or "AFK"
            updateConfigData("afk_active",     True)
            updateConfigData("afk_reason",     reason)
            updateConfigData("afk_start_time", datetime.utcnow().isoformat())
            save_pings([])
            _user_cooldowns.clear()
            await ctx.send(f"> `🌙` You are now AFK: **{reason}**", silent=True)
        except Exception as e:
            print(f"[AFK] afk error: {e}", type_="ERROR")
        finally:
            _in_command[0] = False

    @bot.command(
        name="afkm",
        usage="<message>",
        description="Set AFK auto-reply. Use \\\\n for newlines."
    )
    async def afkm_cmd(ctx, *, args: str = ""):
        await ctx.message.delete()
        _in_command[0] = True
        try:
            if not args.strip():
                await ctx.send("> `❌` Usage: `<p>afkm <message>`", silent=True)
                return
            message = args.strip().replace("\\n", "\n")
            updateConfigData("afk_message", message)
            preview = message.replace("\n", " ↵ ")
            await ctx.send(f"> `✅` AFK message set: `{preview}`", silent=True)
        except Exception as e:
            print(f"[AFK] afkm error: {e}", type_="ERROR")
        finally:
            _in_command[0] = False

    @bot.command(
        name="afkp",
        usage="",
        description="Show all pings received during the current/last AFK session."
    )
    async def afkp_cmd(ctx):
        await ctx.message.delete()
        _in_command[0] = True
        try:
            pings = load_pings()
            if not pings:
                await ctx.send("📭 No pings recorded.", silent=True)
                return

            count     = len(pings)
            time_word = "time" if count == 1 else "times"
            lines     = [f"### You were pinged {count} {time_word}.\n\nAFK Pings:"]
            for i, ping in enumerate(pings, 1):
                lines.append(
                    f"{i}. {ping.get('user', 'Unknown')} in {ping.get('channel_link', '?')}: "
                    f"[Jump to message]({ping.get('jump_url', '')}) - {ping.get('content', '*(empty)*')}"
                )
            await ctx.send("\n".join(lines))
        except Exception as e:
            print(f"[AFK] afkp error: {e}", type_="ERROR")
        finally:
            _in_command[0] = False

    @bot.command(
        name="afksettings",
        usage="[setting] [value]",
        description="View or change AFK settings."
    )
    async def afksettings_cmd(ctx, *, args: str = ""):
        await ctx.message.delete()
        _in_command[0] = True
        try:
            parts    = args.strip().split() if args.strip() else []
            cfg      = getConfigData()
            everyone = cfg.get("afk_everyone", False)
            cooldown = cfg.get("afk_cooldown", 0)
            active   = cfg.get("afk_active", False)
            reason   = cfg.get("afk_reason", "AFK")
            msg      = cfg.get("afk_message", "").replace("\n", " ↵ ")
            prefix   = cfg.get("prefix", ".")

            # ── No args → show settings menu ──────────────────────────
            if not parts:
                cooldown_display = f"`{cooldown}s`" if cooldown > 0 else "`once per session`"
                menu = (
                    f"### `⚙️` AFK Settings\n"
                    f"\n"
                    f"**Status**\n"
                    f"> {'`🟢` Active' if active else '`🔴` Inactive'}"
                    f"{f' — reason: **{reason}**' if active else ''}\n"
                    f"\n"
                    f"**Auto-reply message** (`{prefix}afkm <message>`)\n"
                    f"> `{msg or 'not set'}`\n"
                    f"\n"
                    f"**@everyone / @here pings** (`{prefix}afksettings everyone on/off`)\n"
                    f"> {'`✅` Enabled' if everyone else '`❌` Disabled'} — "
                    f"{'bot will respond to mass pings' if everyone else 'bot ignores mass pings'}\n"
                    f"\n"
                    f"**Reply cooldown** (`{prefix}afksettings cooldown <seconds>`)\n"
                    f"> {cooldown_display} — "
                    f"{'replies once per session per user' if cooldown == 0 else f'replies once every {cooldown}s per user'}\n"
                    f"\n"
                    f"-# Use `{prefix}afksettings <setting> <value>` to change a setting."
                )
                await ctx.send(menu, silent=True)
                return

            setting = parts[0].lower()
            value   = parts[1].lower() if len(parts) > 1 else ""

            # ── everyone on/off ────────────────────────────────────────
            if setting == "everyone":
                if value not in ("on", "off"):
                    await ctx.send("`> ❌` Usage: `<p>afksettings everyone on/off`", silent=True)
                    return
                state = value == "on"
                updateConfigData("afk_everyone", state)
                label = "`✅` Enabled" if state else "`❌` Disabled"
                await ctx.send(
                    f"{label} @everyone / @here auto-replies.",
                    silent=True
                )

            # ── cooldown <seconds> ─────────────────────────────────────
            elif setting == "cooldown":
                if not value.isdigit():
                    await ctx.send(
                        "❌ Usage: `<p>afksettings cooldown <seconds>` — e.g. `<p>afksettings cooldown 30`\n"
                        "-# Use `0` to reply once per session (no repeat replies).",
                        silent=True
                    )
                    return
                secs = int(value)
                updateConfigData("afk_cooldown", secs)
                if secs == 0:
                    await ctx.send("> `✅` Cooldown set to **once per session** (users won't get a second reply).", silent=True)
                else:
                    await ctx.send(f"> `✅` Cooldown set to **{secs} second{'s' if secs != 1 else ''}**.", silent=True)

            else:
                await ctx.send(
                    f"❓ Unknown setting `{setting}`.\n"
                    f"-# Available: `everyone`, `cooldown`",
                    silent=True
                )

        except Exception as e:
            print(f"[AFK] afksettings error: {e}", type_="ERROR")
        finally:
            _in_command[0] = False

    # =========================================================
    # EVENT LISTENER
    # =========================================================

    @bot.listen("on_message")
    async def afk_listener(message):
        if not getConfigData().get("afk_active", False):
            return

        # ── Selfbot sent a message ──────────────────────────────────────
        if message.author.id == bot.user.id:
            if _in_command[0] or _sending_reply[0]:
                return

            prefix = getConfigData().get("prefix", ".")
            if message.content.startswith(prefix):
                return

            # ✅ Real user-typed message → Welcome Back!
            start_str = getConfigData().get("afk_start_time")
            try:
                elapsed  = (datetime.utcnow() - datetime.fromisoformat(start_str)).total_seconds()
                duration = format_duration(elapsed)
            except Exception:
                duration = "some time"

            pings      = load_pings()
            ping_count = len(pings)
            ping_word  = "time" if ping_count == 1 else "times"

            updateConfigData("afk_active", False)
            _user_cooldowns.clear()

            try:
                await message.reply(
                    f"> `👋` Welcome back, you were away for **{duration}**. "
                    f"You got pinged: **{ping_count}** {ping_word}."
                )
            except Exception as e:
                print(f"[AFK] Welcome back reply failed: {e}", type_="ERROR")
            return

        # ── Someone else sent a message ─────────────────────────────────
        if message.author.bot:
            return

        cfg      = getConfigData()
        everyone = cfg.get("afk_everyone", False)

        # Determine if this message actually pings the selfbot
        direct_ping   = bot.user in message.mentions
        everyone_ping = everyone and (message.mention_everyone)

        if not direct_ping and not everyone_ping:
            return

        author_id = message.author.id

        # Check cooldown
        if on_cooldown(author_id):
            return
        set_cooldown(author_id)

        # Build jump URL and channel reference
        if message.guild:
            jump_url     = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
            channel_link = f"<#{message.channel.id}>"
        else:
            jump_url     = f"https://discord.com/channels/@me/{message.channel.id}/{message.id}"
            channel_link = "DMs"

        # Log ping
        pings = load_pings()
        pings.append({
            "user":         str(message.author),
            "user_id":      str(author_id),
            "channel_link": channel_link,
            "jump_url":     jump_url,
            "content":      message.content[:200]
        })
        save_pings(pings)

        # Send afkm reply
        afk_reply = cfg.get("afk_message", "I'm currently AFK. I'll be back soon!")

        _sending_reply[0] = True
        try:
            await message.reply(afk_reply)
        except Exception as e:
            print(f"[AFK] Auto-reply failed: {e}", type_="ERROR")
        finally:
            _sending_reply[0] = False

afk_script()
