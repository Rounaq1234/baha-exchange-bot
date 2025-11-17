# flow_views/venmo_flow.py
import discord
from config import FEE_RATES
from .paypal_flow import CurrencySelectionView # Reusing CurrencySelectionView 

# Step 4: Venmo Transfer Type Selection
class VenmoTypeView(discord.ui.View):
    def __init__(self, sender_method, account_type, receiving_method, timeout=300):
        super().__init__(timeout=timeout)
        self.sender_method = sender_method
        self.account_type = account_type
        self.receiving_method = receiving_method

    @discord.ui.select(
        placeholder="Select the Venmo transfer speed...",
        options=[
            discord.SelectOption(label="Standard Transfer", value="venmo_standard", description=f"{int(FEE_RATES.get('venmo_standard', 0)*100)}% Fee", emoji="🟢"),
            discord.SelectOption(label="Instant Transfer", value="venmo_instant", description=f"{round(FEE_RATES.get('venmo_instant', 0)*100, 2)}% Fee", emoji="⚡")
        ]
    )
    async def select_venmo_type(self, interaction: discord.Interaction, select: discord.ui.Select):
        venmo_type = select.values[0]
        fee_rate = FEE_RATES.get(venmo_type, 0)

        next_view = CurrencySelectionView(
            self.sender_method, self.account_type, self.receiving_method, venmo_type, fee_rate
        )
        
        # EDITS THE EPHEMERAL MESSAGE
        await interaction.response.edit_message(
            content=f"You selected **{venmo_type.replace('_', ' ').title()}** ({round(fee_rate*100, 2)}% Fee).\n\n**What currency are you sending?**",
            view=next_view
        )