# flow_views/paypal_flow.py
import discord
from discord.ext import commands
import config 

# --- Shared Views (used by ALL receiving flows) ---

# View for Ticket Actions (Claim, Close, etc.)
class TicketActionView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, emoji="🛡️")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        
        # Check if the ticket is already claimed (optional, but good practice)
        if channel.category_id == config.TICKET_CATEGORY_CLAIMED_ID:
            return await interaction.response.send_message("This ticket is already claimed.", ephemeral=True)

        # 1. Move channel to the CLAIMED category
        claimed_category = guild.get_channel(config.TICKET_CATEGORY_CLAIMED_ID)
        if claimed_category:
            await channel.edit(category=claimed_category)
        
        # 2. Disable the Claim button and update the message
        self.children[0].disabled = True # Disable the Claim button
        self.children[0].label = f"Claimed by {interaction.user.name}"
        self.children[0].style = discord.ButtonStyle.secondary # Change color to gray

        await interaction.response.edit_message(view=self)
        
        # 3. Announce the claim
        await channel.send(f"**🛡️ Ticket Claimed!** {interaction.user.mention} has claimed this exchange ticket. The channel has been moved to the `Claimed` category.")


    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ⚠️ Placeholder: Logic to close the channel
        await interaction.response.send_message("Ticket will now close...", ephemeral=False)

    @discord.ui.button(label="Reopen", style=discord.ButtonStyle.blurple, emoji="🔓")
    async def reopen_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ⚠️ Placeholder: Logic to reopen a closed ticket
        await interaction.response.send_message("Ticket status changed to Reopened.", ephemeral=False)


# View for the final confirmation/cancellation buttons (Includes Ticket Creation)
class ConfirmCancelView(discord.ui.View):
    def __init__(self, flow_data, amount_sent, final_received, fee_amount, timeout=300):
        super().__init__(timeout=timeout)
        self.flow_data = flow_data
        self.amount_sent = amount_sent        
        self.final_received = final_received  
        self.fee_amount = fee_amount # Storing the calculated fee amount

    @discord.ui.button(label="✔ Confirm", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        # 1. SETUP TICKET PERMISSIONS
        guild = interaction.guild
        member = interaction.user
        # 🟢 Use UNCLAIMED category for initial creation
        category = guild.get_channel(config.TICKET_CATEGORY_UNCLAIMED_ID) 
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False), 
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        try:
            # 2. CREATE TICKET CHANNEL (in the UNCLAIMED category)
            ticket_channel_name = f"exchange-{member.name}-{self.flow_data['receiver']}".lower().replace(' ', '-')
            ticket_channel = await guild.create_text_channel(
                ticket_channel_name,
                category=category,
                overwrites=overwrites
            )

            # 3. Format and Send the TICKET EMBED with Actions
            ticket_embed = discord.Embed(
                title=f"💸 New Exchange Request: {self.flow_data['sender'].title()} → {self.flow_data['receiver'].title()}",
                description=f"Hello {member.mention}! A staff member will be with you shortly to handle this exchange.\n",
                color=discord.Color.blue()
            )
            ticket_embed.add_field(name="Amount Sent", value=f"${self.amount_sent:,.2f} ({self.flow_data['currency']})", inline=True)
            ticket_embed.add_field(name="Final Received", value=f"**${self.final_received:,.2f}**", inline=True)
            
            # 🟢 Logic to display specific crypto coin (e.g., Crypto → LTC)
            exchange_type_value = f"{self.flow_data['receiver'].title()}"

            if self.flow_data.get('crypto_coin'):
                # Format: Crypto → LTC
                exchange_type_value += f" → {self.flow_data['crypto_coin']}"
            else:
                # Fallback for non-crypto methods (e.g., PayPal Balance)
                exchange_type_value += f" ({self.flow_data['specific_type'].replace('_', ' ').title()})"
            
            exchange_type_value += f"\nFee: ${self.fee_amount:,.2f}"


            ticket_embed.add_field(name="Exchange Type", 
                                   value=exchange_type_value, 
                                   inline=False)
            
            ticket_embed.set_footer(text=f"User ID: {member.id} | Ticket ID: {ticket_channel.id}")


            await ticket_channel.send(
                content=f"@here New exchange ticket created by {member.mention}!", 
                embed=ticket_embed,
                view=TicketActionView() 
            )

            # 4. ACKNOWLEDGE USER - EDITS THE EPHEMERAL SUMMARY MESSAGE
            self.clear_items()
            await interaction.response.edit_message(
                content=interaction.message.content + f"\n\n**✅ Transaction Confirmed.** A staff member has been notified and a ticket has been opened in {ticket_channel.mention}.",
                view=self
            )

        except Exception as e:
            print(f"Error creating ticket: {e}")
            self.clear_items()
            await interaction.response.edit_message(
                content=interaction.message.content + f"\n\n**❌ Error:** Could not create ticket channel. (Bot permission issue, check category ID/permissions).",
                view=self
            )


    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.clear_items()
        # EDITS THE EPHEMERAL SUMMARY MESSAGE
        await interaction.response.edit_message(
            content=interaction.message.content + "\n\n**❌ Transaction Cancelled.**",
            view=self
        )
        self.stop()


