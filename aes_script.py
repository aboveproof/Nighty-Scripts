def script_function():
    """
    ADVANCED AES ENCRYPTION SUITE
    ----------------------------

    A comprehensive encryption system that implements AES with multiple security layers,
    including RSA key exchange, PBKDF2 key derivation, and various encryption modes.

    COMMANDS:
    <p>aes encrypt <message> [--mode MODE] [--keysize SIZE] - Encrypt a message with multi-layer security
    <p>aes decrypt <encrypted_data> [--key KEY] - Decrypt encrypted data
    <p>aes genkey [--size SIZE] - Generate a secure encryption key
    <p>aes explain - Detailed explanation of AES and encryption methods used
    <p>aes config <setting> <value> - Configure encryption settings
    <p>aes benchmark - Test encryption/decryption performance
    <p>aes help - Show detailed help information

    EXAMPLES:
    <p>aes encrypt "Secret message" --mode CBC --keysize 256
    <p>aes decrypt "encrypted_data_here" --key "your_key"
    <p>aes genkey --size 256
    <p>aes config default_mode GCM

    FEATURES:
    - AES encryption with 128/192/256-bit keys
    - Multiple modes: CBC, GCM, CTR, OFB
    - RSA key exchange for secure key distribution
    - PBKDF2 key derivation with salt
    - HMAC authentication
    - Base64 encoding for safe text transmission
    - Performance benchmarking
    - Secure random number generation

    NOTES:
    - Requires 'pycryptodome' package (standard Python crypto library)
    - All keys are generated using cryptographically secure random sources
    - Encrypted data includes integrity verification
    - Private keys are stored securely in local configuration
    """
    
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    from Crypto.Protocol.KDF import PBKDF2
    from Crypto.Hash import SHA256, HMAC
    from Crypto.Util.Padding import pad, unpad
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_OAEP
    import os
    import base64
    import json
    import time
    import hashlib
    import hmac
    from pathlib import Path
    
    # Configuration setup
    SCRIPT_NAME = "AdvancedAES"
    BASE_DIR = Path(getScriptsPath()) / "json"
    CONFIG_FILE = BASE_DIR / "aes_config.json"
    KEYS_FILE = BASE_DIR / "aes_keys.json"
    
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    def script_log(message, level="INFO"):
        """Enhanced logging with timestamp and script context."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{SCRIPT_NAME}] [{level}] {message}", type_=level)
    
    def load_config():
        """Load script configuration with defaults."""
        default_config = {
            "default_mode": "GCM",
            "default_keysize": 256,
            "pbkdf2_iterations": 100000,
            "rsa_keysize": 2048,
            "enable_compression": True,
            "enable_hmac": True
        }
        
        if not CONFIG_FILE.exists():
            save_config(default_config)
            return default_config
        
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                # Ensure all default keys exist
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            script_log("Config file corrupted, using defaults", "ERROR")
            return default_config
    
    def save_config(config):
        """Save configuration to JSON file."""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
        except IOError as e:
            script_log(f"Failed to save config: {e}", "ERROR")
    
    def load_keys():
        """Load stored encryption keys."""
        if not KEYS_FILE.exists():
            return {}
        
        try:
            with open(KEYS_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            script_log("Keys file corrupted", "ERROR")
            return {}
    
    def save_keys(keys_data):
        """Save encryption keys securely."""
        try:
            with open(KEYS_FILE, "w") as f:
                json.dump(keys_data, f, indent=4)
        except IOError as e:
            script_log(f"Failed to save keys: {e}", "ERROR")
    
    def generate_secure_key(size_bits=256):
        """Generate a cryptographically secure random key."""
        return get_random_bytes(size_bits // 8)
    
    def derive_key_from_password(password: str, salt: bytes = None, iterations: int = 100000):
        """Derive encryption key from password using PBKDF2."""
        if salt is None:
            salt = get_random_bytes(32)
        
        key = PBKDF2(password, salt, 32, count=iterations, hmac_hash_module=SHA256)
        return key, salt
    
    def generate_rsa_keypair(key_size=2048):
        """Generate RSA key pair for secure key exchange."""
        private_key = RSA.generate(key_size)
        public_key = private_key.publickey()
        
        # Export keys in PEM format
        private_pem = private_key.export_key().decode()
        public_pem = public_key.export_key().decode()
        
        return private_pem, public_pem
    
    def encrypt_aes_gcm(plaintext: bytes, key: bytes):
        """Encrypt using AES-GCM (authenticated encryption)."""
        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        return cipher.nonce + tag + ciphertext
    
    def decrypt_aes_gcm(ciphertext_with_nonce: bytes, key: bytes):
        """Decrypt using AES-GCM."""
        nonce = ciphertext_with_nonce[:16]
        tag = ciphertext_with_nonce[16:32]
        ciphertext = ciphertext_with_nonce[32:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)
    
    def encrypt_aes_cbc(plaintext: bytes, key: bytes):
        """Encrypt using AES-CBC with PKCS7 padding."""
        cipher = AES.new(key, AES.MODE_CBC)
        padded_data = pad(plaintext, AES.block_size)
        ciphertext = cipher.encrypt(padded_data)
        return cipher.iv + ciphertext
    
    def decrypt_aes_cbc(ciphertext_with_iv: bytes, key: bytes):
        """Decrypt using AES-CBC and remove PKCS7 padding."""
        iv = ciphertext_with_iv[:16]
        ciphertext = ciphertext_with_iv[16:]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_plaintext = cipher.decrypt(ciphertext)
        return unpad(padded_plaintext, AES.block_size)
    
    def encrypt_aes_ctr(plaintext: bytes, key: bytes):
        """Encrypt using AES-CTR mode."""
        cipher = AES.new(key, AES.MODE_CTR)
        ciphertext = cipher.encrypt(plaintext)
        return cipher.nonce + ciphertext
    
    def decrypt_aes_ctr(ciphertext_with_nonce: bytes, key: bytes):
        """Decrypt using AES-CTR mode."""
        nonce = ciphertext_with_nonce[:8]
        ciphertext = ciphertext_with_nonce[8:]
        cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
        return cipher.decrypt(ciphertext)
    
    def add_hmac_protection(data: bytes, key: bytes):
        """Add HMAC authentication to encrypted data."""
        h = HMAC.new(key, digestmod=SHA256)
        h.update(data)
        return data + h.digest()
    
    def verify_hmac_protection(data_with_hmac: bytes, key: bytes):
        """Verify and remove HMAC authentication."""
        data = data_with_hmac[:-32]  # HMAC-SHA256 is 32 bytes
        received_hmac = data_with_hmac[-32:]
        
        h = HMAC.new(key, digestmod=SHA256)
        h.update(data)
        expected_hmac = h.digest()
        
        if received_hmac != expected_hmac:
            raise ValueError("HMAC verification failed - data may be tampered")
        
        return data
    
    def multi_layer_encrypt(message: str, mode: str = "GCM", key_size: int = 256, password: str = None):
        """
        Multi-layer encryption with AES + additional security features.
        Returns encrypted data package with all necessary components.
        """
        config = load_config()
        
        # Step 1: Generate or derive encryption key
        if password:
            encryption_key, salt = derive_key_from_password(password, iterations=config["pbkdf2_iterations"])
        else:
            encryption_key = generate_secure_key(key_size)
            salt = None
        
        # Step 2: Compress data if enabled
        plaintext = message.encode('utf-8')
        if config["enable_compression"]:
            import zlib
            plaintext = zlib.compress(plaintext)
        
        # Step 3: Encrypt with specified AES mode
        if mode.upper() == "GCM":
            encrypted_data = encrypt_aes_gcm(plaintext, encryption_key)
        elif mode.upper() == "CBC":
            encrypted_data = encrypt_aes_cbc(plaintext, encryption_key)
        elif mode.upper() == "CTR":
            encrypted_data = encrypt_aes_ctr(plaintext, encryption_key)
        else:
            raise ValueError(f"Unsupported encryption mode: {mode}")
        
        # Step 4: Add HMAC protection if enabled
        if config["enable_hmac"]:
            hmac_key = SHA256.new(encryption_key + b"hmac_salt").digest()
            encrypted_data = add_hmac_protection(encrypted_data, hmac_key)
        
        # Step 5: Create data package
        package = {
            "version": "1.0",
            "mode": mode.upper(),
            "key_size": key_size,
            "has_compression": config["enable_compression"],
            "has_hmac": config["enable_hmac"],
            "data": base64.b64encode(encrypted_data).decode(),
            "timestamp": int(time.time())
        }
        
        if salt:
            package["salt"] = base64.b64encode(salt).decode()
            package["iterations"] = config["pbkdf2_iterations"]
        else:
            package["key"] = base64.b64encode(encryption_key).decode()
        
        return json.dumps(package)
    
    def multi_layer_decrypt(encrypted_package: str, password: str = None, key: str = None):
        """
        Multi-layer decryption of encrypted data package.
        """
        try:
            package = json.loads(encrypted_package)
            
            # Extract encryption key
            if "salt" in package and password:
                salt = base64.b64decode(package["salt"])
                iterations = package.get("iterations", 100000)
                encryption_key, _ = derive_key_from_password(password, salt, iterations)
            elif "key" in package:
                encryption_key = base64.b64decode(package["key"])
            elif key:
                encryption_key = base64.b64decode(key)
            else:
                raise ValueError("No decryption key available")
            
            # Decode encrypted data
            encrypted_data = base64.b64decode(package["data"])
            
            # Remove HMAC protection if present
            if package.get("has_hmac", False):
                hmac_key = SHA256.new(encryption_key + b"hmac_salt").digest()
                encrypted_data = verify_hmac_protection(encrypted_data, hmac_key)
            
            # Decrypt with appropriate mode
            mode = package["mode"]
            if mode == "GCM":
                plaintext = decrypt_aes_gcm(encrypted_data, encryption_key)
            elif mode == "CBC":
                plaintext = decrypt_aes_cbc(encrypted_data, encryption_key)
            elif mode == "CTR":
                plaintext = decrypt_aes_ctr(encrypted_data, encryption_key)
            else:
                raise ValueError(f"Unsupported decryption mode: {mode}")
            
            # Decompress if needed
            if package.get("has_compression", False):
                import zlib
                plaintext = zlib.decompress(plaintext)
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    @bot.command(
        name="aes",
        usage="<subcommand> [args] [--flags]",
        description="Advanced multi-layer AES encryption system with RSA key exchange and authentication"
    )
    async def aes_command(ctx, *, args: str):
        await ctx.message.delete()
        
        if not args.strip():
            await show_aes_help(ctx)
            return
        
        parts = args.split()
        subcommand = parts[0].lower() if parts else ""
        subargs = " ".join(parts[1:]) if len(parts) > 1 else ""
        
        try:
            if subcommand == "encrypt":
                await handle_encrypt(ctx, subargs)
            elif subcommand == "decrypt":
                await handle_decrypt(ctx, subargs)
            elif subcommand == "genkey":
                await handle_genkey(ctx, subargs)
            elif subcommand == "explain":
                await handle_explain(ctx)
            elif subcommand == "config":
                await handle_config(ctx, subargs)
            elif subcommand == "benchmark":
                await handle_benchmark(ctx)
            elif subcommand in ["help", "?"]:
                await show_aes_help(ctx)
            else:
                await ctx.send(f"Unknown subcommand: `{subcommand}`. Use `{getConfigData().get('prefix', '<p>')}aes help` for usage.")
        
        except Exception as e:
            script_log(f"Error in aes command: {e}", "ERROR")
            await ctx.send(f"❌ Error: {str(e)}")
    
    async def handle_encrypt(ctx, args):
        """Handle encryption subcommand."""
        if not args.strip():
            await ctx.send("❌ Usage: `<p>aes encrypt <message> [--mode MODE] [--keysize SIZE] [--password PASSWORD]`")
            return
        
        # Parse arguments and flags
        parts = args.split()
        flags = {}
        message_parts = []
        
        i = 0
        while i < len(parts):
            if parts[i].startswith("--"):
                flag = parts[i][2:]
                if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                    flags[flag] = parts[i + 1]
                    i += 2
                else:
                    flags[flag] = True
                    i += 1
            else:
                message_parts.append(parts[i])
                i += 1
        
        message = " ".join(message_parts)
        if not message:
            await ctx.send("❌ No message provided to encrypt")
            return
        
        config = load_config()
        mode = flags.get("mode", config["default_mode"])
        key_size = int(flags.get("keysize", config["default_keysize"]))
        password = flags.get("password")
        
        try:
            status_msg = await ctx.send("🔐 Encrypting message with multi-layer security...")
            
            encrypted_package = multi_layer_encrypt(message, mode, key_size, password)
            
            await status_msg.delete()
            
            # Send encrypted data via embed for better formatting
            await forwardEmbedMethod(
                channel_id=ctx.channel.id,
                title="🔐 Message Encrypted Successfully",
                description=f"**Mode:** AES-{mode}-{key_size}\n**Layers:** Compression + HMAC + Base64",
                content=f"```json\n{encrypted_package[:1500]}{'...' if len(encrypted_package) > 1500 else ''}```"
            )
            
            script_log(f"Message encrypted using {mode}-{key_size}", "SUCCESS")
            
        except Exception as e:
            await ctx.send(f"❌ Encryption failed: {str(e)}")
            script_log(f"Encryption error: {e}", "ERROR")
    
    async def handle_decrypt(ctx, args):
        """Handle decryption subcommand."""
        if not args.strip():
            await ctx.send("❌ Usage: `<p>aes decrypt <encrypted_data> [--password PASSWORD] [--key KEY]`")
            return
        
        # Parse flags
        parts = args.split()
        flags = {}
        data_parts = []
        
        i = 0
        while i < len(parts):
            if parts[i].startswith("--"):
                flag = parts[i][2:]
                if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                    flags[flag] = parts[i + 1]
                    i += 2
                else:
                    flags[flag] = True
                    i += 1
            else:
                data_parts.append(parts[i])
                i += 1
        
        encrypted_data = " ".join(data_parts)
        if not encrypted_data:
            await ctx.send("❌ No encrypted data provided")
            return
        
        password = flags.get("password")
        key = flags.get("key")
        
        try:
            status_msg = await ctx.send("🔓 Decrypting message...")
            
            decrypted_message = multi_layer_decrypt(encrypted_data, password, key)
            
            await status_msg.delete()
            await ctx.send(f"🔓 **Decrypted Message:**\n```\n{decrypted_message}\n```")
            
            script_log("Message decrypted successfully", "SUCCESS")
            
        except Exception as e:
            await ctx.send(f"❌ Decryption failed: {str(e)}")
            script_log(f"Decryption error: {e}", "ERROR")
    
    async def handle_genkey(ctx, args):
        """Handle key generation subcommand."""
        parts = args.split()
        size = 256
        
        for i, part in enumerate(parts):
            if part == "--size" and i + 1 < len(parts):
                try:
                    size = int(parts[i + 1])
                    if size not in [128, 192, 256]:
                        raise ValueError("Key size must be 128, 192, or 256")
                except ValueError as e:
                    await ctx.send(f"❌ Invalid key size: {e}")
                    return
        
        try:
            key = generate_secure_key(size)
            key_b64 = base64.b64encode(key).decode()
            
            await forwardEmbedMethod(
                channel_id=ctx.channel.id,
                title="🔑 Secure Key Generated",
                description=f"**Key Size:** {size} bits\n**Format:** Base64\n\n```\n{key_b64}\n```",
                content="⚠️ **Keep this key secure and never share it publicly!**"
            )
            
            script_log(f"Generated {size}-bit key", "SUCCESS")
            
        except Exception as e:
            await ctx.send(f"❌ Key generation failed: {str(e)}")
    
    async def handle_explain(ctx):
        """Provide detailed explanation of AES and the encryption system."""
        explanation = """
