from datetime import datetime
import requests
import json
import asyncio

def script_function():
    
    # Initialize configuration
    if getConfigData().get("dmlogger_enabled") is None:
        updateConfigData("dmlogger_enabled", False)

    # Helper function to check if webhook is configured
    def is_webhook_configured():
        """Returns True if webhook URL is configured"""
        return WEBHOOK_URL != "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

    # Helper function to check if logging is enabled
    def is_logging_enabled():
        """Returns True if logging is enabled"""
        enabled = getConfigData().get("dmlogger_enabled", False)
        return enabled and is_webhook_configured()

    # Asynchronous helper for running sync functions
    async def run_in_thread(func, *args, **kwargs):
        """Runs a synchronous function in a separate thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # Webhook sending function
    def send_webhook_embed(embed_data: dict) -> bool:
        """
        Sends an embed to the Discord webhook.
        
        Args:
            embed_data: A dictionary representing the embed structure.
        
        Returns:
            True if the message was sent successfully, False otherwise.
        """
        if not is_webhook_configured():
            print("Webhook URL is not configured.", type_="ERROR")
            return False
        
        payload = {"embeds": [embed_data]}
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(payload), timeout=10)
            response.raise_for_status()
            
            if response.status_code == 204:
                return True
            else:
                print(f"Webhook returned unexpected status: {response.status_code}", type_="ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Error sending webhook message: {e}", type_="ERROR")
            return False
        except Exception as e:
            print(f"Unexpected error during webhook sending: {e}", type_="ERROR")
            return False

    # Helper function to format timestamp
    def format_timestamp():
        """Returns current timestamp formatted"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Helper function to truncate long messages
    def truncate_message(content, max_length=1800):
        """Truncates message content if too long"""
        if len(content) > max_length:
            return content[:max_length] + "... (truncated)"
        return content

    # Event listener for new DM messages
    @bot.listen("on_message")
    async def dm_message_logger(message):
        # Ignore messages from self
        if message.author.id == bot.user.id:
            return
        
        # Only process DMs (messages without a guild)
        if message.guild:
            return
        
        # Check if logging is enabled
        if not is_logging_enabled():
            return
        
        try:
            # Prepare message content
            msg_content = truncate_message(message.content) if message.content else "*No text content*"
            
            # Add attachment info if present
            if message.attachments:
                attachment_info = "\n\n**Attachments:**\n"
                for att in message.attachments:
                    attachment_info += f"- [{att.filename}]({att.url})\n"
                msg_content += attachment_info
            
            # Create embed data
            embed_data = {
                "title": "📨 New DM Received",
                "description": (
                    f"# DM Logger - Sent\n\n"
                    f"**DM logger | {message.author} sent a message**\n\n"
                    f"**Message:**\n> {msg_content}\n\n"
                    f"**Jump:** [Click here]({message.jump_url})\n\n"
                    f"**Timestamp:** {format_timestamp()}"
                ),
                "color": 0x5865F2,
                "footer": {"text": "DM Logger"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send via webhook
            success = await run_in_thread(send_webhook_embed, embed_data)
            
            if success:
                print(f"Logged new DM from {message.author}", type_="INFO")
                
        except Exception as e:
            print(f"Error logging DM message: {e}", type_="ERROR")

    # Event listener for edited DM messages
    @bot.listen("on_message_edit")
    async def dm_edit_logger(before, after):
        # Ignore self edits
        if after.author.id == bot.user.id:
            return
        
        # Only process DMs
        if after.guild:
            return
        
        # Ignore if content didn't change
        if before.content == after.content:
            return
        
        # Check if logging is enabled
        if not is_logging_enabled():
            return
        
        try:
            # Prepare message contents
            before_content = truncate_message(before.content) if before.content else "*No text content*"
            after_content = truncate_message(after.content) if after.content else "*No text content*"
            
            # Create embed data
            embed_data = {
                "title": "✏️ DM Edited",
                "description": (
                    f"# DM Logger - Edit\n\n"
                    f"**DM logger | {after.author} edited a message**\n\n"
                    f"**Before:**\n> {before_content}\n\n"
                    f"**After:**\n> {after_content}\n\n"
                    f"**Jump:** [Click here]({after.jump_url})\n\n"
                    f"**Timestamp:** {format_timestamp()}"
                ),
                "color": 0xFFA500,
                "footer": {"text": "DM Logger"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send via webhook
            success = await run_in_thread(send_webhook_embed, embed_data)
            
            if success:
                print(f"Logged DM edit from {after.author}", type_="INFO")
                
        except Exception as e:
            print(f"Error logging DM edit: {e}", type_="ERROR")

    # Event listener for deleted DM messages
    @bot.listen("on_message_delete")
    async def dm_delete_logger(message):
        # Ignore self deletions
        if message.author.id == bot.user.id:
            return
        
        # Only process DMs
        if message.guild:
            return
        
        # Check if logging is enabled
        if not is_logging_enabled():
            return
        
        try:
            # Prepare message content
            msg_content = truncate_message(message.content) if message.content else "*No text content*"
            
            # Add attachment info if present
            if message.attachments:
                attachment_info = "\n\n**Attachments (deleted):**\n"
                for att in message.attachments:
                    attachment_info += f"- {att.filename}\n"
                msg_content += attachment_info
            
            # Create embed data
            embed_data = {
                "title": "🗑️ DM Deleted",
                "description": (
                    f"# DM Logger - Deleted\n\n"
                    f"**DM logger | {message.author} deleted a message**\n\n"
                    f"**Message:**\n> {msg_content}\n\n"
                    f"**Jump:** [Original location]({message.jump_url})\n\n"
                    f"**Timestamp:** {format_timestamp()}"
                ),
                "color": 0xFF0000,
                "footer": {"text": "DM Logger"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send via webhook
            success = await run_in_thread(send_webhook_embed, embed_data)
            
            if success:
                print(f"Logged DM deletion from {message.author}", type_="INFO")
                
        except Exception as e:
            print(f"Error logging DM deletion: {e}", type_="ERROR")

    # Command to configure DM logger
    @bot.command(
        name="dmlog",
        aliases=["dmlogger"],
        usage="<on|off|status>",
        description="Configure DM logging settings"
    )
    async def dmlog_command(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        # Parse arguments
        args = args.strip().lower()
        
        # Status command
        if args == "status":
            enabled = getConfigData().get("dmlogger_enabled", False)
            webhook_configured = is_webhook_configured()
            
            status_msg = f"**DM Logger Status**\n\n"
            status_msg += f"**Webhook Configured:** {'✅ Yes' if webhook_configured else '❌ No (edit script)'}\n"
            status_msg += f"**Logging Enabled:** {'✅ Yes' if enabled else '❌ No'}\n"
            status_msg += f"**Currently Logging:** {'✅ Active' if (enabled and webhook_configured) else '❌ Inactive'}\n\n"
            
            if not webhook_configured:
                status_msg += "⚠️ Please edit the WEBHOOK_URL at the top of the script.\n"
            elif not enabled:
                status_msg += f"Use `{getConfigData().get('prefix', '<p>')}dmlog on` to enable logging."
            
            await ctx.send(status_msg, delete_after=15)
            return
        
        # On command
        if args == "on":
            if not is_webhook_configured():
                await ctx.send("❌ Webhook URL not configured. Please edit the WEBHOOK_URL at the top of the script.", delete_after=10)
                return
            
            updateConfigData("dmlogger_enabled", True)
            await ctx.send("✅ DM logging enabled.", delete_after=5)
            print("DM logging enabled", type_="SUCCESS")
            return
        
        # Off command
        if args == "off":
            updateConfigData("dmlogger_enabled", False)
            await ctx.send("✅ DM logging disabled.", delete_after=5)
            print("DM logging disabled", type_="INFO")
            return
        
        # Show help
        prefix = getConfigData().get('prefix', '<p>')
        help_msg = f"**DM Logger Configuration**\n\n"
        help_msg += f"`{prefix}dmlog on` - Enable DM logging\n"
        help_msg += f"`{prefix}dmlog off` - Disable DM logging\n"
        help_msg += f"`{prefix}dmlog status` - Check current status\n\n"
        help_msg += f"**Setup:** Edit WEBHOOK_URL at the top of the script first!"
        
        await ctx.send(help_msg, delete_after=15)

    print("DM Logger script loaded successfully", type_="SUCCESS")

# Initialize the script
script_function()