# Modal for amount input and calculation (Shared across all flows)
class AmountModal(discord.ui.Modal, title="Enter Exchange Amount"):
    def __init__(self, flow_data):
        super().__init__()
        self.flow_data = flow_data

    amount_input = discord.ui.TextInput(
        label="Amount to Exchange",
        placeholder="e.g., 200.00",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount_sent = float(self.amount_input.value)
        except ValueError:
            # EPHEMERAL ERROR
            return await interaction.response.send_message("Invalid amount. Please enter a number.", ephemeral=True)
        
        # --- FEE CALCULATION LOGIC (Minimum $3.00) ---
        fee_rate = self.flow_data['fee_rate']
        MINIMUM_FEE = 3.00

        if amount_sent <= 0:
             return await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)

        # 1. Calculate the fee based on the standard percentage
        percentage_fee = amount_sent * fee_rate

        # 2. Apply the minimum fee rule ($3.00 minimum)
        if percentage_fee < MINIMUM_FEE:
            fee_amount = MINIMUM_FEE
        else:
            fee_amount = percentage_fee
        
        # Final Calculation
        final_received = amount_sent - fee_amount
        
        # --- END FEE CALCULATION LOGIC ---

        # Format the summary message
        summary_message = (
            f"**Sending Method:** {self.flow_data['sender']} ({self.flow_data['account_type'].replace('_', ' ').title()})\n"
            f"**Receiving Method:** {self.flow_data['receiver'].title()} ({self.flow_data['specific_type'].replace('_', ' ').title()})\n"
            f"**Currency:** {self.flow_data['currency']}\n"
            f"**Amount Sent:** ${amount_sent:,.2f}\n"
            f"**Fee ({int(fee_rate*100)}% or Min ${MINIMUM_FEE:.2f}):** ${fee_amount:,.2f}\n" 
            f"**Final Amount Received:** **${final_received:,.2f}**\n\n"
            f"**Please confirm the transaction details below:**"
        )

        # EPHEMERAL FINAL SUMMARY - Passing the calculated fee amount
        await interaction.response.send_message(
            summary_message,
            view=ConfirmCancelView(self.flow_data, amount_sent, final_received, fee_amount),
            ephemeral=True
        )


# --- PAYPAL SPECIFIC FLOW VIEWS ---

# Step 4: Currency Selection
class CurrencySelectionView(discord.ui.View):
    def __init__(self, sender, account, receiver, specific_type, fee_rate, timeout=300):
        super().__init__(timeout=timeout)
        self.flow_data = {
            "sender": sender,
            "account_type": account,
            "receiver": receiver,
            "specific_type": specific_type,
            "fee_rate": fee_rate,
        }

    @discord.ui.select(
        placeholder="Select the currency you are sending...",
        options=[
            discord.SelectOption(label="USD", value="USD", emoji="🇺🇸"),
            discord.SelectOption(label="EUR", value="EUR", emoji="🇪🇺"),
            discord.SelectOption(label="GBP", value="GBP", emoji="🇬🇧"),
        ]
    )
    async def select_currency(self, interaction: discord.Interaction, select: discord.ui.Select):
        currency = select.values[0]
        self.flow_data["currency"] = currency
        # Next step is the AmountModal 
        await interaction.response.send_modal(AmountModal(self.flow_data))


# Step 3: PayPal Type Selection
class PayPalTypeView(discord.ui.View):
    def __init__(self, sender_method, account_type, receiving_method, timeout=300):
        super().__init__(timeout=timeout)
        self.sender_method = sender_method
        self.account_type = account_type
        self.receiving_method = receiving_method

    @discord.ui.select(
        placeholder="Select your PayPal receiving type (Fee included)",
        options=[
            discord.SelectOption(label="PayPal Balance", value="paypal_balance", description=f"{int(config.FEE_RATES.get('paypal_balance', 0)*100)}% Fee", emoji="🟢"),
            discord.SelectOption(label="PayPal Card", value="paypal_card", description=f"{int(config.FEE_RATES.get('paypal_card', 0)*100)}% Fee", emoji="🔴")
        ]
    )
    async def select_paypal_type(self, interaction: discord.Interaction, select: discord.ui.Select):
        paypal_type = select.values[0]
        fee_rate = config.FEE_RATES.get(paypal_type, 0)

        next_view = CurrencySelectionView(
            self.sender_method, self.account_type, self.receiving_method, paypal_type, fee_rate
        )
        
        # EDITS THE EPHEMERAL MESSAGE
        await interaction.response.edit_message(
            content=f"You selected **{paypal_type.replace('_', ' ').title()}** ({int(fee_rate*100)}% Fee).\n\n**What currency are you sending?**",
            view=next_view
        )