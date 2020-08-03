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
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
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
	
	async def __userisimmun(self, message, username, userid):
		await self.__replySilence(message, "The user [{}](tg:user?id={}) is immun against this!".format(username, userid))
	
	def __getDisplayname(self, user): # belongs to fosmbot's core
		displayname = []
	
		if user.first_name: displayname.append(user.first_name)
		if user.last_name: displayname.append(user.last_name)
		
		return " ".join(displayname)
	
	def createTimestamp(self): # belongs to fosmbot's core
		return time.strftime("%Y-%m-%d")
	
	async def mydata(self, client, message, userlevel, userlevel_int):
		if not message.chat.type == "private":
			await self.replySilence("Please request access to insights of the data we have about you by issueing that command in private chat with me.")
			return False
		
		if dbhelper.userExists(message.from_user.id):
			await self.reply(message, "The data we have about you (nothing critical):")
			await self.userstat(client, message, userlevel, userlevel_int, ["issuedbyid"])
			await self.reply("One column belonging to you has been stripped off because it contains the telegram id by the user who wrote that comment about you or it has the value `NULL` meaning that no one wrote a comment about you yet. In this case the 'comment' field does not contain anything.")
		else:
			await self.__userNotFound(message, self.__getDisplayname(message.from_user))
	
	async def changecomment(self, client, message, userlevel, userlevel_int):
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			command[0] = message.reply_to_message.from_user.id
		
		if not len(command) > 1:
			await self.__replySilence(message, "Syntax: `/changecomment <username> <comment>`. To have `<username>` to be automatically filled out, reply the command to a message from the user in question")
			return False
		
		command[0] = str(command[0])
		userInQuestion = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userInQuestion)
				return False
		userInQuestion_id = command[0]
		del command[0]
		
		dbhelper.sendToPostgres(config["updatecomment"], (" ".join(command), int(userInQuestion_id)))
		message.reply("Comment about [{}](tg:user?id={}) changed".format(userInQuestion, str(userInQuestion_id)))
	
	async def testme(self, client, message, userlevel, userlevel_int):
		await self.__replySilence(message, "Tested me!")
	
	async def changelevel(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			command[0] = message.reply_to_message.from_user.id
		
		if not len(command) == 2:
			await self.__replySilence(message, "Syntax: `/changelevel <username> <level>`. To have `<username>` to be automatically filled out, reply the command to a message from the user in question")
			return False
		
		
		levelToPromoteTo_int = config["LEVELS"].index(command[1])
		if not levelToPromoteTo_int > userlevel_int: # if true, then the user who issued that command has no rights to promote <user> to <level>
			return False # user does not have the right to promote <user> to <level>
		
		command[0] = str(command[0])
		userToPromote = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userToPromote)
				return False
		
		userToPromote_int = config["LEVELS"].index(dbhelper.getuserlevel(command[0]))
		if not userToPromote_int > userlevel_int: # if true, then the user who issued that command has no rights to promote <user> to <level>
			return False
		
		dbhelper.sendToPostgres(config["changeLevel"], (command[1], command[0]))
		await self.__logGroup(message, "User [{}](tg:user?id={}) is now a `{}` one as requested by [{}](tg:user?id={}) with level `{}`".format(userToPromote, userToPromote_int, command[1], self.__getDisplayname(message.from_user), message.from_user.id, userlevel))
	
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
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			command[0] = message.reply_to_message.from_user.id
		
		if len(command) == 0:
			await self.__reply(message, "Syntax: `/funban <username>`. To have `<username>` to be automatically filled out, reply the command to a message from the user in question")
			return False
		
		command[0] = str(command[0])
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userinput)
				return False
		
		if not dbhelper.userHasLevel(command[0], "banned"):
			await self.__replySilence(message, "User [{}](tg:user?id={}) hasn't been banned or they are immun against bans".format(userinput, toban))
			return False
		
		dbhelper.sendToPostgres(config["updatecomment"], ("unbanned", int(command[0])))
		dbhelper.sendToPostgres(config["updateissuedbyid"], (message.from_user.id, int(command[0])))
		dbhelper.sendToPostgres(config["changeLevel"], ("user", int(command[0])))
		
		groups = dbhelper.sendToPostgres(config["getgroups"])
		for group in groups:
			app.unban_chat_member(group, command[0])
		
		await self.__logGroup(message, "**Unbanned** user [{}](tg://user?id={}) from federation 'osmallgroups'".format(userinput, command[0]))
	
	async def fban(self, client, message, userlevel, userlevel_int):
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			command[0] = message.reply_to_message.from_user.id
		
		if not len(command) > 2:
			await self.__replySilence(message, "Please provide a reason to ban a user for {} days. Syntax: `/fban <username> <reason>`. To have `<username>` to be automatically filled out, reply the command to a message from the user in question".format(str(config["daystoban"])))
			return False
		
		command[0] = str(command[0])
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userinput)
				return False
		toban = int(command[0])
		del command[0]
		
		if dbhelper.userHasLevel(toban, "banned"):
			await self.__replySilence(message, "User [{}](tg:user?id={}) already banned".format(userinput, toban))
			return False
		
		toban_level = dbhelper.getuserlevel(toban)
		if toban_level in config["immunity"]:
			await self.__userisimmun(message, userinput, toban);
			return False
		
		dbhelper.sendToPostgres(config["updatecomment"], (" ".join(command), toban))
		dbhelper.sendToPostgres(config["updateissuedbyid"], (message.from_user.id, toban))
		dbhelper.sendToPostgres(config["changeLevel"], ("banned", toban))
		
		groups = dbhelper.sendToPostgres(config["getgroups"])
		for group in groups:
			app.kick_chat_member(group, toban, int(time.time() + 60*60*24*int(config["daystoban"]))) # kick chat member and automatically unban after ... days
		
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
		
		command[0] = str(command[0])
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
		config["botowner"] = command[0]
		await self.__logGroup(message, "Ownership changed from [{}](tg://user?id={}) to [{}](tg://user?id={}). The new ownership will be ensured by a file on the server".format(self.__getDisplayname(message.from_user),  message.from_user.id, userinput, command[0]))
	
	async def addgroup(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		if message.chat.type == "private" or message.chat.type == "channel":
			return False
		
		if not dbhelper.sendToPostgres(config["getgroup"], (message.chat.id,)):
			dbhelper.sendToPostgres(config["authorizegroup"], (message.chat.id,))
			await self.__logGroup(message, "Added group [{}](tg:group?id={}). Now it belongs to the federation 'osmallgroups'".format(message.chat.title, message.chat.id))
	
	async def removegroup(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		if message.chat.type == "private" or message.chat.type == "channel":
			return False
		
		if dbhelper.sendToPostgres(config["getgroup"], (message.chat.id,)):
			dbhelper.sendToPostgres(config["deauthorizegroup"], (message.chat.id,))
			await self.__logGroup(message, "Removed group [{}](tg:group?id={}). It does not longer belong to the federation 'osmallgroups'. Past fbans won't be recovered for this group.".format(message.chat.title, message.chat.id))
	
	async def search(self, client, message, userlevel, userlevel_int):
		if not message.chat.type == "private":
			return False
		
		output = dbhelper.sendToPostgres(config["getusersbydisplayname"], (" ".join(command),))
		
		users = []
		for user in output:
			users.append(output[user])
		
		output = ["Search results for users with name '{}':".format(" ".join(command))]
		for user in users:
			output.append("[{}](tg:user?id={}) - `{}`".format(user["username"], user["id"], user["id"]))
		
		await self.reply(message, "<br />".join(output))
		
	async def __returnusers(self, message, level):
		if not message.chat.type == "private":
			return False
		output = []
		
		users = dbhelper.sendToPostgres(config["getusersbylevel"], (level,))
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
		banned = dbhelper.sendToPostgres(config["getusersbylevel"], ("banned",))
		
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
	
	async def userstat(self, client, message, userlevel, userlevel_int, exclude=[]):
		if not message.chat.type == "private":
			return False
	
		command = message.command
		
		if len(command) == 0:
			await self.__reply(message, "Syntax `/userstat <username>` not used.")
			return True
		
		command[0] = str(command[0])
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userinput)
				return False
		
		user = dbhelper.sendToPostgres(config["getuser"], (command[0],))
		for i in user:
			user = user[i]
		
		output = ["[{}](tg:user?id={}):".format(user["displayname"], user["id"])]
		columntrans = {"id": "Telegram id", "username": "Username", "displayname": "Name", "level": "Access level", "comment": "Comment", "issuedbyid": "Comment by", "ts": "Record created at"}
		for i in user:
			label = i
			if label in columntrans:
				label = str(columntrans[i])
			if not i in exclude:
				output.append("**{}**: {}".format(label, user[i]))
		
		await self.__reply(message, "<br />".join(output))
	
	async def mystat(self, client, message, userlevel, userlevel_int):
		message.command = [message.from_user.id]
		await self.userstat(client, message, userlevel, userlevel_int, ["issuedbyid"])
	
	async def mylevel(self, client, message, userlevel, userlevel_int):
		if not message.chat.type == "private":
			return False
		
		await self.__reply(message, "You are".format(userlevel))
	
	async def groupid(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		if "chat" in dir(message) and message.chat is not None:
			await self.__replySilence(message, "Chat id `{}`".format(str(message.chat.id)))
	
	async def myid(self, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		if not message.chat.type == "private":
			return False
		
		await self.__replySilence(message, "Your id `{}`".format(str(message.from_user.id)))
		
	async def execCommand(self, command, client, message, userlevel, userlevel_int): # belongs to fosmbot's core
		if not command[0].startswith("__") or not command[0].startswith("noncmd"):
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
	config["botowner"] = int(readOwner())
	
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
		else:
			dbhelper.sendToPostgres(config["updatedisplayname"], (displayname, user.id))
	
	if user.id == config["botowner"]:
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
			if "chat" in dir(message) and message.chat is not None:
				objid = message.chat.id
			else:
				objid = message.from_user.id
			
			if "groupspecified" in config:
				if command[0] in config["groupspecified"]:
					if not objid == 0 and str(objid) in config["groupspecified"][command[0]]:
						await commander.execCommand(command, client, message, userlevel, rightlevel)
						return True
					else:
						await message.reply("Command not available to you. It is either just executable in a specified group or just available for a specified user.")
						return False
			
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
	
	if "forward_from" in dir(message) and message.forward_from is not None:
		addUserToDatabase(message.forward_from)

if __name__ == "__main__":
	logging.info("starting fosmbot...")
	app.run()
