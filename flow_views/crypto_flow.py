# flow_views/crypto_flow.py (UPDATED)
import discord
from config import FEE_RATES
from .paypal_flow import AmountModal 

# --- STEP 4: Fiat Currency Selection (USD/CAD) ---
class FiatCurrencySelectionView(discord.ui.View):
    def __init__(self, flow_data, crypto_coin, timeout=300):
        super().__init__(timeout=timeout)
        self.flow_data = flow_data
        self.flow_data['crypto_coin'] = crypto_coin
        
        # The default fee (8%) is already in flow_data['fee_rate']

    @discord.ui.select(
        placeholder="Select the fiat currency you are sending...",
        options=[
            discord.SelectOption(label="USD", value="USD", emoji="🇺🇸"),
            discord.SelectOption(label="CAD", value="CAD", emoji="🇨🇦"),
        ]
    )
    async def select_fiat_currency(self, interaction: discord.Interaction, select: discord.ui.Select):
        currency = select.values[0]
        self.flow_data["currency"] = currency
        
        # Next step is the AmountModal 
        await interaction.response.send_modal(AmountModal(self.flow_data))


# --- STEP 3: Crypto Coin Selection (LTC, BTC, SOL, ETH) ---
class CryptoSelectionView(discord.ui.View):
    def __init__(self, sender, account, receiver, timeout=300):
        super().__init__(timeout=timeout)
        
        default_crypto_type = "crypto_default"
        default_fee_rate = FEE_RATES.get(default_crypto_type, 0)
        
        self.flow_data = {
            "sender": sender,
            "account_type": account,
            "receiver": receiver,
            "specific_type": default_crypto_type, 
            "fee_rate": default_fee_rate,
        }

    @discord.ui.select(
        placeholder="What Crypto Currency are you going to exchange?",
        options=[
            discord.SelectOption(label="Litecoin (LTC)", value="LTC", emoji="🪙"),
            # FIX: Replacing potentially problematic Bitcoin Sign (₿) with generic money bag (💰)
            discord.SelectOption(label="Bitcoin (BTC)", value="BTC", emoji="💰"),
            discord.SelectOption(label="Solana (SOL)", value="SOL", emoji="🟣"),
            discord.SelectOption(label="Ethereum (ETH)", value="ETH", emoji="♦️"),
        ]
    )
    async def select_crypto_coin(self, interaction: discord.Interaction, select: discord.ui.Select):
        crypto_coin = select.values[0]
        
        next_view = FiatCurrencySelectionView(self.flow_data, crypto_coin)
        
        # EDITS the EPHEMERAL message
        await interaction.response.edit_message(
            content=f"You selected **{crypto_coin}** (8% Fee or Min $3.00).\n\n**What fiat currency are you sending?**",
            view=next_view
        )