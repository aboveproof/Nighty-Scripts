def script_function():
    BASE_DIR = Path(getScriptsPath()) / "json"
    IGNORED_USERS_FILE = BASE_DIR / "ignored_users.json"
    
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize ignored users file
    if not IGNORED_USERS_FILE.exists():
        with open(IGNORED_USERS_FILE, "w") as f:
            json.dump([], f, indent=4)
    
    def load_ignored_users():
        """Load the list of ignored user IDs."""
        try:
            with open(IGNORED_USERS_FILE, "r") as f:
                data = json.load(f)
                return [str(uid) for uid in data] if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            print("Error loading ignored users file", type_="ERROR")
            return []
    
    def save_ignored_users(user_ids):
        """Save the list of ignored user IDs."""
        try:
            with open(IGNORED_USERS_FILE, "w") as f:
                json.dump(user_ids, f, indent=4)
            return True
        except IOError as e:
            print(f"Error saving ignored users: {e}", type_="ERROR")
            return False
    
    def extract_user_id(args):
        """Extract user ID from mention or direct ID input."""
        if not args:
            return None
        
        # Check for mention format <@123456789> or <@!123456789>
        mention_match = re.match(r'<@!?(\d+)>', args.strip())
        if mention_match:
            return mention_match.group(1)
        
        # Check if it's a direct ID (all digits)
        direct_id = args.strip().split()[0]
        if direct_id.isdigit():
            return direct_id
        
        return None
    
    @bot.command(
        name="block",
        aliases=["b"],
        usage="<@user or user_id>",
        description="Block a user using Discord's native block feature"
    )
    async def block_user(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not args:
            await ctx.send("> Please provide a user mention or ID to block.", delete_after=5)
            return
        
        user_id = extract_user_id(args)
        if not user_id:
            await ctx.send("> Invalid user mention or ID format.", delete_after=5)
            return
        
        # Check if already blocked to prevent errors
        try:
            async for relationship in bot.user.relationships:
                if str(relationship.user.id) == user_id and relationship.type.name == "blocked":
                    await ctx.send(f"> User `{user_id}` is already blocked.", delete_after=5)
                    return
        except Exception as e:
            print(f"Error checking block status: {e}", type_="ERROR")
        
        try:
            # Attempt to fetch the user
            user = await bot.fetch_user(int(user_id))
            
            # Block the user via Discord API
            await user.block()
            
            await ctx.send(f"> Successfully blocked **{user.name}** (`{user_id}`)", delete_after=5)
            print(f"Blocked user: {user.name} ({user_id})", type_="SUCCESS")
            
        except ValueError:
            await ctx.send("> Invalid user ID format.", delete_after=5)
        except Exception as e:
            await ctx.send(f"> Failed to block user: {str(e)}", delete_after=5)
            print(f"Error blocking user {user_id}: {e}", type_="ERROR")
    
    @bot.command(
        name="unblock",
        aliases=["ub"],
        usage="<@user or user_id>",
        description="Unblock a previously blocked user"
    )
    async def unblock_user(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not args:
            await ctx.send("> Please provide a user mention or ID to unblock.", delete_after=5)
            return
        
        user_id = extract_user_id(args)
        if not user_id:
            await ctx.send("> Invalid user mention or ID format.", delete_after=5)
            return
        
        try:
            # Attempt to fetch the user
            user = await bot.fetch_user(int(user_id))
            
            # Unblock the user via Discord API
            await user.unblock()
            
            await ctx.send(f"> Successfully unblocked **{user.name}** (`{user_id}`)", delete_after=5)
            print(f"Unblocked user: {user.name} ({user_id})", type_="SUCCESS")
            
        except ValueError:
            await ctx.send("> Invalid user ID format.", delete_after=5)
        except Exception as e:
            await ctx.send(f"> Failed to unblock user: {str(e)}", delete_after=5)
            print(f"Error unblocking user {user_id}: {e}", type_="ERROR")
    
    @bot.command(
        name="ignore",
        aliases=["ig"],
        usage="<@user or user_id>",
        description="Ignore a user's messages (uses Discord's suppress feature)"
    )
    async def ignore_user(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not args:
            await ctx.send("> Please provide a user mention or ID to ignore.", delete_after=5)
            return
        
        user_id = extract_user_id(args)
        if not user_id:
            await ctx.send("> Invalid user mention or ID format.", delete_after=5)
            return
        
        # Check if already ignored to prevent errors
        try:
            async for relationship in bot.user.relationships:
                if str(relationship.user.id) == user_id and relationship.type.name == "implicit":
                    await ctx.send(f"> User `{user_id}` is already ignored.", delete_after=5)
                    return
        except Exception as e:
            print(f"Error checking ignore status: {e}", type_="ERROR")
        
        try:
            # Attempt to fetch the user
            user = await bot.fetch_user(int(user_id))
            
            # Ignore the user via Discord API (suppress messages)
            await user.ignore()
            
            await ctx.send(f"> Successfully ignored **{user.name}** (`{user_id}`)", delete_after=5)
            print(f"Ignored user: {user.name} ({user_id})", type_="SUCCESS")
            
        except ValueError:
            await ctx.send("> Invalid user ID format.", delete_after=5)
        except AttributeError:
            await ctx.send("> Ignore feature may not be available in this Discord version.", delete_after=5)
        except Exception as e:
            await ctx.send(f"> Failed to ignore user: {str(e)}", delete_after=5)
            print(f"Error ignoring user {user_id}: {e}", type_="ERROR")
    
    @bot.command(
        name="unignore",
        aliases=["uig"],
        usage="<@user or user_id>",
        description="Remove a user from your ignore list"
    )
    async def unignore_user(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        if not args:
            await ctx.send("> Please provide a user mention or ID to unignore.", delete_after=5)
            return
        
        user_id = extract_user_id(args)
        if not user_id:
            await ctx.send("> Invalid user mention or ID format.", delete_after=5)
            return
        
        try:
            # Attempt to fetch the user
            user = await bot.fetch_user(int(user_id))
            
            # Unignore the user via Discord API
            await user.unignore()
            
            await ctx.send(f"> Successfully unignored **{user.name}** (`{user_id}`)", delete_after=5)
            print(f"Unignored user: {user.name} ({user_id})", type_="SUCCESS")
            
        except ValueError:
            await ctx.send("> Invalid user ID format.", delete_after=5)
        except AttributeError:
            await ctx.send("> Unignore feature may not be available in this Discord version.", delete_after=5)
        except Exception as e:
            await ctx.send(f"> Failed to unignore user: {str(e)}", delete_after=5)
            print(f"Error unignoring user {user_id}: {e}", type_="ERROR")
    
    @bot.command(
        name="blocklist",
        aliases=["bl", "blocks"],
        description="View your list of blocked users"
    )
    async def view_blocklist(ctx):
        await ctx.message.delete()
        
        try:
            # Fetch blocked users from Discord
            blocked_users = []
            async for relationship in bot.user.relationships:
                if relationship.type.name == "blocked":
                    blocked_users.append(f"> • **{relationship.user.name}** (`{relationship.user.id}`)")
            
            if not blocked_users:
                await ctx.send("> Your block list is empty.", delete_after=5)
                return
            
            blocklist_text = "\n".join(blocked_users)
            await ctx.send(f"> **Blocked Users ({len(blocked_users)}):**\n{blocklist_text}", delete_after=15)
            
        except Exception as e:
            await ctx.send(f"> Failed to retrieve block list: {str(e)}", delete_after=5)
            print(f"Error retrieving block list: {e}", type_="ERROR")
    
    @bot.command(
        name="ignorelist",
        aliases=["il", "ignores"],
        description="View your list of ignored users"
    )
    async def view_ignorelist(ctx):
        await ctx.message.delete()
        
        try:
            # Fetch ignored users from Discord relationships
            ignored_users = []
            async for relationship in bot.user.relationships:
                if relationship.type.name == "implicit":
                    ignored_users.append(f"> • **{relationship.user.name}** (`{relationship.user.id}`)")
            
            if not ignored_users:
                await ctx.send("> Your ignore list is empty.", delete_after=5)
                return
            
            ignorelist_text = "\n".join(ignored_users)
            await ctx.send(f"> **Ignored Users ({len(ignored_users)}):**\n{ignorelist_text}", delete_after=15)
            
        except Exception as e:
            await ctx.send(f"> Failed to retrieve ignore list: {str(e)}", delete_after=5)
            print(f"Error retrieving ignore list: {e}", type_="ERROR")
    
    @bot.command(
        name="blockhelp",
        aliases=["bhelp", "bh"],
        description="Display help information for Block & Ignore Manager"
    )
    async def block_help(ctx):
        await ctx.message.delete()
        
        prefix = getConfigData().get('prefix', '.')
        
        help_text = f"""

> **BLOCK COMMANDS:**
> `{prefix}block <@user or user_id>` - Block a user using Discord API
> `{prefix}unblock <@user or user_id>` - Unblock a previously blocked user
> `{prefix}blocklist` - View all blocked users

> **IGNORE COMMANDS:**
> `{prefix}ignore <@user or user_id>` - Ignore user's messages (local filter)
> `{prefix}unignore <@user or user_id>` - Remove user from ignore list
> `{prefix}ignorelist` - View all ignored users

> **ALIASES:**
> Block: `{prefix}b` | Unblock: `{prefix}ub`
> Ignore: `{prefix}ig` | Unignore: `{prefix}uig`
> Blocklist: `{prefix}bl` | Ignorelist: `{prefix}il`"""
        
        await ctx.send(help_text, delete_after=30)
    
    
    print("Block & Ignore Manager script loaded successfully.", type_="SUCCESS")

script_function()
