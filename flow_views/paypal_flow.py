# flow_views/paypal_flow.py
import discord
from discord.ext import commands
import config
import json # 🟢 ADDED for saving transaction data to channel topic


# --- New Modal for Closing Ticket via Button (Fallback, less robust than /complete) ---
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

        await interaction.response.send_message(f"Ticket closure confirmed by {interaction.user.mention}. Logging and deleting channel...", ephemeral=True)
        
        # NOTE: Using simplified logging for modal since /complete is the preferred method
        log_channel = self.channel.guild.get_channel(config.LOG_CHANNEL_ID)
        try:
            if log_channel:
                 await log_channel.send(f"⚠️ **MODAL CLOSE:** Ticket {self.channel.mention} closed by {interaction.user.name}. Use `/complete` for full logging.")

            await self.channel.delete(reason=f"Ticket closed via modal by {interaction.user.name}")
        except Exception as e:
            print(f"Error during modal closure/deletion: {e}")


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
        
        if channel.category_id == config.TICKET_CATEGORY_CLAIMED_ID:
            return await interaction.response.send_message("This ticket is already claimed.", ephemeral=True)

        claimed_category = guild.get_channel(config.TICKET_CATEGORY_CLAIMED_ID)
        if claimed_category:
            await channel.edit(category=claimed_category)
        
        self.children[0].disabled = True
        self.children[0].label = f"Claimed by {interaction.user.name}"
        self.children[0].style = discord.ButtonStyle.secondary 

        await interaction.response.edit_message(view=self)
        
        await channel.send(f"**🛡️ Ticket Claimed!** {interaction.user.mention} has claimed this exchange ticket. The channel has been moved to the `Claimed` category.")


    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        await interaction.response.send_message("Ticket status changed to Reopened.", ephemeral=False)


# View for the final confirmation/cancellation buttons (Includes Ticket Creation)
class ConfirmCancelView(discord.ui.View):
    def __init__(self, flow_data, amount_sent, final_received, fee_amount, timeout=300):
        super().__init__(timeout=timeout)
        self.flow_data = flow_data
        self.amount_sent = amount_sent        
        self.final_received = final_received  
        self.fee_amount = fee_amount 

    @discord.ui.button(label="✔ Confirm", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        await interaction.response.defer() 

        # 1. SETUP TICKET VARIABLES
        guild = interaction.guild
        member = interaction.user
        category = guild.get_channel(config.TICKET_CATEGORY_UNCLAIMED_ID) 
        
        # --- DYNAMIC PING/PERMISSION LOGIC ---
        sender_key = self.flow_data['sender']
        role_id = config.EXCHANGER_ROLES.get(sender_key)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False), 
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        
        exchanger_role = None
        if role_id:
            exchanger_role = guild.get_role(role_id)
            if exchanger_role:
                overwrites[exchanger_role] = discord.PermissionOverwrite(
                    read_messages=True, 
                    send_messages=True
                )
        # --- END DYNAMIC PING/PERMISSION LOGIC ---

        try:
            # 🟢 NEW: Prepare data for saving to channel topic
            data_to_save = {
                'sender': self.flow_data['sender'],
                'receiver': self.flow_data['receiver'],
                'currency': self.flow_data['currency'],
                'amount_sent': self.amount_sent,
                'final_received': self.final_received,
                'fee_amount': self.fee_amount,
                'crypto_coin': self.flow_data.get('crypto_coin', None),
                'creator_id': member.id 
            }
            topic_string = json.dumps(data_to_save) 


            # 2. CREATE TICKET CHANNEL (Includes overwrites and topic)
            ticket_channel_name = f"exchange-{member.name}-{self.flow_data['receiver']}".lower().replace(' ', '-')
            ticket_channel = await guild.create_text_channel(
                ticket_channel_name,
                category=category,
                overwrites=overwrites, 
                topic=topic_string      # Saves data for /complete command
            )

            # --- Final Ping Content ---
            if exchanger_role:
                ping_content = f"{exchanger_role.mention} New exchange ticket created by {member.mention}! Required Exchanger: **{sender_key.title()}**"
            else:
                ping_content = f"@here New exchange ticket created by {member.mention}!"
            # --------------------------


            # 3. Format and Send the TICKET EMBED with Actions
            ticket_embed = discord.Embed(
                title=f"💸 New Exchange Request: {self.flow_data['sender'].title()} → {self.flow_data['receiver'].title()}",
                description=f"Hello {member.mention}! A staff member will be with you shortly to handle this exchange.\n",
                color=discord.Color.blue()
            )
            ticket_embed.add_field(name="Amount Sent", value=f"${self.amount_sent:,.2f} ({self.flow_data['currency']})", inline=True)
            ticket_embed.add_field(name="Final Received", value=f"**${self.final_received:,.2f}**", inline=True)
            
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
                content=ping_content,
                embed=ticket_embed,
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
            return await interaction.response.send_message("Invalid amount. Please enter a number.", ephemeral=True)
        
        # --- FEE CALCULATION LOGIC (Minimum $3.00) ---
        fee_rate = self.flow_data['fee_rate']
        MINIMUM_FEE = 3.00

        if amount_sent <= 0:
             return await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)

        percentage_fee = amount_sent * fee_rate

        if percentage_fee < MINIMUM_FEE:
            fee_amount = MINIMUM_FEE
        else:
            fee_amount = percentage_fee
        
        final_received = amount_sent - fee_amount
        # --- END FEE CALCULATION LOGIC ---

        summary_message = (
            f"**Sending Method:** {self.flow_data['sender']} ({self.flow_data['account_type'].replace('_', ' ').title()})\n"
            f"**Receiving Method:** {self.flow_data['receiver'].title()} ({self.flow_data['specific_type'].replace('_', ' ').title()})\n"
            f"**Currency:** {self.flow_data['currency']}\n"
            f"**Amount Sent:** ${amount_sent:,.2f}\n"
            f"**Fee ({int(fee_rate*100)}% or Min ${MINIMUM_FEE:.2f}):** ${fee_amount:,.2f}\n" 
            f"**Final Amount Received:** **${final_received:,.2f}**\n\n"
            f"**Please confirm the transaction details below:**"
        )

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
        
        await interaction.response.edit_message(
            content=f"You selected **{paypal_type.replace('_', ' ').title()}** ({int(fee_rate*100)}% Fee).\n\n**What currency are you sending?**",
            view=next_view
        )
