import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import asyncio
import subprocess
import os
from datetime import datetime
from pathlib import Path

PTERODACTYL_PATH = "/var/www/pterodactyl"

class BlueprintInstaller(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.install_queue = []
        self.is_processing = False
        self.stop_requested = False
        
        self.process_queue_task.start()
        print("Blueprint installer cog loaded")
        print("Cron task scheduled to run every 5 minutes")
    
    def cog_unload(self):
        self.process_queue_task.cancel()
    
    @tasks.loop(minutes=5)
    async def process_queue_task(self):
        print(f"Cron triggered. Queue length: {len(self.install_queue)}, Currently processing: {self.is_processing}")
        
        if self.is_processing:
            print("[v0] Still processing previous batch. Skipping this cycle.")
            return
        
        if len(self.install_queue) == 0:
            print("Queue is empty. Nothing to process.")
            return
        
        await self.process_entire_queue()
    
    @process_queue_task.before_loop
    async def before_process_queue_task(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if not message.attachments:
            return
        
        blueprint_files = [att for att in message.attachments if att.filename.endswith(".blueprint")]
        
        if not blueprint_files:
            return
        
        for attachment in blueprint_files:
            queue_item = {
                "message": message,
                "attachment": attachment,
                "added_at": datetime.now()
            }
            self.install_queue.append(queue_item)
            
            status = "⚙️ Currently processing blueprints. Your file will be installed in the next cycle." if self.is_processing else "⏳ Will be processed in the next scheduled run (every 5 minutes)."
            
            await message.reply(
                f"📦 Blueprint `{attachment.filename}` added to queue. Position: {len(self.install_queue)}\n{status}"
            )
            print(f"[v0] Added {attachment.filename} to queue. Queue length: {len(self.install_queue)}")
    
    @app_commands.command(name="stop-installations", description="Stop the blueprint installation queue")
    @app_commands.checks.has_permissions(administrator=True)
    async def stop_installations(self, interaction: discord.Interaction):
        if not self.is_processing:
            await interaction.response.send_message("❌ No installations are currently running.", ephemeral=True)
            return
        
        self.stop_requested = True
        await interaction.response.send_message("🛑 Stop requested. Current installation will finish, then processing will halt.")
    
    @app_commands.command(name="queue-status", description="Check the current blueprint installation queue")
    async def queue_status(self, interaction: discord.Interaction):
        if len(self.install_queue) == 0:
            await interaction.response.send_message("📭 Queue is empty.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📦 Blueprint Installation Queue",
            description=f"**Queue Length:** {len(self.install_queue)}\n**Processing:** {'Yes' if self.is_processing else 'No'}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        queue_list = "\n".join([f"{i+1}. `{item['attachment'].filename}`" for i, item in enumerate(self.install_queue[:10])])
        if len(self.install_queue) > 10:
            queue_list += f"\n... and {len(self.install_queue) - 10} more"
        
        embed.add_field(name="Queued Blueprints", value=queue_list, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def process_entire_queue(self):
        if len(self.install_queue) == 0 or self.is_processing:
            return
        
        self.is_processing = True
        self.stop_requested = False
        print(f"[v0] Starting to process {len(self.install_queue)} blueprint(s) in queue")
        
        while len(self.install_queue) > 0:
            if self.stop_requested:
                print("[v0] Stop requested. Halting queue processing.")
                break
            
            queue_item = self.install_queue.pop(0)
            print(f"[v0] Processing blueprint. Remaining in queue: {len(self.install_queue)}")
            
            await self.process_blueprint(queue_item["message"], queue_item["attachment"])
            
            if len(self.install_queue) > 0 and not self.stop_requested:
                print("[v0] Waiting 10 seconds before next blueprint...")
                await asyncio.sleep(10)
        
        self.is_processing = False
        self.stop_requested = False
        print("[v0] Finished processing all blueprints in queue")
    
    async def process_blueprint(self, message, attachment):
        file_name = attachment.filename
        temp_file_path = f"/tmp/{file_name}"
        target_file_path = os.path.join(PTERODACTYL_PATH, file_name)
        
        try:
            status_message = await message.reply(f"📦 Processing blueprint: `{file_name}`...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as response:
                    if response.status == 200:
                        file_data = await response.read()
                        
                        with open(temp_file_path, "wb") as f:
                            f.write(file_data)
                        
                        print(f"[v0] Downloaded {file_name} to {temp_file_path}")
                        
                        with open(target_file_path, "wb") as f:
                            f.write(file_data)
                        
                        print(f"[v0] Copied {file_name} to {target_file_path}")
            
            await status_message.edit(content=f"📦 Blueprint copied to Pterodactyl directory. Installing...")
            
            install_result = await self.run_blueprint_install(file_name, status_message)
            
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            if install_result["success"]:
                embed = discord.Embed(
                    title=f"✅ Installation Complete",
                    description=f"Blueprint `{file_name}` installed successfully.",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                output_preview = install_result["output"][-1900:] if len(install_result["output"]) > 1900 else install_result["output"]
                embed.add_field(name="Output", value=f"\`\`\`\n{output_preview}\n\`\`\`", inline=False)
                await status_message.edit(content=None, embed=embed)
            else:
                embed = discord.Embed(
                    title=f"❌ Installation Failed",
                    description=f"Blueprint `{file_name}` failed to install.",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                output_preview = install_result["output"][-1900:] if len(install_result["output"]) > 1900 else install_result["output"]
                embed.add_field(name="Output", value=f"\`\`\`\n{output_preview}\n\`\`\`", inline=False)
                await status_message.edit(content=None, embed=embed)
        
        except Exception as error:
            print(f"[v0] Error processing blueprint: {error}")
            await message.reply(f"❌ Error processing `{file_name}`: {str(error)}")
    
    async def run_blueprint_install(self, file_name, status_message):
        command = ["blueprint", "-i", file_name]
        
        print(f"[v0] Running: {' '.join(command)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=PTERODACTYL_PATH,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            output = ""
            error_output = ""
            last_update = 0
            
            embed = discord.Embed(
                title=f"⚙️ Installing {file_name}",
                description="Starting installation...",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Console Output", value="\`\`\`\nInitializing...\n\`\`\`", inline=False)
            await status_message.edit(content=None, embed=embed)
            
            async def read_and_respond():
                nonlocal output, last_update
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    
                    text = line.decode()
                    output += text
                    print(f"[v0] stdout: {text.strip()}")
                    
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_update >= 0.5:
                        last_update = current_time
                        embed = discord.Embed(
                            title=f"⚙️ Installing {file_name}",
                            description="Installation in progress...",
                            color=discord.Color.blue(),
                            timestamp=datetime.now()
                        )
                        output_preview = output[-1900:] if len(output) > 1900 else output
                        embed.add_field(name="Console Output", value=f"\`\`\`\n{output_preview}\n\`\`\`", inline=False)
                        try:
                            await status_message.edit(embed=embed)
                        except:
                            pass
                    
                    if any(prompt in text.lower() for prompt in ["?", "(y/n)", "(y/n)", "[y/n]", "continue?", "proceed?"]):
                        print("[v0] Auto-responding with: yes")
                        process.stdin.write(b"yes\n")
                        await process.stdin.drain()
                    elif "press enter" in text.lower():
                        print("[v0] Auto-responding with: Enter")
                        process.stdin.write(b"\n")
                        await process.stdin.drain()
            
            async def read_stderr():
                nonlocal error_output
                while True:
                    line = await process.stderr.readline()
                    if not line:
                        break
                    
                    text = line.decode()
                    error_output += text
                    print(f"[v0] stderr: {text.strip()}")
            
            await asyncio.gather(read_and_respond(), read_stderr())
            
            return_code = await process.wait()
            
            print(f"[v0] Process exited with code {return_code}")
            
            full_output = output + (f"\n\nErrors:\n{error_output}" if error_output else "")
            
            return {
                "success": return_code == 0,
                "output": full_output or "Installation completed with no output."
            }
        
        except Exception as error:
            print(f"[v0] Process error: {error}")
            return {
                "success": False,
                "output": f"Process error: {str(error)}"
            }

async def setup(bot):
    await bot.add_cog(BlueprintInstaller(bot))
