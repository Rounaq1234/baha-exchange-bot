# config.py

# config.py (Changes highlighted)
import os # 🟢 NEW: Import os for environment variables

# --- DISCORD BOT CONFIGURATION ---
# ⚠️ REQUIRED: Replace with the actual token
# OLD: BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
# 🟢 NEW: Read token securely from environment variables
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN') 

# ... (rest of configuration) ...

# OPTIONAL: Replace with the ID of your server for instant slash command sync. 
# Use '0' for global sync (30-60 min delay).
TEST_GUILD_ID = 0


# --- TICKET CONFIGURATION ---
# REQUIRED: Replace with the ID of the Discord Category where new tickets should be placed.
# config.py

# ... (rest of configuration) ...

# --- TICKET CONFIGURATION ---
# REQUIRED: Replace with the IDs of the Discord Categories for organization.
TICKET_CATEGORY_UNCLAIMED_ID = 1439845355050242201  # ⚠️ Replace with your Unclaimed Category ID
TICKET_CATEGORY_CLAIMED_ID = 1439845500160577627    # ⚠️ Replace with your Claimed Category ID

# config.py

# ... (other config) ...

# --- TICKET LOGGING CONFIGURATION ---
# REQUIRED: Replace with the ID of the channel where exchange logs will be sent.
LOG_CHANNEL_ID = 1439984362077687818 # ⚠️ Replace with your Log Channel ID

# ... (rest of fee configuration) ...

# ... (rest of fee configuration) ...


# --- FEE CONFIGURATION ---
# Dictionary to store the fee rate (as a decimal) for different receiving methods.
FEE_RATES = {
    # PayPal Fees
    "paypal_balance": 0.08,  # 8% Fee
    "paypal_card": 0.20,     # 20% Fee
    
    # Crypto Fees (Simplified)
    "crypto_default": 0.08,  # 8% fee for any crypto transaction
    
    # Zelle Fees
    "zelle_standard": 0.08,  # 8% Fee
    "zelle_instant": 0.15,   # 15% Fee (Currently unsupported in the flow)
    
    # Venmo Fees
    "venmo_standard": 0.08,  # 8% Fee for Standard transfer
    "venmo_instant": 0.15, # 15% Fee for Instant transfer

}
