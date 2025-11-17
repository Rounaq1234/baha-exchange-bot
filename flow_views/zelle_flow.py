# flow_views/zelle_flow.py
import discord
from config import FEE_RATES
from .paypal_flow import CurrencySelectionView # Reusing CurrencySelectionView 

# Step 4: Zelle Transfer Type Selection
class ZelleTypeView(discord.ui.View):
    def __init__(self, sender_method, account_type, receiving_method, timeout=300):
        super().__init__(timeout=timeout)
        self.sender_method = sender_method
        self.account_type = account_type
        self.receiving_method = receiving_method

    @discord.ui.select(
        placeholder="Select the Zelle transfer speed/type...",
        options=[
            discord.SelectOption(label="Standard Transfer", value="zelle_standard", description=f"{int(FEE_RATES.get('zelle_standard', 0)*100)}% Fee", emoji="🟢"),
            discord.SelectOption(label="Instant Transfer", value="zelle_instant", description=f"{int(FEE_RATES.get('zelle_instant', 0)*100)}% Fee", emoji="⚡")
        ]
    )
    async def select_zelle_type(self, interaction: discord.Interaction, select: discord.ui.Select):
        zelle_type = select.values[0]
        fee_rate = FEE_RATES.get(zelle_type, 0)

        next_view = CurrencySelectionView(
            self.sender_method, self.account_type, self.receiving_method, zelle_type, fee_rate
        )
        
        # EDITS THE EPHEMERAL MESSAGE
        await interaction.response.edit_message(
            content=f"You selected **{zelle_type.replace('_', ' ').title()}** ({int(fee_rate*100)}% Fee).\n\n**What currency are you sending?**",
            view=next_view
        )