import discord
from discord.ext import commands
import config
# Import AmountModal from the paypal_flow file since it's shared
from flow_views.paypal_flow import AmountModal 


# ==============================================================================
# --- STEP 3: Receiving Method Selection (Crypto -> Fiat) ---
# ==============================================================================
class FiatReceiverView(discord.ui.View):
    def __init__(self, flow_data, crypto_coin, timeout=300):
        super().__init__(timeout=timeout)
        
        # Initialize full flow data based on previous steps and current selection
        self.flow_data = flow_data
        self.flow_data["crypto_coin"] = crypto_coin # Specific coin stored here
        self.flow_data["fee_rate"] = config.FEE_RATES.get("crypto", 0.05)
        self.flow_data["currency"] = "USD" 
        
        # Set the placeholder dynamically in __init__
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
        
        # Update flow data with receiving method and specific type
        self.flow_data["receiver"] = fiat_method
        self.flow_data["specific_type"] = "general" 

        # Passes the flow data to the modal for amount input
        await interaction.response.send_modal(AmountModal(self.flow_data))


# ==============================================================================
# --- STEP 2: Crypto Coin Selection (Starts the Crypto Flow) ---
# ==============================================================================
class CryptoCoinView(discord.ui.View):
    # CORRECTED __init__ to accept all 3 positional arguments + timeout
    def __init__(self, sender_method, account_type, receiving_method, timeout=300):
        super().__init__(timeout=timeout)
        # Initialize the base flow data
        self.flow_data = {
            "sender": sender_method, 
            "account_type": account_type, 
            "receiver": receiving_method,
            # client_id will be captured in the select callback below
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
        crypto_coin = select.values[0]
        
        # Capture client_id here where the interaction object is available
        self.flow_data["client_id"] = str(interaction.user.id)
        
        # Passes the complete flow data and the selected coin to the next view (FiatReceiverView)
        next_view = FiatReceiverView(self.flow_data, crypto_coin) 
        
        await interaction.response.edit_message(
            content=f"You selected **{crypto_coin}**. Now, select the method you want to **receive** the funds through:",
            view=next_view
        )
