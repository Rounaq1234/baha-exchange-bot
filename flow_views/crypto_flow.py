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
        # Set base flow data for AmountModal
        self.flow_data = {
            "sender": "crypto", # General sender type
            "account_type": "n/a", 
            "crypto_coin": crypto_coin, # Specific coin for the ticket title/log
            "fee_rate": config.FEE_RATES.get("crypto", 0.06),
            "currency": "USD" # Default currency for receiving fiat (can be made selectable)
        }

    @discord.ui.select(
        placeholder=f"Select method to receive funds from {self.flow_data['crypto_coin']}...",
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
        self.flow_data["specific_type"] = "general" # General type for fiat receiver

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
            # Add more coins as needed
        ]
    )
    async def select_crypto_coin(self, interaction: discord.Interaction, select: discord.ui.Select):
        crypto_coin = select.values[0]
        
        next_view = FiatReceiverView(crypto_coin)
        
        await interaction.response.edit_message(
            content=f"You selected **{crypto_coin}**. Now, select the method you want to **receive** the funds through:",
            view=next_view
        )