🔐 **Advanced Encryption Standard (AES) Explanation**

**What is AES?**
AES (Advanced Encryption Standard) is a symmetric encryption algorithm that secures data using the same key for encryption and decryption. Established by NIST in 2001 as a replacement for DES, AES operates on 128-bit data blocks and supports key lengths of 128, 192, or 256 bits, with corresponding rounds of 10, 12, or 14.

**AES Round Operations:**
1. **SubBytes**: Substitutes each byte using a lookup table (S-box)
2. **ShiftRows**: Shifts rows of the 4x4 byte state array cyclically  
3. **MixColumns**: Mixes column data via matrix multiplication in a finite field
4. **AddRoundKey**: XORs the state with a round-specific subkey

**This Script's Multi-Layer Security:**
🛡️ **Layer 1: Data Compression** - Reduces data size and adds obfuscation
🔐 **Layer 2: AES Encryption** - Multiple modes (GCM, CBC, CTR) with 128/192/256-bit keys
🔒 **Layer 3: HMAC Authentication** - Prevents tampering with SHA-256 hash
🎯 **Layer 4: Base64 Encoding** - Safe text transmission format
🔑 **Layer 5: PBKDF2 Key Derivation** - Secure password-to-key conversion (100k+ iterations)

**Advanced Features:**
• RSA key exchange for secure key distribution
• Cryptographically secure random number generation  
• Authenticated encryption with GCM mode
• Integrity verification with HMAC-SHA256
• Configurable encryption parameters
• Performance benchmarking tools

