# Discord Blueprint Bot

A Discord bot that automates Pterodactyl blueprint installation with cron-based queue management.

## Features

- Accepts `.blueprint` file uploads in Discord
- Cron-based queue system: runs every 5 minutes
- Processes all queued blueprints sequentially
- Automatically copies files to `/var/www/pterodactyl`
- Runs `blueprint -i [filename]` command
- Auto-responds to prompts with "yes" or Enter
- Provides status updates and completion notifications
- Accepts submissions during processing (queued for next cycle)
- Built with Python and discord.py cogs for modular architecture

## Setup

1. **Install Python dependencies:**
   \`\`\`bash
   cd bot
   pip install -r requirements.txt
   \`\`\`

2. **Create a Discord Bot:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to "Bot" section and create a bot
   - Enable "Message Content Intent" under Privileged Gateway Intents
   - Copy the bot token

3. **Set environment variable:**
   \`\`\`bash
   export DISCORD_BOT_TOKEN="your-bot-token-here"
   \`\`\`

4. **Invite bot to your server:**
   - Go to OAuth2 → URL Generator
   - Select scopes: `bot`
   - Select permissions: `Send Messages`, `Read Messages/View Channels`, `Read Message History`
   - Use the generated URL to invite the bot

5. **Run the bot:**
   \`\`\`bash
   python main.py
   \`\`\`

## Usage

1. Upload a `.blueprint` file to any channel the bot can see
2. The bot will automatically:
   - Add the file to the installation queue
   - Show your position in the queue
   - Process all queued files every 5 minutes
   - Download each file when processing
   - Copy it to `/var/www/pterodactyl`
   - Run the installation command
   - Auto-respond to all prompts
   - Notify you when complete
   - Wait 10 seconds between each blueprint installation

## Queue Behavior

- Cron job runs every 5 minutes to process the queue
- If currently processing, the cron cycle is skipped
- All queued blueprints are processed sequentially in one batch
- 10-second delay between each blueprint installation
- New submissions are accepted anytime and queued for the next cycle
- If processing takes longer than 5 minutes, the next cycle waits

## Architecture

The bot uses discord.py's cogs system for modular organization:
- `main.py` - Bot initialization and startup
- `cogs/blueprint_installer.py` - Blueprint processing logic and queue management

## Requirements

- Python 3.8+
- discord.py 2.3.0+
- aiohttp 3.9.0+
- Access to `/var/www/pterodactyl` directory
- `blueprint` command available in PATH or in the Pterodactyl directory
- Proper permissions to run blueprint installations

## Notes

- The bot requires write access to `/var/www/pterodactyl`
- Make sure the bot process has sufficient permissions
- Consider running with a service manager like systemd for production
