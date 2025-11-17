# main.py
import discord
from discord.ext import commands
import config
from flow_views.start_view import MethodSelectionView 

# Define the Intents
intents = discord.Intents.default()
intents.message_content = True 

# Initialize the Bot/Client
bot = commands.Bot(command_prefix='!', intents=intents)

# --- COMMAND REGISTRATION ---
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
        
        # This message must be public for the buttons/views to attach
        await interaction.channel.send(
            "**Request an Exchange**", 
            embed=embed,
            view=MethodSelectionView() 
        )
        # Confirmation message is ephemeral
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

# --- EVENTS ---

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    
    # RELIABLE GUILD SYNC METHOD
    try:
        if config.TEST_GUILD_ID != 0:
            guild = discord.Object(id=config.TEST_GUILD_ID) 
            synced = await bot.tree.sync(guild=guild)
            
        else:
            synced = await bot.tree.sync()
            
        print(f"✅ Synced {len(synced)} command(s).")
        for command in synced:
            print(f"- Synced command: /{command.name}")

    except Exception as e:
        print(f"❌ ERROR syncing commands. Check Guild ID and Bot Scopes: {e}")


# --- RUN THE BOT ---

if __name__ == "__main__":
    if config.BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("ERROR: Please update BOT_TOKEN in config.py before running.")
    else:
        bot.run(config.BOT_TOKEN)