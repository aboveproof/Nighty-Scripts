def paymentSettings():
    os.makedirs(f'{getScriptsPath()}/scriptData', exist_ok=True)
    script_config_path = f"{getScriptsPath()}/scriptData/payments.json"
    
    def updateSetting(key, value):
        settings = json.load(open(script_config_path, 'r', encoding="utf-8", errors="ignore")) if os.path.exists(script_config_path) else {}
        settings[key] = value
        json.dump(settings, open(script_config_path, 'w', encoding="utf-8", errors="ignore"), indent=2)

    def getSetting(key=None):
        if os.path.exists(script_config_path):
            with open(script_config_path, 'r', encoding="utf-8", errors="ignore") as f:
                settings = json.load(f)
            return settings.get(key) if key else settings
        return None if key else {}

    ## helper functions
    def isValidCashtag(cashtag):
        return bool(re.fullmatch(r"\$[a-zA-Z0-9]{1,15}", cashtag)) or not cashtag

    def isValidCryptoAddress(address, type="litecoin"):
        if type == "bitcoin":
            return bool(re.fullmatch(r"[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{39,59}", address)) or not address
        elif type == "ethereum":
            return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", address)) or not address
        elif type == "monero":
            return bool(re.fullmatch(r"4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}", address)) or not address
        else:  # litecoin
            return bool(re.fullmatch(r"[LM][a-km-zA-HJ-NP-Z1-9]{25,34}", address)) or not address

    def isValidPaypal(email_or_link):
        return bool(re.fullmatch(r"[^@]+@[^@]+\.[^@]+|https?://(www\.)?paypal\.me/[a-zA-Z0-9]+", email_or_link)) or not email_or_link

    def isValidVenmo(venmo_or_link):
        return bool(re.fullmatch(r"@[a-zA-Z0-9_]+|https?://(www\.)?venmo\.com/[a-zA-Z0-9]+", venmo_or_link)) or not venmo_or_link

    def isValidCashappLink(link):
        return bool(re.fullmatch(r"\$[a-zA-Z0-9]{1,15}|https?://(www\.)?cash\.app/[a-zA-Z0-9]+", link)) or not link

    def validateCashtag(new_value, current_input):
        if not isValidCashappLink(new_value):
            current_input.invalid = True
            current_input.error_message = "Invalid CashApp tag or link. Use $tag or https://cash.app/ format."
            return False
        current_input.invalid = False
        current_input.error_message = None
        updateSetting("cashapp", new_value)
        return True

    def validateLtcAddress(new_value, current_input):
        if not isValidCryptoAddress(new_value, "litecoin"):
            current_input.invalid = True
            current_input.error_message = "Invalid Litecoin address format."
            return False
        current_input.invalid = False
        current_input.error_message = None
        updateSetting("litecoin", new_value)
        return True

    def validateBtcAddress(new_value, current_input):
        if not isValidCryptoAddress(new_value, "bitcoin"):
            current_input.invalid = True
            current_input.error_message = "Invalid Bitcoin address format."
            return False
        current_input.invalid = False
        current_input.error_message = None
        updateSetting("bitcoin", new_value)
        return True

    def validateEthAddress(new_value, current_input):
        if not isValidCryptoAddress(new_value, "ethereum"):
            current_input.invalid = True
            current_input.error_message = "Invalid Ethereum address format."
            return False
        current_input.invalid = False
        current_input.error_message = None
        updateSetting("ethereum", new_value)
        return True

    def validateXmrAddress(new_value, current_input):
        if not isValidCryptoAddress(new_value, "monero"):
            current_input.invalid = True
            current_input.error_message = "Invalid Monero address format."
            return False
        current_input.invalid = False
        current_input.error_message = None
        updateSetting("monero", new_value)
        return True

    def validatePaypal(new_value, current_input):
        if not isValidPaypal(new_value):
            current_input.invalid = True
            current_input.error_message = "Invalid PayPal email or link format."
            return False
        current_input.invalid = False
        current_input.error_message = None
        updateSetting("paypal", new_value)
        return True

    def validateVenmo(new_value, current_input):
        if not isValidVenmo(new_value):
            current_input.invalid = True
            current_input.error_message = "Invalid Venmo handle or link format."
            return False
        current_input.invalid = False
        current_input.error_message = None
        updateSetting("venmo", new_value)
        return True

    ## ui functions
    def checkPaypalInput(new_value):
        validatePaypal(new_value, paypal_input)

    def checkCashtagInput(new_value):
        validateCashtag(new_value, cashtag_input)

    def checkLtcInput(new_value):
        validateLtcAddress(new_value, ltc_input)

    def checkBtcInput(new_value):
        validateBtcAddress(new_value, btc_input)

    def checkEthInput(new_value):
        validateEthAddress(new_value, eth_input)

    def checkXmrInput(new_value):
        validateXmrAddress(new_value, xmr_input)

    def checkVenmoInput(new_value):
        validateVenmo(new_value, venmo_input)

    # Clear functions for each payment method
    def clearPaypal():
        paypal_input.value = ""  # Clear the input field
        paypal_input.invalid = False  # Reset validation state
        paypal_input.error_message = None
        updateSetting("paypal", "")  # Update the settings file

    def clearCashapp():
        cashtag_input.value = ""
        cashtag_input.invalid = False
        cashtag_input.error_message = None
        updateSetting("cashapp", "")

    def clearVenmo():
        venmo_input.value = ""
        venmo_input.invalid = False
        venmo_input.error_message = None
        updateSetting("venmo", "")

    def clearLitecoin():
        ltc_input.value = ""
        ltc_input.invalid = False
        ltc_input.error_message = None
        updateSetting("litecoin", "")

    def clearBitcoin():
        btc_input.value = ""
        btc_input.invalid = False
        btc_input.error_message = None
        updateSetting("bitcoin", "")

    def clearEthereum():
        eth_input.value = ""
        eth_input.invalid = False
        eth_input.error_message = None
        updateSetting("ethereum", "")

    def clearMonero():
        xmr_input.value = ""
        xmr_input.invalid = False
        xmr_input.error_message = None
        updateSetting("monero", "")

    ## Actual Tab
    payment_tab = Tab(name="Payment Settings", title="Payment Settings", icon="calc")
    p_container = payment_tab.create_container(type="columns")
    payment_card = p_container.create_card(height="full", width="full", gap=6)

    ## Payment section
    payment_card.create_ui_element(UI.Text, content="Payment Methods", size="xl", weight="bold")
    
    payment_card.create_ui_element(
        UI.Text, 
        content=f"To send your payment methods, use the {bot.command_prefix}payment command.", 
        size="base", 
        weight="bold", 
        margin="mt-2"
    )
    payment_card.create_ui_element(
        UI.Text,
        content="(leave blank to exclude the payment method.)",
        size="sm",
        weight="normal",
        color="gray",
        margin="mb-4"
    )

    payment_card.create_ui_element(
        UI.Text, 
        content="Traditional Payment",
        size="lg", 
        weight="bold", 
        margin="mt-4"
    )

    fiat_group = payment_card.create_group(type="columns", gap=4, full_width=True)

    # PayPal Input with "x" inside and a separate "Clear" button
    paypal_group = fiat_group.create_group(type="rows", gap=2, full_width=True)
    paypal_input = paypal_group.create_ui_element(
        UI.Input,
        label="PayPal Email or Link",
        placeholder=getSetting("paypal") or "Email or https://paypal.me/USER",
        show_clear_button=True,
        onInput=checkPaypalInput,
        onClear=clearPaypal,
        full_width=True
    )
    paypal_group.create_ui_element(
        UI.Button,
        label="Clear",
        onClick=clearPaypal,
        size="sm",
        variant="bordered"
    )

    # CashApp Input with "x" inside and a separate "Clear" button
    cashapp_group = fiat_group.create_group(type="rows", gap=2, full_width=True)
    cashtag_input = cashapp_group.create_ui_element(
        UI.Input,
        label="CashApp Tag or Link",
        placeholder=getSetting("cashapp") or "$Tag or https://cash.app/USER",
        show_clear_button=True,
        onInput=checkCashtagInput,
        onClear=clearCashapp,
        full_width=True
    )
    cashapp_group.create_ui_element(
        UI.Button,
        label="Clear",
        onClick=clearCashapp,
        size="sm",
        variant="bordered"
    )

    # Venmo Input with "x" inside and a separate "Clear" button
    venmo_group = fiat_group.create_group(type="rows", gap=2, full_width=True)
    venmo_input = venmo_group.create_ui_element(
        UI.Input,
        label="Venmo Handle or Link",
        placeholder=getSetting("venmo") or "@USER or https://venmo.com/USER",
        show_clear_button=True,
        onInput=checkVenmoInput,
        onClear=clearVenmo,
        full_width=True
    )
    venmo_group.create_ui_element(
        UI.Button,
        label="Clear",
        onClick=clearVenmo,
        size="sm",
        variant="bordered"
    )

    # Crypto Payments Section
    payment_card.create_ui_element(
        UI.Text, 
        content="Crypto Payment", 
        size="lg", 
        weight="bold", 
        margin="mt-6"
    )

    crypto_group = payment_card.create_group(type="columns", gap=4, full_width=True)

    # Litecoin Input with "x" inside and a separate "Clear" button
    ltc_group = crypto_group.create_group(type="rows", gap=2, full_width=True)
    ltc_input = ltc_group.create_ui_element(
        UI.Input,
        label="Litecoin Address",
        placeholder=getSetting("litecoin") or "LTC Address",
        show_clear_button=True,
        onInput=checkLtcInput,
        onClear=clearLitecoin,
        full_width=True
    )
    ltc_group.create_ui_element(
        UI.Button,
        label="Clear",
        onClick=clearLitecoin,
        size="sm",
        variant="bordered"
    )

    # Bitcoin Input with "x" inside and a separate "Clear" button
    btc_group = crypto_group.create_group(type="rows", gap=2, full_width=True)
    btc_input = btc_group.create_ui_element(
        UI.Input,
        label="Bitcoin Address",
        placeholder=getSetting("bitcoin") or "BTC Address",
        show_clear_button=True,
        onInput=checkBtcInput,
        onClear=clearBitcoin,
        full_width=True
    )
    btc_group.create_ui_element(
        UI.Button,
        label="Clear",
        onClick=clearBitcoin,
        size="sm",
        variant="bordered"
    )

    # Ethereum Input with "x" inside and a separate "Clear" button
    eth_group = crypto_group.create_group(type="rows", gap=2, full_width=True)
    eth_input = eth_group.create_ui_element(
        UI.Input,
        label="Ethereum Address",
        placeholder=getSetting("ethereum") or "ETH Address",
        show_clear_button=True,
        onInput=checkEthInput,
        onClear=clearEthereum,
        full_width=True
    )
    eth_group.create_ui_element(
        UI.Button,
        label="Clear",
        onClick=clearEthereum,
        size="sm",
        variant="bordered"
    )

    # Monero Input with "x" inside and a separate "Clear" button
    xmr_group = crypto_group.create_group(type="rows", gap=2, full_width=True)
    xmr_input = xmr_group.create_ui_element(
        UI.Input,
        label="Monero Address",
        placeholder=getSetting("monero") or "XMR Address",
        show_clear_button=True,
        onInput=checkXmrInput,
        onClear=clearMonero,
        full_width=True
    )
    xmr_group.create_ui_element(
        UI.Button,
        label="Clear",
        onClick=clearMonero,
        size="sm",
        variant="bordered"
    )

    @bot.command(name="payment", aliases=["payment", "pay", "p"])
    async def payment(ctx):
        await ctx.message.delete()
        payment = {
            "PayPal": getSetting("paypal"),
            "CashApp": getSetting("cashapp"),
            "Venmo": getSetting("venmo"),
            "Litecoin": getSetting("litecoin"),
            "Bitcoin": getSetting("bitcoin"),
            "Ethereum": getSetting("ethereum"),
            "Monero": getSetting("monero"),
        }
        valid_payment = [f"> {name}: **{value}**" for name, value in payment.items() if value]
        if valid_payment:
            instructions = (
                "**Payment Instructions**\n\n"
                "Ensure the transaction is completed successfully.\n"
                "Provide a screenshot of the transaction details as proof of payment.\n"
                "Make sure the screenshot is **clear** and **uncropped**.\n\n"
                "**Rules for Payment**\n"
                "- Payments must be sent as **Friends & Family (F&F)** where applicable.\n"
                "- Double-check the address before sending funds.\n"
                "- **All payments are non-refundable** in case of errors or incorrect transactions.\n"
                "- Do **NOT** include any notes or memos with the transaction.\n\n"
                "### Accepted Payment Methods ###\n"
                + "\n".join(valid_payment)
            )
            await ctx.send(instructions)
        else:
            await ctx.send("> No payment methods have been set up.")

    payment_tab.render()

paymentSettings()