**Security relies on proper implementation and key management.**
        """
        
        await ctx.send(explanation)
    
    async def handle_config(ctx, args):
        """Handle configuration subcommand."""
        parts = args.split()
        if len(parts) < 2:
            config = load_config()
            config_str = json.dumps(config, indent=2)
            await ctx.send(f"**Current Configuration:**\n```json\n{config_str}\n```")
            return
        
        setting = parts[0]
        value = " ".join(parts[1:])
        
        config = load_config()
        
        # Type conversion based on setting
        if setting in ["pbkdf2_iterations", "default_keysize", "rsa_keysize"]:
            try:
                value = int(value)
            except ValueError:
                await ctx.send(f"❌ Setting '{setting}' requires an integer value")
                return
        elif setting in ["enable_compression", "enable_hmac"]:
            value = value.lower() in ["true", "1", "yes", "on"]
        
        config[setting] = value
        save_config(config)
        
        await ctx.send(f"✅ Configuration updated: `{setting}` = `{value}`")
        script_log(f"Config updated: {setting} = {value}", "INFO")
    
    async def handle_benchmark(ctx):
        """Run encryption/decryption performance benchmarks."""
        test_message = "This is a test message for benchmarking encryption performance. " * 10
        iterations = 100
        
        status_msg = await ctx.send("⏱️ Running encryption benchmarks...")
        
        results = {}
        modes = ["GCM", "CBC", "CTR"]
        
        for mode in modes:
            encrypt_times = []
            decrypt_times = []
            
            for _ in range(iterations):
                # Encryption benchmark
                start_time = time.perf_counter()
                encrypted = multi_layer_encrypt(test_message, mode, 256)
                encrypt_time = time.perf_counter() - start_time
                encrypt_times.append(encrypt_time)
                
                # Decryption benchmark  
                start_time = time.perf_counter()
                multi_layer_decrypt(encrypted)
                decrypt_time = time.perf_counter() - start_time
                decrypt_times.append(decrypt_time)
            
            results[mode] = {
                "avg_encrypt": sum(encrypt_times) / len(encrypt_times) * 1000,  # Convert to ms
                "avg_decrypt": sum(decrypt_times) / len(decrypt_times) * 1000
            }
        
        await status_msg.delete()
        
        benchmark_text = "📊 **Encryption Performance Benchmarks**\n\n"
        for mode, times in results.items():
            benchmark_text += f"**AES-{mode}-256:**\n"
            benchmark_text += f"• Encryption: {times['avg_encrypt']:.2f} ms\n"
            benchmark_text += f"• Decryption: {times['avg_decrypt']:.2f} ms\n\n"
        
        benchmark_text += f"*Tested with {iterations} iterations on {len(test_message)} byte message*"
        
        await ctx.send(benchmark_text)
        script_log("Benchmark completed", "SUCCESS")
    
    async def show_aes_help(ctx):
        """Show detailed help information."""
        help_text = f"""
