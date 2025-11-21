def weatherScript():
    
    import aiohttp
    import asyncio
    import json
    from pathlib import Path
    from datetime import datetime, timedelta
    
    # Script configuration key prefix
    SCRIPT_KEY = "weather_script"
    
    # Cache for weather data
    weather_cache = {
        "last_update": None,
        "data": None,
        "location_name": None
    }
    
    def script_log(message, level="INFO"):
        """Helper function for consistent logging."""
        # print(f"[Weather] {message}", type_=level)
    
    async def geocode_location(location):
        """
        Converts location name to coordinates using Open-Meteo geocoding API.
        
        Args:
            location: City name, city with state/country
            
        Returns:
            Tuple of (latitude, longitude, location_name) or None on error
        """
        geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(geocode_url, params=params, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if not data.get("results"):
                        script_log(f"Location not found: {location}", level="ERROR")
                        return None
                    
                    result = data["results"][0]
                    lat = result["latitude"]
                    lon = result["longitude"]
                    name = result["name"]
                    country = result.get("country", "")
                    admin1 = result.get("admin1", "")
                    
                    # Build full location name
                    location_parts = [name]
                    if admin1 and admin1 != name:
                        location_parts.append(admin1)
                    if country:
                        location_parts.append(country)
                    full_name = ", ".join(location_parts)
                    
                    # script_log(f"Geocoded {location} to {lat}, {lon}", level="INFO")
                    return (lat, lon, full_name)
                    
        except Exception as e:
            script_log(f"Geocoding error: {e}", level="ERROR")
            return None
    
    async def fetch_weather(latitude, longitude):
        """
        Fetches weather data from Open-Meteo API.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            
        Returns:
            Dict with weather data or None on error
        """
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": "true",
            "temperature_unit": "fahrenheit",
            "windspeed_unit": "mph",
            "timezone": "auto"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(weather_url, params=params, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    # script_log(f"Successfully fetched weather data", level="SUCCESS")
                    return data
                    
        except Exception as e:
            script_log(f"Weather API error: {e}", level="ERROR")
            return None
    
    def get_weather_description(weather_code):
        """Map WMO weather codes to descriptions."""
        weather_descriptions = {
            0: "Clear Sky",
            1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Foggy", 48: "Rime Fog",
            51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
            61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
            71: "Light Snow", 73: "Snow", 75: "Heavy Snow",
            77: "Snow Grains",
            80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
            85: "Light Snow Showers", 86: "Snow Showers",
            95: "Thunderstorm", 96: "Thunderstorm + Hail", 99: "Severe Thunderstorm"
        }
        return weather_descriptions.get(weather_code, "Unknown")
    
    def get_temp_emoji(temp):
        """Get emoji based on temperature."""
        if temp >= 85:
            return "🔥"
        elif temp >= 70:
            return "☀️"
        elif temp >= 50:
            return "⛅"
        elif temp >= 32:
            return "🌥️"
        else:
            return "❄️"
    
    def format_weather_message(data, location_name):
        """Format weather data for Discord message."""
        if not data or "error" in data:
            return None
        
        try:
            current = data.get("current_weather", {})
            temp = round(current.get("temperature", 0))
            wind_speed = round(current.get("windspeed", 0))
            wind_direction = current.get("winddirection", 0)
            weather_code = current.get("weathercode", 0)
            
            description = get_weather_description(weather_code)
            
            # Wind direction to cardinal
            directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                         "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            direction_index = round(wind_direction / 22.5) % 16
            wind_dir = directions[direction_index]
            
            temp_emoji = get_temp_emoji(temp)
            
            message = f"""# {temp_emoji} Weather for {location_name}

**Current Conditions:** {description}
**Temperature:** {temp}°F
**Wind:** {wind_speed} mph {wind_dir}

*Data from Open-Meteo*"""
            
            return message
            
        except Exception as e:
            script_log(f"Error formatting weather data: {e}", level="ERROR")
            return None
    
    async def update_weather_cache():
        """Updates the weather cache for dynamic values."""
        default_location = getConfigData().get(f"{SCRIPT_KEY}_default_location")
        if not default_location:
            script_log("No default location set for dynamic value", level="INFO")
            return
        
        # Check if we need to update (15 minute cache)
        now = datetime.now()
        if weather_cache["last_update"]:
            time_diff = now - weather_cache["last_update"]
            if time_diff < timedelta(minutes=15):
                # script_log("Using cached weather data", level="INFO")
                return
        
        # script_log(f"Updating weather cache for {default_location}", level="INFO")
        
        # Geocode and fetch weather
        geocode_result = await geocode_location(default_location)
        if not geocode_result:
            return
        
        lat, lon, full_name = geocode_result
        data = await fetch_weather(lat, lon)
        
        if data and "current_weather" in data:
            weather_cache["data"] = data
            weather_cache["location_name"] = full_name
            weather_cache["last_update"] = now
            # script_log("Weather cache updated successfully", level="SUCCESS")
    
    def weather_temp_value():
        """Dynamic value: Returns just the temperature (e.g., '72°F')."""
        if not weather_cache["data"]:
            return "N/A"
        
        try:
            current = weather_cache["data"].get("current_weather", {})
            temp = round(current.get("temperature", 0))
            return f"{temp}°F"
        except Exception:
            return "N/A"
    
    def weather_full_value():
        """Dynamic value: Returns location and temperature with condition (e.g., 'Atlanta: 72°F Clear Sky')."""
        if not weather_cache["data"] or not weather_cache["location_name"]:
            return "No weather data"
        
        try:
            current = weather_cache["data"].get("current_weather", {})
            temp = round(current.get("temperature", 0))
            weather_code = current.get("weathercode", 0)
            description = get_weather_description(weather_code)
            
            # Use just the city name (first part)
            city = weather_cache["location_name"].split(",")[0]
            
            return f"{city}: {temp}°F {description}"
        except Exception:
            return "Weather unavailable"
    
    def weather_emoji_value():
        """Dynamic value: Returns just the temperature emoji."""
        if not weather_cache["data"]:
            return "🌡️"
        
        try:
            current = weather_cache["data"].get("current_weather", {})
            temp = round(current.get("temperature", 0))
            return get_temp_emoji(temp)
        except Exception:
            return "🌡️"
    
    # Register dynamic values
    addDRPCValue("weather_temp", weather_temp_value)
    addDRPCValue("weather_full", weather_full_value)
    addDRPCValue("weather_emoji", weather_emoji_value)
    
    @bot.command(
        name="weather",
        aliases=["w", "temp"],
        usage="[location] OR set <location> OR refresh",
        description="Get current weather in Fahrenheit"
    )
    async def weather_command(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        args = args.strip()
        
        # Handle 'set' subcommand
        if args.lower().startswith("set "):
            location = args[4:].strip()
            if not location:
                await ctx.send("Please provide a location to set.\nExample: `<p>weather set Atlanta, GA`")
                return
            
            updateConfigData(f"{SCRIPT_KEY}_default_location", location)
            await ctx.send(f"Default location set to: **{location}**\nDynamic values will now use this location.")
            script_log(f"Default location set to: {location}", level="INFO")
            
            # Clear cache to force refresh
            weather_cache["last_update"] = None
            return
        
        # Handle 'refresh' subcommand
        if args.lower() == "refresh":
            weather_cache["last_update"] = None
            await update_weather_cache()
            if weather_cache["data"]:
                await ctx.send(f"Weather data refreshed!\n`{weather_full_value()}`")
            else:
                await ctx.send("Failed to refresh weather data. Make sure you've set a default location.")
            return
        
        # Determine location to use
        if args:
            location = args
        else:
            location = getConfigData().get(f"{SCRIPT_KEY}_default_location")
            if not location:
                await ctx.send("No location provided and no default set.\nUsage: `<p>weather <location>` or `<p>weather set <location>`")
                return
        
        # Show loading message
        status_msg = await ctx.send(f"Fetching weather for **{location}**...")
        
        # Geocode the location
        geocode_result = await geocode_location(location)
        if not geocode_result:
            await status_msg.edit(content=f"Location not found: **{location}**\nTry being more specific (e.g., 'Atlanta, GA')")
            return
        
        lat, lon, full_name = geocode_result
        
        # Fetch weather data
        data = await fetch_weather(lat, lon)
        
        if not data or "error" in data:
            await status_msg.edit(content="Failed to fetch weather data. Please try again.")
            return
        
        # Format and send weather data
        weather_msg = format_weather_message(data, full_name)
        if weather_msg:
            # Disable private mode temporarily
            current_private = getConfigData().get("private")
            updateConfigData("private", False)
            
            try:
                await forwardEmbedMethod(
                    channel_id=ctx.channel.id,
                    content=weather_msg,
                    title="Current Weather"
                )
                await status_msg.delete()
            except Exception as e:
                script_log(f"Failed to send weather embed: {e}", level="ERROR")
                await status_msg.edit(content=weather_msg)
            finally:
                updateConfigData("private", current_private)
        else:
            await status_msg.edit(content="Failed to format weather data. Check logs.")
    
    # Background task to keep weather cache updated
    async def weather_update_loop():
        """Background task that updates weather cache every 15 minutes."""
        while True:
            try:
                await update_weather_cache()
            except Exception as e:
                script_log(f"Error in weather update loop: {e}", level="ERROR")
            
            # Wait 15 minutes before next update
            await asyncio.sleep(900)  # 900 seconds = 15 minutes
    
    # Start the background update task
    bot.loop.create_task(weather_update_loop())
    
    # script_log("Weather script initialized with dynamic values: {weather_temp}, {weather_full}, {weather_emoji}", level="SUCCESS")

weatherScript()
