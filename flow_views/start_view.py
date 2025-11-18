# flow_views/start_view.py
import discord
from discord.ext import commands
from config import FEE_RATES

# Import all flow views for routing
from .paypal_flow import PayPalTypeView
# 🟢 CORRECTED IMPORT: Use the correct class name CryptoCoinView
from .crypto_flow import CryptoCoinView 
from .zelle_flow import ZelleTypeView 
from .venmo_flow import VenmoTypeView


# --- STEP 3: RECEIVING METHOD SELECTION ---
class ReceivingMethodView(discord.ui.View):
    def __init__(self, sender_method, account_type, timeout=300):
        super().__init__(timeout=timeout)
        self.sender_method = sender_method
        self.account_type = account_type

    @discord.ui.select(
        placeholder="Select your desired receiving method...",
        options=[
            discord.SelectOption(label="PayPal", value="paypal", emoji="🅿️"),
            discord.SelectOption(label="Crypto", value="crypto", emoji="💰"),
            discord.SelectOption(label="Zelle", value="zelle", emoji="💳"),
            discord.SelectOption(label="Venmo", value="venmo", emoji="💸"),
        ]
    )
    async def select_receiving_method(self, interaction: discord.Interaction, select: discord.ui.Select):
        receiving_method = select.values[0]

        # ROUTING LOGIC
        if receiving_method == "paypal":
            next_view = PayPalTypeView(self.sender_method, self.account_type, receiving_method)
            content = f"You selected **{receiving_method.title()}** as your receiving method.\n\n**Please select your PayPal type:**"
            
        elif receiving_method == "crypto":
            # 🟢 FIX: Use CryptoCoinView and pass flow data for the next step
            # Note: CryptoCoinView needs self.sender_method and self.account_type to continue the flow
            next_view = CryptoCoinView(self.sender_method, self.account_type, receiving_method)
 
            # Fee logic explanation is included in the content message
            content = (
                f"You selected **{receiving_method.title()}** as your receiving method (8% Fee or Min $3.00).\n\n"
                f"**What Crypto Currency are you going to exchange?**"
            )
            
        elif receiving_method == "zelle":
            next_view = ZelleTypeView(self.sender_method, self.account_type, receiving_method)
            content = f"You selected **{receiving_method.title()}** as your receiving method.\n\n**Please select the Zelle transfer type:**"
            
        elif receiving_method == "venmo":
            next_view = VenmoTypeView(self.sender_method, self.account_type, receiving_method)
            content = f"You selected **{receiving_method.title()}** as your receiving method.\n\n**Please select the Venmo transfer speed:**"
            
        else:
            return await interaction.response.send_message(f"Flow for {receiving_method.title()} is not fully built.", ephemeral=True)

        # EDITS THE EPHEMERAL MESSAGE 
        await interaction.response.edit_message(content=content, view=next_view)


# --- STEP 2: ACCOUNT TYPE SELECTION ---
class AccountTypeView(discord.ui.View):
    def __init__(self, sender_method, timeout=300):
        super().__init__(timeout=timeout)
        self.sender_method = sender_method 

    @discord.ui.select(
        placeholder="Please select your account type...",
        options=[
            discord.SelectOption(label="Adult account", value="adult_account"),
            discord.SelectOption(label="Under 18 account", value="under_18_account", description="Requires parental/guardian verification.")
        ]
    )
    async def select_account_type(self, interaction: discord.Interaction, select: discord.ui.Select):
        account_type = select.values[0]

        if account_type == "adult_account":
            next_view = ReceivingMethodView(self.sender_method, account_type)
            # EDITS THE EPHEMERAL MESSAGE (No ephemeral=True here)
            await interaction.response.edit_message(
                content=f"You selected **{self.sender_method} ({account_type.replace('_', ' ').title()})**.\n\n**What payment method would you like to receive in return?**",
                view=next_view
            )
        else:
            await interaction.response.send_message(
                "Verification is required for Under 18 accounts. Transaction cancelled.", ephemeral=True
            )
            self.stop()


# --- STEP 1: INITIAL METHOD SELECTION ---
class MethodSelectionView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.select(
        placeholder="Select Option",
        options=[
            discord.SelectOption(label="PayPal", value="paypal", description="9% or 25% Fee", emoji="🅿️"),
            discord.SelectOption(label="CashApp", value="cashapp", description="9% Fee", emoji="💰"),
            discord.SelectOption(label="ApplePay", value="applepay", description="9% Fee", emoji="🍎"),
            discord.SelectOption(label="Venmo", value="venmo", description="9% Fee", emoji="🇻"),
            discord.SelectOption(label="Zelle", value="zelle", description="9% Fee", emoji="💜"),
            discord.SelectOption(label="Crypto", value="crypto", description="Send Crypto to Receive Fiat", emoji="💎"), 
        ]
    )
    # 🟢 CONSOLIDATED LOGIC: Using select_callback for all initial choices
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        sender_method = select.values[0]

        # Case 1: Start Crypto-to-Fiat Flow (Sender is Crypto, No Account Type needed)
        if sender_method == "crypto":
            # The 'sender' method is crypto, receiving method selection is the next step
            next_view = ReceivingMethodView(sender_method, "adult_account") # Defaulting account type for simplicity
            
            content = (
                f"You selected **{sender_method.title()}** as your sending method. "
                f"No account type selection is needed for Crypto.\n\n"
                f"**What payment method would you like to receive in return?**"
            )
            
            await interaction.response.send_message(
                content=content,
                view=next_view,
                ephemeral=True
            )
            return

        # Case 2: Fiat Sender (Requires Account Type Selection for CashApp)
        # This mirrors the logic you had in your removed select_method, initiating the ephemeral flow.
        elif sender_method == "cashapp":
            next_view = AccountTypeView(sender_method)
            content = f"You selected **{sender_method}** as your sending method.\n\n**Please select your account type:**"
        
        # Case 3: Other Fiat Senders (Bypass Account Type, Go straight to Receiving Method)
        else:
            account_type = "adult_account" 
            next_view = ReceivingMethodView(sender_method, account_type)
            content = f"You selected **{sender_method} ({account_type.replace('_', ' ').title()})**.\n\n**What payment method would you like to receive in return?**"

        # Start the new flow as the initial EPHEMERAL response.
        await interaction.response.send_message(
            content=content,
            view=next_view,
            ephemeral=True
        )
