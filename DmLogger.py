import requests
import json
import asyncio
from datetime import datetime

def script_function():    
    # Initialize default config values
    if getConfigData().get("dm_logger_enabled") is None:
        updateConfigData("dm_logger_enabled", True)
    if getConfigData().get("dm_webhook_url") is None:
        updateConfigData("dm_webhook_url", "")
    if getConfigData().get("embed_color") is None:
        updateConfigData("embed_color", "5865F2")
    
    # --- Asynchronous Helper for requests ---
    async def run_in_thread(func, *args, **kwargs):
        """Runs a synchronous function in a separate thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    
    # --- Webhook Sending Function ---
    def send_webhook_message(webhook_url: str, embed_data: dict = None, content: str = None) -> bool:
        """
        Sends a message or embed to a Discord webhook.
        
        Returns:
            True if the message was sent successfully, False otherwise.
        """
        if not webhook_url:
            print("Webhook URL is not configured.", type_="ERROR")
            return False
        if not embed_data and not content:
            print("Webhook requires either content or embed data.", type_="ERROR")
            return False

        payload = {}
        if content:
            payload["content"] = content
        if embed_data:
            payload["embeds"] = [embed_data]

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(webhook_url, headers=headers, data=json.dumps(payload), timeout=10)
            response.raise_for_status()

            if response.status_code == 204:
                print("DM logged to webhook successfully.", type_="INFO")
                return True
            else:
                print(f"Webhook returned unexpected status: {response.status_code}", type_="ERROR")
                return False

        except requests.exceptions.RequestException as e:
            print(f"Error sending DM log to webhook: {e}", type_="ERROR")
            return False
        except Exception as e:
            print(f"Unexpected error during webhook sending: {e}", type_="ERROR")
            return False

    # --- DM Event Listener ---
    @bot.listen('on_message')
    async def log_dm(message):
        # Only process DMs (not guild messages)
        if message.guild:
            return
        
        # Ignore messages from the bot itself or other bots
        if message.author.id == bot.user.id or message.author.bot:
            return
        
        # Check if DM logging is enabled
        if not getConfigData().get("dm_logger_enabled", True):
            return
        
        # Log to console
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] DM from {message.author.name} ({message.author.id}): {message.clean_content}", type_="INFO")
        
        # Log to webhook if configured
        webhook_url = getConfigData().get("dm_webhook_url", "")
        if webhook_url:
            # Create embed for webhook
            embed_data = {
                "title": "New Direct Message",
                "description": f"> {message.clean_content}" if message.clean_content else "> *[No text content]*",
                "color": int(getConfigData().get("embed_color", "5865F2"), 16),
                "fields": [
                    {"name": "From", "value": f"{message.author.name} ({message.author.mention})", "inline": True},
                    {"name": "User ID", "value": str(message.author.id), "inline": True},
                    {"name": "Message Link", "value": f"[Jump to Message]({message.jump_url})", "inline": True},
                    {"name": "Timestamp", "value": timestamp, "inline": False}
                ],
                "footer": {"text": "DM Logger Enhanced"},
                "thumbnail": {"url": str(message.author.avatar.url) if message.author.avatar else ""}
            }
            
            # Handle attachments
            if message.attachments:
                attachment_list = []
                for i, attachment in enumerate(message.attachments[:5]):  # Limit to 5 attachments
                    attachment_list.append(f"[{attachment.filename}]({attachment.url})")
                
                embed_data["fields"].append({
                    "name": "Attachments", 
                    "value": "\n".join(attachment_list), 
                    "inline": False
                })
                
                # Set the first image as the main embed image if it's an image
                first_attachment = message.attachments[0]
                if any(first_attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    embed_data["image"] = {"url": first_attachment.url}
            
            # Send to webhook asynchronously
            try:
                await run_in_thread(send_webhook_message, webhook_url, embed_data)
            except Exception as e:
                print(f"Failed to send DM log to webhook: {e}", type_="ERROR")

    # --- Commands ---
    @bot.command(
        name="setdmwebhook",
        description="Set the webhook URL for DM logging"
    )
    async def set_dm_webhook(ctx, *, webhook_url: str):
        await ctx.message.delete()
        
        if not webhook_url:
            await ctx.send("Please provide a webhook URL.")
            return
        
        if webhook_url.startswith("https://discord.com/api/webhooks/") or webhook_url.startswith("https://discordapp.com/api/webhooks/"):
            updateConfigData("dm_webhook_url", webhook_url.strip())
            await ctx.send("DM webhook URL updated successfully.", delete_after=5)
            print(f"DM webhook URL updated by {ctx.author.name}", type_="SUCCESS")
        else:
            await ctx.send("Invalid webhook URL format. Please provide a valid Discord webhook URL.", delete_after=8)

    @bot.command(
        name="toggledmlog",
        description="Enable or disable DM logging"
    )
    async def toggle_dm_logging(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        current_state = getConfigData().get("dm_logger_enabled", True)
        new_state = not current_state
        updateConfigData("dm_logger_enabled", new_state)
        
        status = "enabled" if new_state else "disabled"
        await ctx.send(f"DM logging {status}.", delete_after=5)
        print(f"DM logging {status} by {ctx.author.name}", type_="INFO")

    @bot.command(
        name="dmlogstatus",
        description="Check the current DM logging status and configuration"
    )
    async def dm_log_status(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        enabled = getConfigData().get("dm_logger_enabled", True)
        webhook_url = getConfigData().get("dm_webhook_url", "")
        
        status_emoji = "Enabled" if enabled else "Disabled"
        webhook_status = "Configured" if webhook_url else "Not set"
        
        status_message = f"""**DM Logger Status**

**Logging:** {status_emoji}
**Webhook:** {webhook_status}
**Console Logging:** Always active when logging is enabled

Use `{getConfigData().get('prefix', '<p>')}toggledmlog` to toggle logging.
Use `{getConfigData().get('prefix', '<p>')}setdmwebhook <url>` to set webhook."""
        
        await ctx.send(status_message, delete_after=15)

    @bot.command(
        name="dmloghelp",
        description="Show help information for the DM Logger script"
    )
    async def dm_log_help(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        help_message = f"""**DM Logger Help**

**Description:**
Logs all direct messages to console and optionally to a Discord webhook.

**Commands:**
`{getConfigData().get('prefix', '<p>')}setdmwebhook <webhook_url>` - Set the webhook URL for DM logging
`{getConfigData().get('prefix', '<p>')}toggledmlog` - Enable or disable DM logging
`{getConfigData().get('prefix', '<p>')}dmlogstatus` - Check current DM logging status and configuration
`{getConfigData().get('prefix', '<p>')}dmloghelp` - Show this help message

**Examples:**
`{getConfigData().get('prefix', '<p>')}setdmwebhook https://discord.com/api/webhooks/123456789/abc123`
`{getConfigData().get('prefix', '<p>')}toggledmlog`
`{getConfigData().get('prefix', '<p>')}dmlogstatus`

**Features:**
- Automatically logs all incoming DMs to console with timestamp and user info
- Optional webhook logging with rich embeds including user avatar and message link
- Handles file attachments and displays image previews
- Toggle logging on/off as needed
- Does not log your own messages or messages from other bots

**Setup:**
1. Load the script (logging to console starts automatically)
2. Use `setdmwebhook` command to configure webhook logging (optional)
3. Use `dmlogstatus` to verify configuration"""
        
        await ctx.send(help_message, delete_after=30)

# Call the script function to initialize
script_function()
