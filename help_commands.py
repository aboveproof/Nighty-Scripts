def nighty_help_script():    
    async def send_help_embed(ctx, title, description):
        """Send a help embed with proper forwarding and user mention handling."""
        # Save current private setting and disable private mode for embed sending
        current_private = getConfigData().get("private")
        updateConfigData("private", False)
        
        try:
            # Check if the command was used as a reply to another message
            replied_user = None
            if ctx.message.reference and ctx.message.reference.message_id:
                try:
                    # Get the message that was replied to
                    replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    replied_user = replied_message.author
                except Exception as e:
                    print(f"Could not fetch replied message: {e}", type_="ERROR")
            
            # Send user mention first as a regular message if replying
            if replied_user:
                await ctx.send(replied_user.mention)
            
            # Send as embed using forwardEmbedMethod - trying with just content parameter
            await forwardEmbedMethod(
                channel_id=ctx.channel.id,
                content=f"**{title}**\n\n{description}"
            )
            
            print(f"Help embed '{title}' sent successfully{' with user mention' if replied_user else ''}", type_="SUCCESS")
            
        except Exception as e:
            print(f"Error sending help embed: {e}", type_="ERROR")
            # Fallback to plain text if embed fails
            fallback_text = f"**{title}**\n\n{description}"
            if replied_user:
                fallback_text = f"{replied_user.mention}\n\n{fallback_text}"
            await ctx.send(fallback_text)
        finally:
            # Restore original private setting
            updateConfigData("private", current_private)

    @bot.command(
        name="webview",
        description="Fix for weird looking UI issues - provides WebView2 download link"
    )
    async def webview_fix(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        title = "Weird looking UI Fix"
        description = (
            "> 1. Fully close Nighty\n"
            "> 2. Download webview2: https://webview.niggy.one\n"
            "> 3. Then restart nighty"
        )
        
        await send_help_embed(ctx, title, description)
        print("WebView fix command executed", type_="INFO")

    @bot.command(
        name="loading",
        description="Solution for infinite loading problems using VPN"
    )
    async def loading_fix(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        title = "Nighty infinite Loading"
        description = (
            "> 1. ``Download a vpn`` if you dont already have one *[Proton VPN is free](https://protonvpn.com/free-vpn)*\n"
            "> 2. ``Close nighty`` and or ``end nighty.exe task``\n"
            "> 3. ``Open the vpn`` & ``wait for it to connect``\n"
            "> 4. Then run nighty as ``admin``\n"
            "> 5. Once Nighty has finished loading, you can disconnect the VPN"
        )
        
        await send_help_embed(ctx, title, description)
        print("Loading fix command executed", type_="INFO")

    @bot.command(
        name="cmd",
        description="Fix for CMD prompt issues by resetting config"
    )
    async def cmd_fix(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        title = "Nighty CMD prompt fix"
        description = (
            "> 1. Press ``WIN + R``\n"
            "> 2. Type ``%appdata%``\n"
            "> 3. Find ``Nighty Selfbot``\n"
            "> 4. Delete ``nighty.config``\n"
            "> 5. Restart Nighty with ``Admin`` permissions"
        )
        
        await send_help_embed(ctx, title, description)
        print("CMD fix command executed", type_="INFO")

    @bot.command(
        name="safe",
        description="Information about Nighty's safety and ban statistics"
    )
    async def safety_info(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        title = "\"Is Nighty Safe?\""
        description = (
            "> Yes, Nighty is 100% safe.\n\n"
            "> We conduct extensive testing to ensure Nighty Selfbot is **safe to use** and undetectable. However, users should be aware of the following:\n"
            "> Discord's Terms of Service prohibits selfbots.\n"
            "> While bans resulting from Nighty Selfbot usage are extremely rare (0 ban reports in the past 3 years), the risk exists in theory - but in practice, such cases are virtually unheard of.\n"
            "> We are **not responsible** for any action taken against your Discord account, including but not limited to suspension or termination.\n"
            "So in short, you should be aware that it's technically against Discord ToS, but no one got banned in the past 3 years, meaning **Nighty is safe**."
        )
        
        await send_help_embed(ctx, title, description)
        print("Safety info command executed", type_="INFO")

    @bot.command(
        name="ticket",
        description="Instructions for creating support tickets"
    )
    async def ticket_info(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        title = "\"How can i make a ticket?\""
        description = (
            "> To make a ticket type and send ``//newticket`` into any channel you can type in.\n"
            "> Or use this link https://nighty.support"
        )
        
        await send_help_embed(ctx, title, description)
        print("Ticket info command executed", type_="INFO")

    @bot.command(
        name="discordfix",
        description="Fix for Discord links opening in canary instead of regular Discord"
    )
    async def discord_fix(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        title = "How to fix discord link from sending to canary?"
        description = (
            "> 1. Download this bat file: https://discordfix.niggy.one\n"
            "> 2. Run the file\n"
            "> 3. Restart nighty"
        )
        
        await send_help_embed(ctx, title, description)
        print("Discord fix command executed", type_="INFO")

    @bot.command(
        name="help",
        description="Shows all available Nighty help commands"
    )
    async def help_command(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        # Get the user's configured prefix
        prefix = getConfigData().get("prefix", "<p>")
        
        # Check if the command was used as a reply to another message
        replied_user = None
        if ctx.message.reference and ctx.message.reference.message_id:
            try:
                replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                replied_user = replied_message.author
            except Exception as e:
                print(f"Could not fetch replied message: {e}", type_="ERROR")
        
        help_text = (
            "> **Nighty Help Commands**\n"
            "> \n"
            f"> `{prefix}webview` - Fix for weird looking UI issues\n"
            f"> `{prefix}loading` - Solution for infinite loading problems\n"
            f"> `{prefix}cmd` - Fix for CMD prompt issues\n"
            f"> `{prefix}safe` - Information about Nighty's safety\n"
            f"> `{prefix}ticket` - Instructions for creating support tickets\n"
            f"> `{prefix}discordfix` - Fix for Discord links opening in canary\n"
            "> \n"
            "> Use any of these commands to get detailed troubleshooting help!"
        )
        
        # Add user mention if replying
        if replied_user:
            help_text = f"{replied_user.mention}\n\n{help_text}"
        
        await ctx.send(help_text)
        print("Help command executed", type_="INFO")

    print("Nighty Help Commands script initialized successfully", type_="SUCCESS")

# Initialize the script
nighty_help_script()
