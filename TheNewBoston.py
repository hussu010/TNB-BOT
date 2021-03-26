import os
import sys
import asyncio
import discord
from discord.ext import commands
import requests
import django
from asgiref.sync import sync_to_async
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.getcwd() + '/API')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "API.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
from main.models import User, Server, Transaction

# ------------------------------------------------------------------------------------ Startup ------------------------------------------------------------------------------------


directory = os.getcwd()
file_directory = directory + "/files"

bot_prefix = os.environ.get('BOT_PREFIX')
token = os.environ.get('DISCORD_TOKEN')
manager_id = int(os.environ.get('MANAGER_ID'))
bot_wallet = os.environ.get('BOT_WALLET')

if None in [bot_prefix, bot_wallet, token, manager_id]:
    raise Exception("Please configure environment variables properly!")

intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix=bot_prefix, intents=intents)


class Register:
	def  __init__(self, user_id, address):
		self.user_id = user_id
		self.address = address


class Guild:
	def __init__(self, server_id, channel_id):
		self.server_id = server_id
		self.channel_id = channel_id

server_list = [] # servers with modified settings
address_holder = []

@client.event
async def on_ready():

	servers = await sync_to_async(Server.objects.all)()

	for server in servers:
		server_list.append(Guild(server.ServerID, server.ChannelID))

	print ("------------------------------------")
	print(f"Bot Name: {client.user.name}")
	print(f"Bot ID: {str(client.user.id)}")
	print(f"Discord Version: {discord.__version__}")
	print ("------------------------------------")
	await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="TNBC grow"))

# ------------------------------------------------------------------------------------ Constant ------------------------------------------------------------------------------------

async def constant():
	while True:
		await asyncio.sleep(3)
		r = requests.get(f"http://13.57.215.62/bank_transactions?format=json&limit=20&recipient={bot_wallet}") 
		info = r.json()
		deposits = await sync_to_async(Transaction.objects.filter)(Type="DEPOSIT")
		for tx in info["results"]:
			print(tx)
			if tx["id"] not in [tx.TxID for tx in deposits]:
				try:
					user = await sync_to_async(User.objects.filter)(Address=tx['block']['sender'])
					await sync_to_async(user.update)(Coins=user[0].Coins+int(tx['amount']))
				except Exception as e:
					print(e)
				newTX = Transaction(Type="DEPOSIT", TxID=tx["id"], Amount=int(tx['amount']))
				newTX.save()

				try:
					user = await client.fetch_user(user[0].DiscordID)
					embed = discord.Embed(title="Success", description=f"Succesfully deposited {tx['amount']} coin(s) into your account", color=0xff0000)
					await user.send(embed=embed)
				except Exception as e:
					print(e)

# ------------------------------------------------------------------------------------ User functions ------------------------------------------------------------------------------------

@client.command(pass_context=True, brief="Register address")
async def register(ctx, address=None):
	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return

	if address == None:
		embed = discord.Embed(title="Register", description=f"To register your address, use the command `>register [address]`. After this, you need to send 1 coin or more to `{bot_wallet}` and then using the command `>verify` to confirm your address.", color=0xff0000)
		await ctx.send(embed=embed)
	elif len(address) < 64:
		embed = discord.Embed(title="Invalid Address", description=f"Please enter a valid address!", color=0xff0000)
		await ctx.send(embed=embed)
	else:
		users = await sync_to_async(User.objects.filter)(DiscordID=ctx.author.id)
		owned = await sync_to_async(User.objects.filter)(Address=address)
		other = False
		potential = None

		for pending in address_holder:
			if pending.address == address:
				other = True
				potential = pending

		if any(users):
			embed = discord.Embed(title="Already Registered", description=f"You already have a registered address: `{users[0].Address}`", color=0xff0000)
			await ctx.send(embed=embed)
			return
		elif other:
			if potential.user_id == ctx.author.id:
				address_holder.remove(potential)
				address_holder.append(Register(ctx.author.id, address))
				await ctx.send(f"Succesfully re-registered with new address. You now have to send 1 coin or more to `{bot_wallet}` from `{address}` and then use the command `>verify` to confirm the address.")
				return
			embed = discord.Embed(title="In Use", description=f"Someone else is already registering this address", color=0xff0000)
			await ctx.send(embed=embed)
			return
		elif any(owned):
			embed = discord.Embed(title="Already Owned", description=f"Someone else is already owns this address.", color=0xff0000)
			await ctx.send(embed=embed)
			return
		else:
			address_holder.append(Register(ctx.author.id, address))
			embed = discord.Embed(title="Send a Coin!", description=f"You now have to send 1 coin or more to `{bot_wallet}` from `{address}` and then use the command `>verify` to confirm the address.", color=0xff0000)
			await ctx.send(embed=embed)