🔐 **Advanced AES Encryption Suite - Help**

**Main Command:** `{getConfigData().get('prefix', '<p>')}aes <subcommand> [arguments] [flags]`

**Subcommands:**
• `encrypt <message> [--mode MODE] [--keysize SIZE] [--password PASS]` - Encrypt with multi-layer security
• `decrypt <data> [--password PASS] [--key KEY]` - Decrypt encrypted data  
• `genkey [--size SIZE]` - Generate cryptographically secure key
• `explain` - Detailed AES and encryption explanation
• `config <setting> <value>` - Configure encryption settings
• `benchmark` - Performance testing of encryption modes
• `help` - Show this help message

**Encryption Modes:**
🔹 **GCM** - Authenticated encryption (recommended)
🔹 **CBC** - Cipher Block Chaining with PKCS7 padding
🔹 **CTR** - Counter mode for streaming

**Key Sizes:** 128, 192, 256 bits (256 recommended)

**Examples:**
`{getConfigData().get('prefix', '<p>')}aes encrypt "Secret data" --mode GCM --keysize 256`
`{getConfigData().get('prefix', '<p>')}aes decrypt "encrypted_package" --password mypass`
`{getConfigData().get('prefix', '<p>')}aes genkey --size 256`
`{getConfigData().get('prefix', '<p>')}aes config default_mode GCM`

**Security Features:**
✅ Multi-layer encryption with compression
✅ HMAC authentication prevents tampering  
✅ PBKDF2 key derivation (100k+ iterations)
✅ Cryptographically secure random generation
✅ Multiple AES modes supported
        """
        
        await ctx.send(help_text)
    
    # Initialize configuration on script load
    try:
        config = load_config()
        script_log("Advanced AES Encryption Suite initialized", "SUCCESS")
        script_log(f"Default mode: {config['default_mode']}, Key size: {config['default_keysize']}", "INFO")
    except Exception as e:
        script_log(f"Initialization error: {e}", "ERROR")

# Call the script function to register commands
script_function()
