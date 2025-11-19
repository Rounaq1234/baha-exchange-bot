import discord
from discord.ext import commands
import config
# NOTE: Assumes AmountModal exists in flow_views/paypal_flow.py
from flow_views.paypal_flow import AmountModal 


# ==============================================================================
# --- STEP 4: Fiat Receiver Selection (After Crypto Coin is chosen) ---
# ==============================================================================
class FiatReceiverView(discord.ui.View):
    def __init__(self, flow_data, crypto_coin, timeout=300):
        super().__init__(timeout=timeout)
        
        self.flow_data = flow_data
        self.flow_data["crypto_coin"] = crypto_coin 
        self.flow_data["fee_rate"] = config.FEE_RATES.get("crypto", 0.05)
        self.flow_data["currency"] = "USD" 
        
        if self.children and isinstance(self.children[0], discord.ui.Select):
            self.children[0].placeholder = f"Select method to receive funds from {crypto_coin}..." 

    @discord.ui.select(
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
        # Sending a modal is the first and only response, so we do not defer here.
        fiat_method = select.values[0]
        
        self.flow_data["receiver"] = fiat_method
        self.flow_data["specific_type"] = "general" 

        # Passes the flow data to the modal for amount input
        await interaction.response.send_modal(AmountModal(self.flow_data))


# ==============================================================================
# --- STEP 3.5: Crypto Coin Selection ---
# ==============================================================================
class CryptoCoinView(discord.ui.View):
    def __init__(self, sender_method, account_type, receiving_method, timeout=300):
        # FIX: Correctly accept all flow data arguments
        super().__init__(timeout=timeout)
        self.flow_data = {
            "sender": sender_method, 
            "account_type": account_type, 
            "receiver": receiving_method,
        }


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
        # FIX: Defer the interaction immediately to prevent timeout (404 Unknown interaction)
        await interaction.response.defer()
        
        crypto_coin = select.values[0]
        
        self.flow_data["client_id"] = str(interaction.user.id)
        
        next_view = FiatReceiverView(self.flow_data, crypto_coin) 
        
        # Since we deferred, use edit_original_response
        await interaction.edit_original_response(
            content=f"You selected **{crypto_coin}**. Now, select the method you want to **receive** the funds through:",
            view=next_view
        )
