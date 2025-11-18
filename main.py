# main.py
import discord
from discord.ext import commands
from discord import app_commands # 🟢 NEW: Need for defining the /complete command
import config
from flow_views.start_view import MethodSelectionView
import json # 🟢 NEW: Need for parsing data from channel topic


# Define the Intents
# 🟢 UPDATE: members intent is required for role checks in /complete command
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

# Initialize the Bot/Client
# 🟢 UPDATE: Using config.PREFIX for consistency, ensure it's defined in config.py
bot = commands.Bot(command_prefix=config.PREFIX, intents=intents) 


# ==============================================================================
# 🟢 NEW: TICKET MANAGEMENT COMMANDS COG
# ==============================================================================
class TicketCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="complete", 
        description="Completes the exchange, logs the transaction, and deletes the ticket."
    )
    async def complete_command(self, interaction: discord.Interaction):
        channel = interaction.channel
        member = interaction.user

        # --- 1. PRE-CHECK: ROLE & CHANNEL VALIDATION ---
        valid_role_ids = list(config.EXCHANGER_ROLES.values())
        user_role_ids = [role.id for role in member.roles]
        has_permission = any(role_id in user_role_ids for role_id in valid_role_ids)
        
        if not has_permission:
            return await interaction.response.send_message(
                "❌ You do not have permission to run the `/complete` command.", 
                ephemeral=True
            )
            
        valid_categories = [config.TICKET_CATEGORY_UNCLAIMED_ID, config.TICKET_CATEGORY_CLAIMED_ID]
        if channel.category_id not in valid_categories:
            return await interaction.response.send_message(
                "❌ This command can only be used in a ticket channel.", 
                ephemeral=True
            )
            
        # --- 2. RETRIEVE TICKET DATA from Channel Topic ---
        if not channel.topic:
             return await interaction.response.send_message(
                 "❌ Channel topic is empty. No transaction data found.", 
                 ephemeral=True
             )
        
        try:
            flow_data_json = json.loads(channel.topic)
            
            amount_sent = flow_data_json.get('amount_sent', 0.0)
            final_received = flow_data_json.get('final_received', 0.0)
            fee_amount = flow_data_json.get('fee_amount', 0.0)
            flow_data = {
                'sender': flow_data_json.get('sender', 'Unknown'),
                'receiver': flow_data_json.get('receiver', 'Unknown'),
                'currency': flow_data_json.get('currency', 'USD'),
                'crypto_coin': flow_data_json.get('crypto_coin')
            }
            
        except (json.JSONDecodeError, KeyError) as e:
             print(f"Error parsing ticket data in /complete: {e}")
             return await interaction.response.send_message(
                 "❌ Could not retrieve valid transaction data from channel topic. Error: Corrupt data.", 
                 ephemeral=True
             )

        # --- 3. EXECUTE LOGGING AND DELETION ---
        
        await interaction.response.send_message(
            f"✅ **Exchange Complete.** Confirmed by {member.mention}. Logging transaction and deleting channel in a moment...",
            ephemeral=False
        )
        
        # LOGGING
        log_channel = channel.guild.get_channel(config.LOG_CHANNEL_ID)
        
        if log_channel:
            receiver_display = flow_data['receiver'].title()
            crypto_coin = flow_data.get('crypto_coin')
            
            if crypto_coin:
                exchange_desc = f"{crypto_coin} to {receiver_display}"
            else:
                exchange_desc = f"{flow_data['sender'].title()} to {receiver_display}"

            log_embed = discord.Embed(
                title="Exchange Completed",
                description=f"A client successfully exchanged **${amount_sent:,.2f}** ({exchange_desc})",
                color=discord.Color.green()
            )
            log_embed.add_field(name="Final Received", value=f"${final_received:,.2f} ({flow_data['currency']})", inline=True)
            log_embed.add_field(name="Fee Deducted", value=f"${fee_amount:,.2f}", inline=True)
            
            ticket_creator = channel.name.split('-')[1].title() if len(channel.name.split('-')) > 1 else "Unknown"
            
            log_embed.set_footer(text=f"Logged by: {member.name} | Creator: {ticket_creator}")
            log_embed.timestamp = discord.utils.utcnow()

            await log_channel.send(embed=log_embed)
        
        # DELETION
        await channel.delete(reason=f"Ticket completed and logged by {member.name} via /complete.")


# ==============================================================================
# --- COMMAND REGISTRATION (Modified to run the original commands) ---
# ==============================================================================
def register_commands():
    # Command 1: Setup the initial exchange menu
    @bot.tree.command(name="setup_exchange_menu", description="Posts the initial interactive exchange menu in the channel.")
    @commands.has_permissions(administrator=True)
    async def setup_exchange_menu(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Welcome",
            description="You can request an exchange by selecting the appropriate option below.",
            color=discord.Color.green()
        )
        
        await interaction.channel.send(
            "**Request an Exchange**", 
            embed=embed,
            view=MethodSelectionView() 
        )
        await interaction.response.send_message("Exchange menu posted successfully!", ephemeral=True)

    # Command 2: Force sync/reset
    @bot.tree.command(name="reset", description="Forces a sync and clear of all slash commands in this guild.")
    @commands.has_permissions(administrator=True)
    async def reset_commands(interaction: discord.Interaction):
        guild = interaction.guild
        
        bot.tree.clear_commands(guild=guild)
        synced = await bot.tree.sync(guild=guild)

        await interaction.response.send_message(
            f"✅ **Command Sync Complete!**\nSynced **{len(synced)}** command(s) instantly to this server.", 
            ephemeral=True
        )
        print(f"[{interaction.user.name}] executed /reset. Synced {len(synced)} commands to guild {guild.name}.")

register_commands() 

# ==============================================================================
# --- COG LOADER ---
# ==============================================================================
async def setup_cogs():
    # 🟢 NEW: Load the TicketCommands cog
    await bot.add_cog(TicketCommands(bot))


# --- EVENTS ---

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

    # Load Cogs before syncing commands
    await setup_cogs()
    
    # RELIABLE GUILD SYNC METHOD
    try:
        # Check if TEST_GUILD_ID exists in config.py (If you use a development server)
        if hasattr(config, 'TEST_GUILD_ID') and config.TEST_GUILD_ID != 0:
            guild = discord.Object(id=config.TEST_GUILD_ID) 
            synced = await bot.tree.sync(guild=guild)
            
        else:
            # Global sync (takes up to an hour)
            synced = await bot.tree.sync()
            
        print(f"✅ Synced {len(synced)} command(s).")
        for command in synced:
            print(f"- Synced command: /{command.name}")

    except Exception as e:
        print(f"❌ ERROR syncing commands. Check Guild ID and Bot Scopes: {e}")


# --- RUN THE BOT ---

if __name__ == "__main__":
    # Ensure BOT_TOKEN is checked using config attribute
    if hasattr(config, 'BOT_TOKEN') and config.BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("ERROR: Please update BOT_TOKEN in config.py before running.")
    else:
        bot.run(config.BOT_TOKEN)
