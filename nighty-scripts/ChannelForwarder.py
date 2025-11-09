import asyncio
import json
from datetime import datetime
from pathlib import Path

def script_function():
    
    # Configuration keys
    CONFIG_KEYS = {
        "source_token": "forwarder_source_token",
        "source_channel": "forwarder_source_channel",
        "dest_type": "forwarder_dest_type",  # "channel" or "webhook"
        "dest_channel": "forwarder_dest_channel",
        "dest_webhook": "forwarder_dest_webhook",
        "is_running": "forwarder_is_running",
        "last_message_id": "forwarder_last_message_id"
    }
    
    # Initialize config defaults
    for key in CONFIG_KEYS.values():
        if getConfigData().get(key) is None:
            if key == "forwarder_dest_type":
                updateConfigData(key, "webhook")
            elif key == "forwarder_is_running":
                updateConfigData(key, False)
            else:
                updateConfigData(key, "")
    
    # Global task reference
    forwarder_task = None
    
    async def send_webhook_message_async(webhook_url, content=None, embed_data=None, username=None, avatar_url=None):
        """Send message to Discord webhook using requests library in thread"""
        if not webhook_url:
            return False
            
        payload = {}
        if content:
            payload["content"] = content
        if embed_data:
            payload["embeds"] = [embed_data]
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url
            
        try:
            import requests
            
            def send_webhook_sync():
                headers = {"Content-Type": "application/json"}
                response = requests.post(webhook_url, headers=headers, json=payload, timeout=10)
                return response.status_code == 204
            
            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, send_webhook_sync)
            return result
            
        except Exception as e:
            print(f"Webhook error: {e}", type_="ERROR")
            import traceback
            traceback.print_exc()
            return False
    
    async def fetch_messages(token, channel_id, after=None):
        """Fetch messages from source channel using bot's http client"""
        url = f"/channels/{channel_id}/messages"
        params = {"limit": 50}
        if after:
            params["after"] = after
        
        # Build query string manually
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{query_string}"
            
        try:
            import discord
            # Create a custom route with the token
            route = discord.http.Route('GET', full_url)
            
            # Temporarily store original token
            original_token = bot.http.token
            
            # Use the provided token for this request
            bot.http.token = token
            
            try:
                response = await bot.http.request(route)
                return response
            finally:
                # Restore original token
                bot.http.token = original_token
                
        except Exception as e:
            print(f"Error fetching messages: {e}", type_="ERROR")
            import traceback
            traceback.print_exc()
            return None
    
    async def format_message_for_forward(message_data):
        """Format message data for forwarding"""
        author = message_data.get("author", {})
        content = message_data.get("content", "")
        embeds = message_data.get("embeds", [])
        attachments = message_data.get("attachments", [])
        timestamp = message_data.get("timestamp", "")
        
        # Create formatted message
        formatted_content = f"**{author.get('username', 'Unknown')}#{author.get('discriminator', '0000')}**\n"
        
        if content:
            formatted_content += f"{content}\n"
        
        if attachments:
            formatted_content += "\n**Attachments:**\n"
            for att in attachments:
                formatted_content += f"[{att.get('filename', 'file')}]({att.get('url', '')})\n"
        
        # Create embed for webhook
        embed = {
            "description": content if content else "_No text content_",
            "color": 0x5865F2,
            "author": {
                "name": f"{author.get('username', 'Unknown')}#{author.get('discriminator', '0000')}",
                "icon_url": f"https://cdn.discordapp.com/avatars/{author.get('id', '')}/{author.get('avatar', '')}.png"
            },
            "timestamp": timestamp,
            "footer": {"text": "Message Forwarder"}
        }
        
        if attachments and attachments[0].get("content_type", "").startswith("image"):
            embed["image"] = {"url": attachments[0].get("url", "")}
        
        return formatted_content, embed
    
    async def forward_message(message_data, dest_type, dest_channel, dest_webhook):
        """Forward a single message to destination"""
        try:
            formatted_content, embed = await format_message_for_forward(message_data)
            author = message_data.get("author", {})
            
            if dest_type == "webhook" and dest_webhook:
                success = await send_webhook_message_async(
                    dest_webhook,
                    embed_data=embed,
                    username=f"{author.get('username', 'Unknown')}",
                    avatar_url=f"https://cdn.discordapp.com/avatars/{author.get('id', '')}/{author.get('avatar', '')}.png"
                )
                return success
            elif dest_type == "channel" and dest_channel:
                try:
                    channel = bot.get_channel(int(dest_channel))
                    if channel:
                        await channel.send(formatted_content[:2000])
                        return True
                except Exception as e:
                    print(f"Error sending to channel: {e}", type_="ERROR")
                    return False
            
            return False
        except Exception as e:
            print(f"Error forwarding message: {e}", type_="ERROR")
            return False
    
    async def monitor_channel():
        """Main monitoring loop"""
        print("Message forwarder started", type_="INFO")
        
        source_token = getConfigData().get(CONFIG_KEYS["source_token"])
        source_channel = getConfigData().get(CONFIG_KEYS["source_channel"])
        dest_type = getConfigData().get(CONFIG_KEYS["dest_type"])
        dest_channel = getConfigData().get(CONFIG_KEYS["dest_channel"])
        dest_webhook = getConfigData().get(CONFIG_KEYS["dest_webhook"])
        last_message_id = getConfigData().get(CONFIG_KEYS["last_message_id"])
        
        # If no last_message_id exists, get the most recent message ID to start from
        if not last_message_id:
            print("First run - getting current message ID to start monitoring from", type_="INFO")
            initial_messages = await fetch_messages(source_token, source_channel, None)
            if initial_messages and len(initial_messages) > 0:
                last_message_id = initial_messages[0]["id"]
                updateConfigData(CONFIG_KEYS["last_message_id"], last_message_id)
                print(f"Starting from message ID: {last_message_id}", type_="INFO")
        
        while True:
            # Check if we should still be running
            if not getConfigData().get(CONFIG_KEYS["is_running"], False):
                print("Forwarder stopped by config check", type_="INFO")
                break
                
            try:
                messages = await fetch_messages(source_token, source_channel, last_message_id)
                
                if messages:
                    # Process messages in reverse order (oldest first)
                    for message in reversed(messages):
                        if message["id"] != last_message_id:
                            success = await forward_message(message, dest_type, dest_channel, dest_webhook)
                            if success:
                                last_message_id = message["id"]
                                updateConfigData(CONFIG_KEYS["last_message_id"], last_message_id)
                                print(f"Forwarded message {message['id']}", type_="SUCCESS")
                
                # Wait before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Monitor loop error: {e}", type_="ERROR")
                await asyncio.sleep(5)
        
        print("Message forwarder stopped", type_="INFO")
    
    def start_monitoring():
        """Start the monitoring task"""
        nonlocal forwarder_task
        
        try:
            # Check if already running
            if forwarder_task and not forwarder_task.done():
                print("Forwarder already running", type_="ERROR")
                return False
            
            # Check config state
            current_state = getConfigData().get(CONFIG_KEYS["is_running"], False)
            print(f"Current config state before start: {current_state}", type_="INFO")
            
            print("Setting is_running to True...", type_="INFO")
            updateConfigData(CONFIG_KEYS["is_running"], True)
            
            # Verify it was set
            new_state = getConfigData().get(CONFIG_KEYS["is_running"], False)
            print(f"New config state after update: {new_state}", type_="INFO")
            
            print("Creating forwarder task...", type_="INFO")
            forwarder_task = asyncio.create_task(monitor_channel())
            print(f"Forwarder task created: {forwarder_task}", type_="SUCCESS")
            return True
        except Exception as e:
            print(f"Error starting monitoring: {e}", type_="ERROR")
            import traceback
            traceback.print_exc()
            updateConfigData(CONFIG_KEYS["is_running"], False)
            return False
    
    def stop_monitoring():
        """Stop the monitoring task"""
        nonlocal forwarder_task
        
        try:
            print("Setting is_running to False...", type_="INFO")
            updateConfigData(CONFIG_KEYS["is_running"], False)
            
            # Verify it was set
            new_state = getConfigData().get(CONFIG_KEYS["is_running"], False)
            print(f"Config state after stop: {new_state}", type_="INFO")
            
            if forwarder_task and not forwarder_task.done():
                print(f"Task exists and is running: {forwarder_task}", type_="INFO")
            else:
                print(f"Task state: {forwarder_task}", type_="INFO")
                
        except Exception as e:
            print(f"Error stopping monitoring: {e}", type_="ERROR")
    
    # Create the UI Tab directly
    tab = Tab(name="Channel Forwarder", icon="message")
        
    # Main container
    main_container = tab.create_container(type="rows")
        
    # Title card
    title_card = main_container.create_card()
    title_card.create_ui_element(UI.Text, 
        content="Channel Message Forwarder", 
        size="2xl", 
        weight="bold",
        align="center"
    )
    title_card.create_ui_element(UI.Text,
        content="Forward messages from any channel to your destination",
        size="sm",
        color="#888888",
        align="center"
    )
        
    # Configuration container
    config_container = main_container.create_container(type="columns")
        
    # Source configuration card
    source_card = config_container.create_card()
    source_card.create_ui_element(UI.Text,
        content="Source Configuration",
        size="xl",
        weight="bold"
    )
    
    token_input = source_card.create_ui_element(UI.Input,
        label="Discord User Token",
        placeholder="MTk4NjIyNDgzNDcxOTI1MjQ4.Gh2jsi...",
        value=getConfigData().get(CONFIG_KEYS["source_token"], ""),
        full_width=True,
        description="Token of account that can see the source channel"
    )
    
    source_channel_input = source_card.create_ui_element(UI.Input,
        label="Source Channel ID",
        placeholder="123456789012345678",
        value=getConfigData().get(CONFIG_KEYS["source_channel"], ""),
        full_width=True,
        description="ID of the channel to monitor"
    )
        
    # Destination configuration card
    dest_card = config_container.create_card()
    dest_card.create_ui_element(UI.Text,
        content="Destination Configuration",
        size="xl",
        weight="bold"
    )
    
    dest_type_select = dest_card.create_ui_element(UI.Select,
        label="Destination Type",
        items=[
            {"id": "webhook", "title": "Webhook (Recommended)"},
            {"id": "channel", "title": "Channel"}
        ],
        selected_items=[getConfigData().get(CONFIG_KEYS["dest_type"], "webhook")],
        mode="single",
        full_width=True,
        description="How to forward messages"
    )
    
    webhook_input = dest_card.create_ui_element(UI.Input,
        label="Webhook URL",
        placeholder="https://discord.com/api/webhooks/...",
        value=getConfigData().get(CONFIG_KEYS["dest_webhook"], ""),
        full_width=True,
        visible=getConfigData().get(CONFIG_KEYS["dest_type"]) == "webhook"
    )
    
    channel_input = dest_card.create_ui_element(UI.Input,
        label="Destination Channel ID",
        placeholder="123456789012345678",
        value=getConfigData().get(CONFIG_KEYS["dest_channel"], ""),
        full_width=True,
        visible=getConfigData().get(CONFIG_KEYS["dest_type"]) == "channel"
    )
        
    # Control card
    control_card = main_container.create_card(horizontal_align="center")
    
    status_text = control_card.create_ui_element(UI.Text,
        content="Status: Stopped" if not getConfigData().get(CONFIG_KEYS["is_running"]) else "Status: Running",
        size="lg",
        weight="bold",
        color="#00FF00" if getConfigData().get(CONFIG_KEYS["is_running"]) else "#FF0000"
    )
    
    button_group = control_card.create_group(type="columns", gap=3)
    
    save_button = button_group.create_ui_element(UI.Button,
        label="Save Configuration",
        variant="solid",
        color="primary"
    )
    
    start_button = button_group.create_ui_element(UI.Button,
        label="Start Monitoring",
        variant="cta",
        disabled=getConfigData().get(CONFIG_KEYS["is_running"], False)
    )
    
    stop_button = button_group.create_ui_element(UI.Button,
        label="Stop Monitoring",
        variant="solid",
        color="danger",
        disabled=not getConfigData().get(CONFIG_KEYS["is_running"], False)
    )
        
    # Event handlers
    def on_dest_type_change(selected):
        dest_type = selected[0] if selected else "webhook"
        webhook_input.visible = dest_type == "webhook"
        channel_input.visible = dest_type == "channel"
    
    def save_configuration():
        save_button.loading = True
        
        try:
            # Save all configuration
            updateConfigData(CONFIG_KEYS["source_token"], token_input.value)
            updateConfigData(CONFIG_KEYS["source_channel"], source_channel_input.value)
            updateConfigData(CONFIG_KEYS["dest_type"], dest_type_select.selected_items[0] if dest_type_select.selected_items else "webhook")
            updateConfigData(CONFIG_KEYS["dest_webhook"], webhook_input.value)
            updateConfigData(CONFIG_KEYS["dest_channel"], channel_input.value)
            
            print("Configuration saved successfully", type_="SUCCESS")
            tab.toast("Success", "Configuration saved successfully", "SUCCESS")
        except Exception as e:
            print(f"Error saving configuration: {e}", type_="ERROR")
            tab.toast("Error", f"Failed to save: {e}", "ERROR")
        finally:
            save_button.loading = False
    
    async def start_forwarder():
        # Validate configuration
        if not token_input.value or not source_channel_input.value:
            tab.toast("Error", "Please configure source settings", "ERROR")
            return
        
        dest_type = dest_type_select.selected_items[0] if dest_type_select.selected_items else "webhook"
        if dest_type == "webhook" and not webhook_input.value:
            tab.toast("Error", "Please provide webhook URL", "ERROR")
            return
        elif dest_type == "channel" and not channel_input.value:
            tab.toast("Error", "Please provide channel ID", "ERROR")
            return
        
        # Save configuration first
        save_configuration()
        
        # Add a small delay to ensure config is saved
        await asyncio.sleep(0.1)
        
        # Start monitoring
        if start_monitoring():
            start_button.disabled = True
            stop_button.disabled = False
            status_text.content = "Status: Running"
            status_text.color = "#00FF00"
            tab.toast("Success", "Forwarder started successfully", "SUCCESS")
            print("UI updated - forwarder should be running", type_="INFO")
        else:
            tab.toast("Error", "Failed to start forwarder", "ERROR")
    
    async def stop_forwarder():
        print("Stop button pressed", type_="INFO")
        stop_monitoring()
        
        # Wait for task to finish
        await asyncio.sleep(0.5)
        
        start_button.disabled = False
        stop_button.disabled = True
        status_text.content = "Status: Stopped"
        status_text.color = "#FF0000"
        tab.toast("Info", "Forwarder stopped", "INFO")
        print("UI updated - forwarder stopped", type_="INFO")
    
    # Assign event handlers
    dest_type_select.onChange = on_dest_type_change
    save_button.onClick = save_configuration
    start_button.onClick = start_forwarder
    stop_button.onClick = stop_forwarder
    
    # Render the tab
    tab.render()
    
    print("Channel Forwarder script loaded", type_="SUCCESS")

script_function()
