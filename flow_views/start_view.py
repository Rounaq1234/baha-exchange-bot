import discord
from discord.ext import commands
from config import FEE_RATES

# Import all flow views for routing
from .paypal_flow import PayPalTypeView
# We now import the specific view for when Crypto is the receiver
from .crypto_flow import CryptoCoinView, CryptoReceiverCoinView 
from .zelle_flow import ZelleTypeView 
from .venmo_flow import VenmoTypeView 


# --- STEP 3: RECEIVING METHOD SELECTION ---
class ReceivingMethodView(discord.ui.View):
    """
    Allows the user to select their desired receiving method (e.g., Crypto, PayPal).
    """
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
        # Defer immediately to prevent the "Unknown interaction" 404 error
        await interaction.response.defer()
        receiving_method = select.values[0]

        # --- FIX: BRANCHING LOGIC FOR RECEIVER TYPE ---
        
        # 1. If the RECEIVER is a FIAT method (PayPal, Zelle, Venmo, etc.):
        if receiving_method in ["paypal", "zelle", "venmo"]:
            if receiving_method == "paypal":
                next_view = PayPalTypeView(self.sender_method, self.account_type, receiving_method)
                content = f"You selected **{receiving_method.title()}** as your receiving method.\n\n**Please select your PayPal type:**"
                
            elif receiving_method == "zelle":
                next_view = ZelleTypeView(self.sender_method, self.account_type, receiving_method)
                content = f"You selected **{receiving_method.title()}** as your receiving method.\n\n**Please select the Zelle transfer type:**"
                
            elif receiving_method == "venmo":
                next_view = VenmoTypeView(self.sender_method, self.account_type, receiving_method)
                content = f"You selected **{receiving_method.title()}** as your receiving method.\n\n**Please select the Venmo transfer speed:**"
                
            else:
                return await interaction.followup.send(f"Flow for {receiving_method.title()} is not fully built.", ephemeral=True)

        # 2. If the RECEIVER is CRYPTO:
        elif receiving_method == "crypto":
            # CORRECT ROUTE: Uses the new view designed for receiving crypto (PayPal -> Crypto)
            next_view = CryptoReceiverCoinView(self.sender_method, self.account_type, receiving_method)
            content = (
                f"You selected **{receiving_method.title()}** as your receiving method (8% Fee or Min $3.00).\n\n"
                f"**What Crypto Currency do you want to receive?**"
            )
            
        else:
            return await interaction.followup.send(f"Flow for {receiving_method.title()} is not built.", ephemeral=True)

        # Use edit_original_response since we deferred
        await interaction.edit_original_response(content=content, view=next_view)


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
        # Defer immediately to prevent the "Unknown interaction" 404 error
        await interaction.response.defer()
        
        account_type = select.values[0]

        if account_type == "adult_account":
            next_view = ReceivingMethodView(self.sender_method, account_type)
            await interaction.edit_original_response(
                content=f"You selected **{self.sender_method.title()} ({account_type.replace('_', ' ').title()})**.\n\n**What payment method would you like to receive in return?**",
                view=next_view
            )
        else:
            await interaction.followup.send(
                "Verification is required for Under 18 accounts. Transaction cancelled.", ephemeral=True
            )
            self.stop()


# --- STEP 1: INITIAL METHOD SELECTION (Sender) ---
class MethodSelectionView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.select(
        placeholder="Select Option",
        options=[
            discord.SelectOption(label="PayPal", value="paypal", description="8% or 25% Fee", emoji="🅿️"),
            discord.SelectOption(label="CashApp", value="cashapp", description="8% Fee", emoji="💰"),
            discord.SelectOption(label="ApplePay", value="applepay", description="8% Fee", emoji="🍎"),
            discord.SelectOption(label="Venmo", value="venmo", description="8% Fee", emoji="🇻"),
            discord.SelectOption(label="Zelle", value="zelle", description="8% Fee", emoji="💜"),
            discord.SelectOption(label="Crypto", value="crypto", description="Send Crypto to Receive Fiat", emoji="💎"), 
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        sender_method = select.values[0]

        if sender_method == "crypto":
            # Crypto SENDER flow (routes to Fiat RECEIVER views)
            next_view = ReceivingMethodView(sender_method, "adult_account") 
            
            content = (
                f"You selected **{sender_method.title()}** as your sending method.\n\n"
                f"**What payment method would you like to receive in return?**"
            )
            
            await interaction.response.send_message(
                content=content,
                view=next_view,
                ephemeral=True
            )
            return

        elif sender_method == "cashapp":
            next_view = AccountTypeView(sender_method)
            content = f"You selected **{sender_method.title()}** as your sending method.\n\n**Please select your account type:**"
        
        else:
            account_type = "adult_account" 
            next_view = ReceivingMethodView(sender_method, account_type)
            content = f"You selected **{sender_method.title()} ({account_type.replace('_', ' ').title()})**.\n\n**What payment method would you like to receive in return?**"

        await interaction.response.send_message(
            content=content,
            view=next_view,
            ephemeral=True
        )
