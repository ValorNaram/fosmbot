#!/usr/bin/env python3
from lib import database # belongs to fosmbot's core
from lib import dbsetup # belongs to fosmbot's core
import logging, yaml, pyrogram, time, os # belongs to fosmbot's core

config = {} # belongs to fosmbot's core
dbhelper = None # belongs to fosmbot's core
commander = None # belongs to fosmbot's core
allcommands = [] # belongs to fosmbot's core
app = None # belongs to fosmbot's core

def changeOwnerInFile(ownerid, write=True): # belongs to fosmbot's core
	sfile = open("botowner.txt", "w")
	sfile.write(str(ownerid))
	sfile.close()

def readOwner(): # belongs to fosmbot's core
	sfile = open("botowner.txt", "r")
	filebuffer = sfile.read()
	sfile.close
	return filebuffer.replace("\n", "")

class commandControl():
	def __init__(self):
		pass
	
	def __getUserInQuestion(self, message): # belongs to fosmbot's core
		if "reply_to_message" in dir(message):
			return message.reply_to_message.from_user.id
	async def __ownerCannotDo(self, message):
		await message.reply("An owner cannot do this", disable_web_page_preview=True)
	
	async def __userNotFound(self, message, user):
		await message.reply("User '{}' does not exist in the database".format(user), disable_web_page_preview=True, disable_notification=True)
		
	async def __reply(self, message, text): # belongs to fosmbot's core
		await message.reply(text, disable_web_page_preview=True)
	
	async def __replySilence(self, message, text): # belongs to fosmbot's core
		await message.reply(text, disable_web_page_preview=True, disable_notification=True)
	
	async def __logGroup(self, message, text): # belongs to fosmbot's core
		if "logchannel" in config:
			await app.send_message(int(config["logchannel"]), text, disable_web_page_preview=True)
		await self.__replySilence(message, text)
	
	async def __getDisplayname(self, message): # belongs to fosmbot's core
		displayname = []
	
		if user.first_name: displayname.append(user.first_name)
		if user.last_name: displayname.append(user.last_name)
		
		return " ".join(displayname)
	
	async def createTimestamp(self): # belongs to fosmbot's core
		return time.strftime("%Y-%m-%d")
	
	async def changeLevel(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		command = message.command
		
		if "reply_to_message" in dir(message):
			command[1] = message.reply_to_message.from_user.id
		
		if not len(command) == 2:
			await self.__replySilence(message, "Syntax: `/changeLevel <level> <user>`")
			return False
		
		
		levelToPromoteTo_int = config["LEVELS"].index(command[0])
		if not levelToPromoteTo_int > userlevel_int: # if true, then the user who issued that command has no rights to promote <user> to <level>
			return False # user does not have the right to promote <user> to <level>
		
		userToPromote = command[1]
		if command[1].startswith("@"): # if true, then resolve username to telegram id
			command[1] = dbhelper.resolveUsername(command[1])
			if command[1].startswith("error"):
				await self.__userNotFound(message, userToPromote)
		
		userToPromote_int = config["LEVELS"].index(dbhelper.getuserlevel(command[1]))
		if not userToPromote_int > userlevel_int: # if true, then the user who issued that command has no rights to promote <user> to <level>
			return False
		
		dbhelper.sendToPostgres(config["changeLevel"], (command[0], int(command[1])))
	
	async def demoteme(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		if not message.chat.type == "private":
			return False
		
		if userlevel == "owner":
			await self.__ownerCannotDo(message)
		else:
			dbhelper.sendToPostgres(config["changeLevel"], ("user", message.from_user.id))
			await self.__reply(message, "You are now powerless! Thank You for your effort to cut down spammers!")
	
	async def funban(self, client, message, userlevel, userlevel_int):
		command = message.command
		
		if "reply_to_message" in dir(message):
			command[0] = message.reply_to_message.from_user.id
		
		if len(command) == 0:
			await self.__reply(message, "Syntax: `/funban <username>`")
			return False
		
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userinput)
				return False
		
		dbhelper.sendToPostgres(config["updatecomment"], ("unbanned"))
		dbhelper.sendToPostgres(config["updateissuedbyid"], (message.from_user.id, command[0]))
		dbhelper.sendToPostgres(config["changeLevel"], ("user", command[0]))
		
		groups = dbhelper.sendToPostgres(config["getgroups"])
		for group in groups:
			app.unban_chat_member(group, command[0])
		
		await self.__logGroup(message, "**Unbanned** user [{}](tg://user?id={}) from federation 'osmallgroups'".format(userinput, command[0]))
	
	async def fban(self, client, message, userlevel, userlevel_int):
		command = message.command
		
		if "reply_to_message" in dir(message):
			command[0] = message.reply_to_message.from_user.id
		
		if not len(command) > 2:
			await self.__replySilence(message, "Please provide a reason to ban a user for 365 days. Syntax: `/fban <username> <reason>".format(userToPromote))
			return False
		
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userinput)
				return False
		toban = int(command[0])
		del command[0]
		
		dbhelper.sendToPostgres(config["updatecomment"], (" ".join(command)))
		dbhelper.sendToPostgres(config["updateissuedbyid"], (message.from_user.id, toban))
		dbhelper.sendToPostgres(config["changeLevel"], ("banned", toban))
		
		groups = dbhelper.sendToPostgres(config["getgroups"])
		for group in groups:
			app.kick_chat_member(group, toban, int(time.time() + 31536000)) # kick chat member and automatically unban after 365 days
		
		await self.__logGroup(message, "**Banned** user [{}](tg://user?id={}) from federation 'osmallgroups' for 365 days".format(userinput, toban))
		
	async def newowner(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		if not message.chat.type == "private":
			return False
		
		command = message.command
		
		if len(command) == 0:
			await self.__reply(message, "Command to transfer Ownership of 'osmallgroups' federation. Syntax: `/newowner <username>`")
			return False
		if not userlevel_int == 0:
			return False
		
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__reply(message, "Command to transfer Ownership of 'osmallgroups' federation issued but couldn't execute it:")
				await self.__userNotFound(message, userinput)
				return False
		
		dbhelper.sendToPostgres(config["changeLevel"], ("owner", int(command[0])))
		dbhelper.sendToPostgres(config["changeLevel"], ("user", message.from_user.id))
		
		changeOwnerInFile(command[0])
		await self.__logGroup(message, "Ownership changed from [{}](tg://user?id={}) to [{}](tg://user?id={}). The new ownership will be ensured by a file on the server".format(self.__getDisplayname(message.from_user),  message.from_user.id, userinput, command[0]))
	
	async def addgroup(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		dbhelper.sendToPostgres(config["authorizegroup"], (message.chat.id))
		await self.__logGroup(message, "Added group [{}](tg:group?id={}). Now it belongs to the federation 'osmallgroups'".format(self.__getDisplayname(message.chat), message.chat.id))
	
	async def removegroup(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		dbhelper.sendToPostgres(config["deauthorizegroup"], (message.chat.id))
		await self.__logGroup(message, "Removed group [{}](tg:group?id={}). It does not longer belong to the federation 'osmallgroups'. Past fbans won't be recovered for this group.".format(self.__getDisplayname(message.chat), message.chat.id))
	
	async def __returnusers(self, message, level):
		if not message.chat.type == "private":
			return False
		output = []
		
		users = dbhelper.sendToPostgres(config["getusersbylevel"], (level))
		for userid in users:
			output.append(users[userid]["username"] + "<br />")
		
		await self.__reply(message, "- ".join(output))
	
	async def owners(self, client, message, userlevel, userlevel_int):
		await self.__returnusers(message, "owner")
		
	async def fedadmins(self, client, message, userlevel, userlevel_int):
		await self.__returnusers(message, "fedadmin")
	
	async def superadmins(self, client, message, userlevel, userlevel_int):
		await self.__returnusers(message, "superadmin")
	
	async def fbanlist(self, client, message, userlevel, userlevel_int):
		if message.chat.type == "group":
			return False
		
		output = ["id", "username", "displayname", "reason", "issued"]
		banned = dbhelper.sendToPostgres(config["getusersbylevel"], ("banned"))
		
		for userid in banned:
			line = []
			row = banned[userid]
			for field in row:
				line.append("\"" + field + "\"")
			output.append(",".join(output))
		
		sfile = open("fbanlist.csv", "w")
		sfile.write("\n".join(output))
		sfile.close()
		
		await message.reply_document("fbanlist.csv")
	
	async def fstat(self, client, message, userlevel, userlevel_int):
		if not message.chat.type == "private":
			return False
	
		command = message.command
		
		if len(command) == 0: # becomes /mylevel
			await self.__reply(message, "Syntax `/fstat <username>` not used. Executing `/mylevel` command")
			await self.mylevel(self, client, message, userlevel, userlevel_int)
			return True
		
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userinput)
				return False
		
		userlevel = dbhelper.getuserlevel(command[0])
		await self.__reply(message, "'{}' has the level: {}".format(userinput, userlevel))
	
	async def mylevel(self, client, message, userlevel, userlevel_int):
		if not message.chat.type == "private":
			return False
		
		await self.__reply(message, "You have the level: {}".format(userlevel))
	
	async def groupid(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		if "chat" in dir(message):
			await self.__replySilence(message, "Chat id `{}`".format(str(message.chat.id)))
	
	async def myid(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		if not message.chat.type == "private":
			return False
		
		await self.__replySilence(message, "Your id `{}`".format(str(message.from_user.id)))
		
	async def execCommand(self, command, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		if not command[0].startswith("__"):
			func = message.command[0]
			del message.command[0]
			await self.__getattribute__(func)(client, message, userlevel, userlevel_int)

def main(): # belongs to fosmbot's core
	global config, dbhelper, commander, allcommands, app
	
	config = {}
	logging.basicConfig(format='[osmallgroups Bot]: %(asctime)s %(message)s', level=logging.DEBUG, datefmt="%m/%d/%Y %I:%M:%S %p")
	app = pyrogram.Client("fosm")
	
	logging.info("loading 'fosmbot.yml' configuration...")
	sfile = open("fosmbot.yml", "r")
	config = yaml.safe_load(sfile)
	sfile.close()
	
	logging.info("loading available commands...")
	for level in config["LEVELS"]:
		for command in config["LEVEL_" + level.upper()]:
			allcommands.append(command)
	
	logging.info(allcommands)
	if not "dbconnstr" in config:
		logging.info("generating 'dbconnstr'...")
		config["dbconnstr"] = "host={} port={} user={} password={} dbname={}".format(config["DATABASE_HOST"], config["DATABASE_PORT"], config["DATABASE_USER"], config["DATABASE_USER_PASSWD"], config["DATABASE_DBNAME"])
	else:
		logging.info("using predefined 'dbconnstr' instead of generating one...")
	
	logging.info("ensuring owner...")
	config["botowner"] = readOwner()
	
	logging.info("perform automatic set up...")
	dbsetup.setupDB(config)
	logging.info("automatic set up performed!")
	
	logging.info("connecting to database...")
	dbhelper = database.helper(config)
	
	commander = commandControl()

if __name__ == "__main__":
	main()

def addUserToDatabase(user): # belongs to fosmbot's core
	displayname = []
	
	if user.first_name: displayname.append(user.first_name)
	if user.last_name: displayname.append(user.last_name)
		
	displayname = " ".join(displayname)
		
	if not user.is_self and not user.is_deleted and not user.is_bot and not user.is_verified and not user.is_support:
		if not dbhelper.userExists(user.id):
			dbhelper.sendToPostgres(config["adduser"], (user.id, user.username.lower(), displayname, commander.createTimestamp()))
	
	if user.id == config[config["botowner"]]:
		if not dbhelper.userHasLevel(config["botowner"], "owner"):
			logging.info("  setting user '{}' ({}) as owner".format(displayname, user.id))
			dbhelper.sendToPostgres(config["changeLevel"], ("owner", int(config["botowner"])))

@app.on_message(pyrogram.Filters.command(allcommands))
async def postcommandprocessing(client, message): # belongs to fosmbot's core
	print("##################################################################################################") # Kept for debugging purpose
	addUserToDatabase(message.from_user)
	command = message.command
	if command is str:
		command = [command]
		message.command = [message.command]
	
	userlevel = dbhelper.getuserlevel(message.from_user.id)
	rightlevel = config["LEVELS"].index(userlevel)
	
	for i in range(rightlevel, len(config["LEVELS"])):
		if command[0] in config["LEVEL_" + config["LEVELS"][i].upper()]:
			objid = 0
			if "chat" in dir(message):
				objid = message.chat.id
			else:
				objid = message.from_user.id
			
			if "GROUPCOMMANDS" in config:
				if command[0] in config["GROUPCOMMANDS"]:
					if not objid == 0 and str(objid) in config["GROUPCOMMANDS"][command[0]]:
						await commander.execCommand(command, client, message, userlevel, rightlevel)
						return True
				else:
					await commander.execCommand(command, client, message, userlevel, rightlevel)
					return True
	
	await message.reply("Insufficient rights. You are: {}".format(userlevel), disable_web_page_preview=True)

@app.on_message(pyrogram.Filters.new_chat_members)
async def userjoins(client, message): # belongs to fosmbot's core
	newmembers = message.new_chat_members
	if newmembers is not list:
		newmembers = [newmembers]
	
	for member in newmembers:
		addUserToDatabase(member)

@app.on_message()
async def messageFromUser(client, message): # belongs to fosmbot's core
	addUserToDatabase(message.from_user)
	
	if "forward_from" in dir(message):
		addUserToDatabase(message.forward_from)

if __name__ == "__main__":
	logging.info("starting fosmbot...")
	app.run()
