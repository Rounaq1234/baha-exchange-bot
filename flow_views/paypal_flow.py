# flow_views/paypal_flow.py
import discord
from discord.ext import commands
import config 


# --- New Modal for Closing and Logging Ticket ---
class CloseTicketModal(discord.ui.Modal, title="Confirm Ticket Closure"):
    def __init__(self, channel, flow_data, amount_sent, final_received, fee_amount):
        super().__init__()
        self.channel = channel
        self.flow_data = flow_data
        self.amount_sent = amount_sent
        self.final_received = final_received
        self.fee_amount = fee_amount

    confirmation_input = discord.ui.TextInput(
        label="Type 'CONFIRM' to close and log the ticket",
        placeholder="CONFIRM",
        required=True,
        max_length=7
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation_input.value.strip().upper() != "CONFIRM":
            return await interaction.response.send_message("Closure cancelled. You must type 'CONFIRM'.", ephemeral=True)

        # Acknowledge immediately (ephemeral)
        await interaction.response.send_message(f"Ticket closure confirmed by {interaction.user.mention}. Logging and deleting channel...", ephemeral=True)
        
        # --- 1. LOG THE TRANSACTION ---
        log_channel = self.channel.guild.get_channel(config.LOG_CHANNEL_ID)
        
        if log_channel:
            # Create the Log Embed
            receiver_display = self.flow_data['receiver'].title()
            crypto_coin = self.flow_data.get('crypto_coin')
            
            # Determine exchange description
            if crypto_coin:
                # Example: LTC to PayPal
                exchange_desc = f"{crypto_coin} to {receiver_display}"
            else:
                # Example: PayPal to Zelle
                exchange_desc = f"{self.flow_data['sender'].title()} to {receiver_display}"

            log_embed = discord.Embed(
                title="Exchange Complete",
                description=f"A client successfully exchanged **${self.amount_sent:,.2f}** ({exchange_desc})",
                color=discord.Color.green()
            )
            log_embed.add_field(name="Final Received", value=f"${self.final_received:,.2f} ({self.flow_data['currency']})", inline=True)
            log_embed.add_field(name="Fee Deducted", value=f"${self.fee_amount:,.2f}", inline=True)
            
            # Extracts the creator's name from a channel name like "exchange-username-paypal"
            ticket_creator = self.channel.name.split('-')[1].title() if len(self.channel.name.split('-')) > 1 else self.channel.name
            
            log_embed.set_footer(text=f"Logged by: {interaction.user.name} | Creator: {ticket_creator}")
            log_embed.timestamp = discord.utils.utcnow()

            await log_channel.send(embed=log_embed)

        # --- 2. DELETE THE CHANNEL ---
        await self.channel.delete(reason=f"Ticket closed and logged by {interaction.user.name}")


# View for Ticket Actions (Claim, Close, etc.)
class TicketActionView(discord.ui.View):
    def __init__(self, flow_data, amount_sent, final_received, fee_amount, timeout=None):
        super().__init__(timeout=timeout)
        self.flow_data = flow_data
        self.amount_sent = amount_sent
        self.final_received = final_received
        self.fee_amount = fee_amount

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, emoji="🛡️")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        
        # Check if the ticket is already claimed
        if channel.category_id == config.TICKET_CATEGORY_CLAIMED_ID:
            return await interaction.response.send_message("This ticket is already claimed.", ephemeral=True)

        # 1. Move channel to the CLAIMED category
        claimed_category = guild.get_channel(config.TICKET_CATEGORY_CLAIMED_ID)
        if claimed_category:
            await channel.edit(category=claimed_category)
        
        # 2. Disable the Claim button and update the message
        self.children[0].disabled = True
        self.children[0].label = f"Claimed by {interaction.user.name}"
        self.children[0].style = discord.ButtonStyle.secondary 

        await interaction.response.edit_message(view=self)
        
        # 3. Announce the claim
        await channel.send(f"**🛡️ Ticket Claimed!** {interaction.user.mention} has claimed this exchange ticket. The channel has been moved to the `Claimed` category.")


    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Launch the confirmation modal
        modal = CloseTicketModal(
            interaction.channel,
            self.flow_data,
            self.amount_sent,
            self.final_received,
            self.fee_amount
        )
        await interaction.response.send_modal(modal)

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
        
        # 🟢 CRITICAL FIX: DEFER THE INTERACTION IMMEDIATELY
        await interaction.response.defer() 

        # 1. SETUP TICKET PERMISSIONS
        guild = interaction.guild
        member = interaction.user
        # Use UNCLAIMED category for initial creation
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

            # --- DYNAMIC PING LOGIC (USES SENDER PLATFORM) ---
            sender_key = self.flow_data['sender'] # <--- UPDATED TO PING SENDER EXCHANGER
            role_id = config.EXCHANGER_ROLES.get(sender_key)
            
            if role_id:
                # Format the role mention string: <@&ROLE_ID>
                ping_mention = f"<@&{role_id}>"
                ping_content = f"{ping_mention} New exchange ticket created by {member.mention}! Required Exchanger: **{sender_key.title()}**"
            else:
                # Fallback if the sender type isn't mapped
                ping_content = f"@here New exchange ticket created by {member.mention}!"
            # --- END DYNAMIC PING LOGIC ---


            # 3. Format and Send the TICKET EMBED with Actions
            ticket_embed = discord.Embed(
                title=f"💸 New Exchange Request: {self.flow_data['sender'].title()} → {self.flow_data['receiver'].title()}",
                description=f"Hello {member.mention}! A staff member will be with you shortly to handle this exchange.\n",
                color=discord.Color.blue()
            )
            ticket_embed.add_field(name="Amount Sent", value=f"${self.amount_sent:,.2f} ({self.flow_data['currency']})", inline=True)
            ticket_embed.add_field(name="Final Received", value=f"**${self.final_received:,.2f}**", inline=True)
            
            # Logic to display specific crypto coin (e.g., Crypto → LTC)
            exchange_type_value = f"{self.flow_data['receiver'].title()}"

            if self.flow_data.get('crypto_coin'):
                exchange_type_value += f" → {self.flow_data['crypto_coin']}"
            else:
                exchange_type_value += f" ({self.flow_data['specific_type'].replace('_', ' ').title()})"
            
            exchange_type_value += f"\nFee: ${self.fee_amount:,.2f}"


            ticket_embed.add_field(name="Exchange Type", 
                                   value=exchange_type_value, 
                                   inline=False)
            
            ticket_embed.set_footer(text=f"User ID: {member.id} | Ticket ID: {ticket_channel.id}")


            # 4. SEND THE MESSAGE WITH THE DYNAMIC PING
            await ticket_channel.send(
                content=ping_content, # Uses the new selective ping based on sender
                embed=ticket_embed,
                # Pass all transaction data to TicketActionView
                view=TicketActionView(self.flow_data, self.amount_sent, self.final_received, self.fee_amount) 
            )

            # 5. ACKNOWLEDGE USER - Use edit_original_response after deferring
            self.clear_items()
            await interaction.edit_original_response(
                content=interaction.message.content + f"\n\n**✅ Transaction Confirmed.** A staff member has been notified and a ticket has been opened in {ticket_channel.mention}.",
                view=self
            )

        except Exception as e:
            print(f"Error creating ticket: {e}")
            self.clear_items()
            await interaction.edit_original_response(
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
