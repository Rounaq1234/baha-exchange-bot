import discord
from discord.ext import commands
import config
from flow_views.paypal_flow import AmountModal 


# ==============================================================================
# --- NEW: STEP 3.5 (RECEIVER = CRYPTO): Coin Selection for receiving Crypto ---
# This class handles the PayPal -> Crypto, Zelle -> Crypto, etc. flow.
# ==============================================================================
class CryptoReceiverCoinView(discord.ui.View):
    """
    Selects the specific crypto coin the client WANTS TO RECEIVE.
    """
    def __init__(self, sender_method, account_type, receiving_method, timeout=300):
        super().__init__(timeout=timeout)
        self.flow_data = {
            "sender": sender_method, 
            "account_type": account_type, 
            "receiver": receiving_method,
        }

    @discord.ui.select(
        placeholder="Select the Cryptocurrency you want to RECEIVE...",
        options=[
            discord.SelectOption(label="Bitcoin (BTC)", value="BTC", emoji="🪙"),
            discord.SelectOption(label="Ethereum (ETH)", value="ETH", emoji="🔷"),
            discord.SelectOption(label="Litecoin (LTC)", value="LTC", emoji="💨"),
            discord.SelectOption(label="Solana (SOL)", value="SOL", emoji="☀️"),
        ]
    )
    async def select_receiver_coin(self, interaction: discord.Interaction, select: discord.ui.Select):
        # We don't defer because the next step is a modal (which uses a standard interaction response)
        
        receiver_crypto_coin = select.values[0]
        
        # Update flow data
        self.flow_data["client_id"] = str(interaction.user.id)
        # FIX: Renamed key from 'crypto_coin' to 'receiver_crypto_coin' 
        # to prevent downstream code from confusing the receiving coin with the sending method (PayPal).
        self.flow_data["receiver_crypto_coin"] = receiver_crypto_coin 
        self.flow_data["specific_type"] = "receive_crypto"
        self.flow_data["fee_rate"] = config.FEE_RATES.get("crypto_receive", 0.08) # Assuming a fee for receiving
        self.flow_data["currency"] = "USD"
        
        # The next step is always the AmountModal, asking for the fiat amount they are SENDING
        await interaction.response.send_modal(AmountModal(self.flow_data))


# ==============================================================================
# --- STEP 4 (SENDER = CRYPTO): Fiat Receiver Selection ---
# This path is used for: Crypto -> PayPal, Crypto -> Zelle, etc.
# ==============================================================================
class FiatReceiverView(discord.ui.View):
    """
    Selects the final fiat method for receiving funds after crypto is chosen.
    (Used only in Crypto SENDER flow)
    """
    def __init__(self, flow_data, crypto_coin, timeout=300):
        super().__init__(timeout=timeout)
        
        self.flow_data = flow_data
        # Renamed key from 'crypto_coin' to 'sender_crypto_coin' for clarity and consistency
        self.flow_data["sender_crypto_coin"] = crypto_coin 
        self.flow_data["fee_rate"] = config.FEE_RATES.get("crypto_send", 0.05) # Assuming a fee for sending
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
        fiat_method = select.values[0]
        
        self.flow_data["receiver"] = fiat_method
        self.flow_data["specific_type"] = "general" 

        await interaction.response.send_modal(AmountModal(self.flow_data))


# ==============================================================================
# --- STEP 3.5 (SENDER = CRYPTO): Crypto Coin Selection for sending Crypto ---
# This path is used for: Crypto -> PayPal, Crypto -> Zelle, etc.
# ==============================================================================
class CryptoCoinView(discord.ui.View):
    """
    Allows the user to select the specific crypto coin they are SENDING.
    (Used only in Crypto SENDER flow)
    """
    def __init__(self, sender_method, account_type, receiving_method, timeout=300):
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
        # Defer the interaction immediately to prevent timeout
        await interaction.response.defer()
        
        crypto_coin = select.values[0]
        
        self.flow_data["client_id"] = str(interaction.user.id)
        
        # Route to FiatReceiverView (Step 4 of Crypto SENDER flow)
        # crypto_coin is passed to FiatReceiverView which will store it as 'sender_crypto_coin'
        next_view = FiatReceiverView(self.flow_data, crypto_coin) 
        
        await interaction.edit_original_response(
            content=f"You selected **{crypto_coin}**. Now, select the method you want to **receive** the funds through:",
            view=next_view
        )
