# flow_views/crypto_flow.py
import discord
from discord.ext import commands
import config
# Import AmountModal from the paypal_flow file since it's shared
from flow_views.paypal_flow import AmountModal 


# ==============================================================================
# --- STEP 3: Receiving Method Selection (Crypto -> Fiat) ---
# ==============================================================================
class FiatReceiverView(discord.ui.View):
    def __init__(self, crypto_coin, timeout=300):
        super().__init__(timeout=timeout)
        # Set base flow data
        self.flow_data = {
            "sender": "crypto", 
            "account_type": "n/a", 
            "crypto_coin": crypto_coin, # Specific coin stored here
            "fee_rate": config.FEE_RATES.get("crypto", 0.05),
            "currency": "USD" 
        }
        
        # 🟢 FIX: Set the placeholder dynamically in __init__
        # self.children[0] accesses the first component in the view (the select menu)
        self.children[0].placeholder = f"Select method to receive funds from {crypto_coin}..." 

    @discord.ui.select(
        # Note: The placeholder here is generic, but is immediately overridden in __init__
        placeholder="Select method to receive funds...", 
        options=[
            discord.SelectOption(label="PayPal", value="paypal", emoji="🅿️"),
            discord.SelectOption(label="CashApp", value="cashapp", emoji="💰"),
            discord.SelectOption(label="ApplePay", value="applepay", emoji="🍎"),
            discord.SelectOption(label="Venmo", value="venmo", emoji="🇻"),
            discord.SelectOption(label="Zelle", value="zelle", emoji="💜"),
        ]
    )
    async def select_fiat_receiver(self, interaction: discord.Interaction, select: discord.ui.Select):
        fiat_method = select.values[0]
        
        # Update flow data with receiving method and specific type
        self.flow_data["receiver"] = fiat_method
        self.flow_data["specific_type"] = "general" 

        await interaction.response.send_modal(AmountModal(self.flow_data))


# ==============================================================================
# --- STEP 2: Crypto Coin Selection (Starts the Crypto Flow) ---
# ==============================================================================
class CryptoCoinView(discord.ui.View):
    def __init__(self, timeout=300):
        super().__init__(timeout=timeout)

    @discord.ui.select(
        placeholder="Select the Cryptocurrency you are sending...",
        options=[
            discord.SelectOption(label="Bitcoin (BTC)", value="BTC", emoji="🪙"),
            discord.SelectOption(label="Ethereum (ETH)", value="ETH", emoji="🔷"),
            discord.SelectOption(label="Litecoin (LTC)", value="LTC", emoji="💨"),
            discord.SelectOption(label="Solana (SOL)", value="SOL", emoji="☀️"),
        ]
    )
    async def select_crypto_coin(self, interaction: discord.Interaction, select: discord.ui.Select):
        crypto_coin = select.values[0]
        
        # Passes the selected coin to the next view (FiatReceiverView)
        next_view = FiatReceiverView(crypto_coin) 
        
        await interaction.response.edit_message(
            content=f"You selected **{crypto_coin}**. Now, select the method you want to **receive** the funds through:",
            view=next_view
        )