@client.command(pass_context=True, brief="Verify address registration transaction")
async def verify(ctx):
	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return
	for address in address_holder:
		if address.user_id == ctx.author.id:
			r = requests.get(f"http://13.57.215.62/bank_transactions?format=json&limit=1&block__sender={address.address}&recipient={bot_wallet}") # sender and receiver logic needed as well as a user DB
			info = r.json()
			if any(info["results"]):
				query = User(DiscordID=int(ctx.author.id), Address=address.address)
				query.save()
				await ctx.send(f"Address `{address.address}` succesfully associated with {ctx.author.mention}")
				address_holder.remove(address)
			else:
				await ctx.send(f"No transaction detected from `{address.address}`")
			return
	embed = discord.Embed(title="No Address", description=f"No address to verify. Did you make sure to use `{bot_prefix}register [address]`?", color=0xff0000)
	await ctx.send(embed=embed)

@client.command(pass_context=True, brief="Check the verification status of a user")
async def status(ctx, member: discord.Member=None):
	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return

	if not member:
		member = ctx.author

	records = await sync_to_async(User.objects.filter)(DiscordID=member.id)

	if any(records):
		user_address = records[0].Address
		user_coins = records[0].Coins

		r = requests.get(f"http://54.241.124.162/accounts/{user_address}/balance?format=json")
		info = r.json()

		amount = 0
		if any(info):
			amount = info["balance"]

		embed = discord.Embed(title="Status", description=f"{member.name} has a verified address at `{user_address}`\nTheir wallet contains {amount} coins.\n\nTheir discord wallet contains {user_coins} coins", color=0xff0000)
		await ctx.send(embed=embed)
	else:
		embed = discord.Embed(title="Unregistered", description=f"No address could be found for {member.name}", color=0xff0000)
		await ctx.send(embed=embed)


@client.command(pass_context=True, brief="Ways to earn coins")
async def earn(ctx):
	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return

	embed = discord.Embed(title="Earn Coins", description="To earn coins, try completing some tasks: https://thenewboston.com/tasks/All", color=0xff0000)
	await ctx.send(embed=embed)


@client.command(pass_context=True, brief="Ways to earn coins")
async def deposit(ctx):
	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return

	embed = discord.Embed(title="Deposit", description=f"To deposit coins, simply make sure you are registered (`{bot_prefix}status`) and then send coins from your wallet to `{bot_wallet}`", color=0xff0000)
	await ctx.send(embed=embed)


@client.command(pass_context=True, brief="See statistics of the bot")
async def stats(ctx):
	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return

	embed = discord.Embed(title="Bot Stats", color=0xff0000)
	embed.add_field(name='Servers', value=str(len(client.guilds)))
	embed.add_field(name='Users', value=str(len(await sync_to_async(User.objects.all)())))
	await ctx.send(embed=embed)
# ------------------------------------------------------------------------------------ Administrative ------------------------------------------------------------------------------------


@client.command(pass_context=True, brief="secret")
async def kill(ctx):
	if int(ctx.author.id) == manager_id:
		await ctx.message.delete()
		await ctx.send("Recieved shutdown command, shutting down.")
		await asyncio.sleep(1)
		await client.close()
		sys.exit()
		exit()
	else:
		print("nah")

@client.command(pass_context=True, brief="kick member")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
	embed = discord.Embed(title="Member kicked.", description=f"Member kicked: {member.mention}\nReason: {reason}", color=0xff0000)
	await ctx.message.delete()
	await ctx.send(embed=embed)
	await member.kick(reason=reason)

@client.command(pass_context=True, brief="ban member")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
	embed = discord.Embed(title="Member banned.", description=f"Member banned: {member.mention}\nReason: {reason}", color=0xff0000)
	await ctx.message.delete()
	await ctx.send(embed=embed)
	await member.ban(reason=reason)

@client.command(pass_context=True, brief="clear messages")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount=100):
	channel = ctx.message.channel
	messages = []
	async for message in channel.history(limit=amount):
		messages.append(message)
	await channel.delete_messages(messages)
	await ctx.send(f'{str(amount)} messages deleted.')

@client.command(pass_context=True, brief="Set commands channel")
@commands.has_permissions(administrator=True)
async def channel(ctx, channel: discord.TextChannel=None):
	if not channel:
		channel=ctx.channel
		
	query = Server(ServerID=int(ctx.guild.id), ChannelID=int(channel.id))
	query.save()
	server_list.append(Guild(int(ctx.guild.id), int(channel.id)))
	embed = discord.Embed(title="Settings changed", description=f"Commands channel set to: {channel.mention}", color=0xff0000)
	await ctx.send(embed=embed)


client.loop.create_task(constant())
client.run(token)