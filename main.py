import discord
from discord import app_commands
from discord.utils import get
import io

TOKEN = ''

ICON = ''
NAME = ''

SUPPORT_ROLE_ID = 
TRANSCRIPT_CHANNEL_ID = 

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

class TicketsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Support', style=discord.ButtonStyle.blurple, custom_id='ticket_button')
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        ticket_channel_name = f'ticket-{user.name}-{user.id}'
        existing_ticket = get(guild.text_channels, name=ticket_channel_name)
        if existing_ticket:
            await interaction.response.send_message(
                f'You already have a ticket open at {existing_ticket.mention}', ephemeral=True
            )
            return

        support_role = get(guild.roles, id=SUPPORT_ROLE_ID)

        category = get(guild.categories, name='Tickets')
        if not category:
            category = await guild.create_category('Tickets')

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            support_role: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=ticket_channel_name,
            category=category,
            overwrites=overwrites,
            reason=f'Ticket for {user}'
        )

        embed = discord.Embed(
            description=(
                f'Hello {user.mention} :wave:\n\n'
                'To expedite your support process, please provide the following information:\n'
                ' - Detailed description of your issue or query\n\n'
                'A member of our staff will assist you shortly.'
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text=NAME, icon_url=ICON)
        embed.set_thumbnail(url=ICON)
        await channel.send(embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f'I have opened a ticket for you at {channel.mention}', ephemeral=True)

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Close Ticket', style=discord.ButtonStyle.red, custom_id='close_ticket_button')
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (interaction.user.guild_permissions.administrator or get(interaction.guild.roles, id=SUPPORT_ROLE_ID) in interaction.user.roles):
            await interaction.response.send_message("You do not have permission to close this ticket.", ephemeral=True)
            return

        if interaction.channel and interaction.channel.name.startswith('ticket-'):
            channel_name = interaction.channel.name
            parts = channel_name.split('-')
            if len(parts) >= 3:
                username = parts[1]
                try:
                    user_id = int(parts[2])
                    user_obj = interaction.guild.get_member(user_id)
                except ValueError:
                    user_obj = None
            else:
                username = "Unknown User"
                user_obj = None

            transcript_text = ''
            async for message in interaction.channel.history(limit=None, oldest_first=True):
                timestamp = message.created_at.strftime('%Y-%m-%d %H:%M')
                author = message.author
                content = message.content
                transcript_text += f"[{timestamp}] {author}: {content}\n"

            transcript_channel = interaction.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
            if transcript_channel:
                embed = discord.Embed(
                    title='Ticket Transcript',
                    description=f'Transcript for {user_obj.mention if user_obj else username}',
                    color=discord.Color.greyple()
                )
                await transcript_channel.send(embed=embed)
                transcript_bytes = io.BytesIO(transcript_text.encode('utf-8'))
                file = discord.File(fp=transcript_bytes, filename='transcript.txt')
                await transcript_channel.send(file=file)
            else:
                await interaction.response.send_message("Transcript channel not found.", ephemeral=True)

            await interaction.response.send_message("Closing this ticket", ephemeral=True)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("This button can only be used in ticket channels.", ephemeral=True)

class TicketBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.added_views = False

    async def setup_hook(self):
        await self.tree.sync()
        self.add_view(TicketCloseView())

    async def on_ready(self):
        if not self.added_views:
            self.add_view(TicketsView())
            self.added_views = True
        print(f'Logged in as {self.user}')

client = TicketBot()

@client.tree.command(name='ticketpanel', description='Create a support ticket panel')
@app_commands.checks.has_permissions(administrator=True)
async def support_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title='Support Tickets',
        description='If you need support, press the button below to open a support ticket. A team member will assist you shortly.',
        color=discord.Color.blue()
    )
    embed.set_footer(text=NAME, icon_url=ICON)
    embed.set_thumbnail(url=ICON)
    await interaction.response.send_message(embed=embed, view=TicketsView())

@support_panel.error
async def support_panel_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

def is_support_or_admin():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        support_role = get(interaction.guild.roles, id=SUPPORT_ROLE_ID)
        if support_role in interaction.user.roles:
            return True
        return False
    return discord.app_commands.check(predicate)

@client.tree.command(name='close', description='Close this ticket')
@is_support_or_admin()
async def close_ticket(interaction: discord.Interaction):
    if interaction.channel and interaction.channel.name.startswith('ticket-'):
        channel_name = interaction.channel.name
        parts = channel_name.split('-')
        if len(parts) >= 3:
            username = parts[1]
            try:
                user_id = int(parts[2])
                user_obj = interaction.guild.get_member(user_id)
            except ValueError:
                user_obj = None
        else:
            username = "Unknown User"
            user_obj = None

        transcript_text = ''
        async for message in interaction.channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime('%Y-%m-%d %H:%M')
            author = message.author
            content = message.content
            transcript_text += f"[{timestamp}] {author}: {content}\n"

        transcript_channel = interaction.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_channel:
            embed = discord.Embed(
                title='Ticket Transcript',
                description=f'Transcript for {user_obj.mention if user_obj else username}',
                color=discord.Color.greyple()
            )
            await transcript_channel.send(embed=embed)
            transcript_bytes = io.BytesIO(transcript_text.encode('utf-8'))
            file = discord.File(fp=transcript_bytes, filename='transcript.txt')
            await transcript_channel.send(file=file)
        else:
            await interaction.response.send_message("Transcript channel not found.", ephemeral=True)

        await interaction.response.send_message("Closing this ticket", ephemeral=True)
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("This command can only be used in ticket channels.", ephemeral=True)

@close_ticket.error
async def close_ticket_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

@client.tree.command(name='add', description='Add a user to this ticket')
@app_commands.describe(user='The user you want to add to the ticket')
@app_commands.checks.has_permissions(administrator=True)
async def add_user(interaction: discord.Interaction, user: discord.Member):
    if interaction.channel and interaction.channel.name.startswith('ticket-'):
        await interaction.channel.set_permissions(
            user,
            view_channel=True,
            send_messages=True,
            attach_files=True,
            embed_links=True
        )
        await interaction.response.send_message(f'{user.mention} has been added to the ticket by {interaction.user.mention}', ephemeral=False)
    else:
        await interaction.response.send_message('This is not a ticket channel.', ephemeral=True)

@client.tree.command(name='remove', description='Remove a user from this ticket')
@app_commands.describe(user='The user you want to remove from the ticket')
@app_commands.checks.has_permissions(administrator=True)
async def remove_user(interaction: discord.Interaction, user: discord.Member):
    if interaction.channel and interaction.channel.name.startswith('ticket-'):
        support_role = get(interaction.guild.roles, id=SUPPORT_ROLE_ID)
        if support_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to remove users from this ticket.", ephemeral=True)
            return

        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f'{user.mention} has been removed from the ticket by {interaction.user.mention}', ephemeral=False)
    else:
        await interaction.response.send_message('This is not a ticket channel.', ephemeral=True)

client.run(TOKEN)
