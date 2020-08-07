#!/usr/bin/env python3
from lib import database # belongs to fosmbot's core
from lib import dbsetup # belongs to fosmbot's core
import logging, yaml, pyrogram, time, os, threading # belongs to fosmbot's core

exitFlag = 0 # belongs to fosmbot's core
threads = [] # belongs to fosmbot's core
config = {} # belongs to fosmbot's core
dbhelper = None # belongs to fosmbot's core
commander = None # belongs to fosmbot's core
allcommands = [] # belongs to fosmbot's core
app = None # belongs to fosmbot's core

def changeOwnerInFile(ownerid): # belongs to fosmbot's core
	sfile = open("botowner.txt", "w")
	sfile.write(str(ownerid))
	sfile.close()

def readOwner(): # belongs to fosmbot's core
	sfile = open("botowner.txt", "r")
	filebuffer = sfile.read()
	sfile.close
	return filebuffer.replace("\n", "")

def createExpireTime(creationTime): # belongs to fosmbot's core
	expireAt = config["DATABASE_ENTRY_EXPIRE_MONTH"]
		
	if int(creationTime[1]) == 12:
		creationTime[0] = int(creationTime[0])+1
		creationTime[1] = 0
		
	creationTime[1] = int(creationTime[1])+expireAt
	targettime_float = time.mktime((int(creationTime[0]), int(creationTime[1]), int(creationTime[2]),0,0,0,6,0,-1))
	
	return targettime_float

class dbcleanup(threading.Thread): # belongs to fosmbot's core
	def __init__(self):
		threading.Thread.__init__(self)
	
	def isExpired(self, creationTime):
		creationTime = str(creationTime)
		creationTime = creationTime.split(" ")[0].split("-")
		
		targettime_float = createExpireTime(creationTime)
		
		if time.time() > targettime_float: # database entry expired
			return True
		return False
	
	def docleanup(self):
		with dbhelper.conn:
			with dbhelper.conn.cursor() as cursor:
				if exitFlag == 1:
					cursor.close()
					return False
				logging.info("Performing a database clean up...")
				cursor.execute(config["dbcleanupbyts"], ("user",))
				
				if not cursor.description == None:
					columns = []
					for col in cursor.description:
						columns.append(col.name)
					result = [0]
					
					while len(result) > 0:
						result = cursor.fetchmany(20)
						output = dbhelper.toJSON(result, columns, cursor)
						for user in output:
							if exitFlag == 1:
								logging.info("Cleaning up database interrupted, closing transaction...")
								cursor.close()
								return False
							if self.isExpired(output[user]["ts"]):
								dbhelper.sendToPostgres(config["removeuser"], (output[user]["id"],))
		
		logging.info("Database clean up performed. Repeat in '{}' hour(s)".format(int(config["DATABASE_CLEANUP_HOUR"])))
	
	def run(self):
		while exitFlag == 0:
			for i in range(0, 60*60*int(config["DATABASE_CLEANUP_HOUR"])):
				if exitFlag == 1:
					logging.info("Database cleanup schedule canceled!")
					return False
				time.sleep(1)
			
			self.docleanup()
		logging.info("Database cleanup stopped!")
	
class commandControl():
	async def __canTouchUser(self, message, userInQuestion, issuer_level, targetuserdata):
		userInQuestion_level, targetuserdata = dbhelper.getuserlevel(userInQuestion, targetuserdata)
		userInQuestion_level = config["LEVELS"].index(userInQuestion_level)
		if userInQuestion_level > issuer_level: # if true, then the user (issuer_level) who issued that command has rights to touch user in question (userInQuestion)
			return True
		await self.__replySilence(message, "You don't have the necessary rights to touch the user!")
		return False
	def noncmd_getChatUsername(self, message):
		username = ""
		if "username" in dir(message.chat) and message.chat.username is not None:
			username = message.chat.username
		else:
			username = str(message.chat.id)
		
		return username.lower()
	
	async def noncmd_performBan(self, message, toban, issuer, targetuserdata):
		for i in issuer:
			issuer = issuer[i]
		for i in targetuserdata:
			targetuserdata = targetuserdata[i]
		
		for group in targetuserdata["groups"]:
			try:
				await app.kick_chat_member(int(group), toban, int(time.time() + 60*60*24*int(config["daystoban"]))) # kick chat member and automatically unban after ... days
			except:
				try:
					app.send_message(int(group), "[{}](tg://user?={}) **banned** user [{}](tg://user?id={}) from federation 'osmallgroups'. However that user couldn't be banned from this group. **Do I have the right to ban them here?**".format(issuer["displayname"], issuer["id"], targetuserdata["displayname"], toban))
				except:	
					pass
		
		await self.__logGroup(message, "[{}](tg://user?={}) **banned** user [{}](tg://user?id={}) from federation 'osmallgroups' for 365 days".format(issuer["displayname"], issuer["id"], targetuserdata["displayname"], toban))
	
	async def __performUnban(self, message, toban, issuer, targetuserdata):
		for i in issuer:
			issuer = issuer[i]
		for i in targetuserdata:
			targetuserdata = targetuserdata[i]
		
		groups = targetuserdata["groups"]
		for group in targetuserdata["groups"]:
			try:
				await app.unban_chat_member(int(group), toban)
			except:
				try:
					app.send_message(int(group), "[{}](tg://user?={}) **unbanned** user [{}](tg://user?id={}) from federation 'osmallgroups'. However that user couldn't be unbanned from this group. **Do I have the right to unban them here?**".format(issuer["displayname"], issuer["id"], targetuserdata["displayname"], toban))
				except:	
					pass
		
		await self.__logGroup(message, "[{}](tg://user?={}) **unbanned** user [{}](tg://user?id={}) from federation 'osmallgroups'.".format(issuer["displayname"], issuer["id"], targetuserdata["displayname"], toban))
	
	async def __ownerCannotDo(self, message):
		await message.reply("An owner cannot do this", disable_web_page_preview=True, parse_mode="md")
	
	async def __userNotFound(self, message, user):
		await message.reply("User '{}' does not exist in the database".format(user), disable_web_page_preview=True, disable_notification=True, parse_mode="md")
		
	async def __reply(self, message, text): # belongs to fosmbot's core
		await message.reply(text, disable_web_page_preview=True, parse_mode="md")
	
	async def __replySilence(self, message, text): # belongs to fosmbot's core
		await message.reply(text, disable_web_page_preview=True, disable_notification=True, parse_mode="md")
	
	async def __logGroup(self, message, text): # belongs to fosmbot's core
		if "logchannel" in config:
			await app.send_message(int(config["logchannel"]), text, disable_web_page_preview=True, parse_mode="md")
		await self.__replySilence(message, text)
	
	async def __userisimmun(self, message, username, userid, targetuserdata):
		for i in targetuserdata:
			targetuserdata = targetuserdata[i]
		await self.__replySilence(message, "The user [{}](tg://user?id={}) is immun against this!".format(targetuserdata["displayname"], userid))
	
	def noncmd_getDisplayname(self, user): # belongs to fosmbot's core
		displayname = []
		if user is not None:
			if not user.first_name is None: displayname.append(user.first_name)
			if not user.last_name is None: displayname.append(user.last_name)
		
		if len(displayname) == 0:
			if user.username is None:
				displayname.append("Unnamed")
			else:
				displayname.append(user.username.replace("@", ""))
		return " ".join(displayname)
	
	def createTimestamp(self): # belongs to fosmbot's core
		return time.strftime("%Y-%m-%d")
	
	async def viewgroups(self, client, message, userlevel, userlevel_int, userdata):
		if not message.chat.type == "private":
			return False
		
		groups = config["groupslist"]
		out = []
		
		for i in groups:
			group = groups[i]
			out.append("- {} (`{}`)".format("@" + str(group["id"]), str(i)))
		out.append("\n**{} groups** participate in the federation".format(str(len(groups))))
		
		await self.__reply(message, "\n".join(out))
		
	async def removedata(self, client, message, userlevel, userlevel_int, userdata):
		if not message.chat.type == "private":
			return False
		
		targetuserdata = {}
		command = message.command
		
		command[0] = str(command[0])
		targetuserInQuestion = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0], targetuserdata = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, targetuserInQuestion)
				return False
		targetuserInQuestion_id = command[0]
		del command[0]
		
		dbhelper.sendToPostgres(config["removeuser"], (targetuserInQuestion_id,))
		for i in targetuserdata:
			targetuserdata = targetuserdata[i]
		await self.__reply(message, "**Removed user** [{}](tg://user?id={}) from the known users list. A `/adduser` command does not exist but I will recreate the user for you if you forward a message from them to me!".format(targetuserdata["displayname"], targetuserInQuestion_id))
	
	async def help(self, client, message, userlevel, userlevel_int, userdata):
		if not message.chat.type == "private":
			await self.__replySilence(message, "Please issue that command in the private chat with me in order to view the help.")
			return False
		
		if os.path.exists("files/help.md"):
			sfile = open("files/help.md", "r")
			filebuffer = sfile.read()
			sfile.close()
		
			await self.__reply(message, filebuffer)
		else:
			await self.__reply(message, "**No help available**")
	
	async def start(self, client, message, userlevel, userlevel_int, userdata):
		await self.help(client, message, userlevel, userlevel_int, userdata)
	
	async def mydata(self, client, message, userlevel, userlevel_int, userdata):
		if not message.chat.type == "private":
			await self.__replySilence("Please request access to insights of the data we have about you by issueing that command in private chat with me.")
			return False
		
		if dbhelper.userExists(message.from_user.id, userdata):
			message.command = [message.from_user.id]
			await self.__reply(message, "The data we have about you (nothing critical):")
			await self.userstat(client, message, userlevel, userlevel_int, userdata, ["issuedbyid"])
			await self.__reply(message, "One column belonging to you has been stripped off because it contains the telegram id by the user who wrote that comment about you or it has the value `NULL` meaning that no one wrote a comment about you yet. In this case the 'comment' field does not contain anything.")
		else:
			await self.__userNotFound(message, self.noncmd_getDisplayname(message.from_user))
	
	async def privacypolicy(self, client, message, userlevel, userlevel_int, userdata):
		if not message.chat.type == "private":
			await self.__replySilence(message, "Please issue that command in the private chat with me in order to view the privacy policy.")
			return False
		
		if os.path.exists("files/privacypolicy.md"):
			sfile = open("files/privacypolicy.md", "r")
			filebuffer = sfile.read()
			sfile.close()
		
			await self.__reply(message, filebuffer)
		else:
			await self.__reply(message, "**No Privacy Policy available**")
	
	async def changecomment(self, client, message, userlevel, userlevel_int, userdata):
		targetuserdata = {}
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			newcommand = [message.reply_to_message.from_user.id]
			for i in command:
				newcommand.append(i)
			command = newcommand
		
		if not len(command) > 1:
			await self.__replySilence(message, "Syntax: `/changecomment <username or id> <comment>`. To have `<username or id>` to be automatically filled out, reply the command to a message from the user in question")
			return False
		
		command[0] = str(command[0])
		targetuserInQuestion = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0], targetuserdata = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, targetuserInQuestion)
				return False
		if len(targetuserdata) == 0:
			targetuserdata = dbhelper.sendToPostgres(config["getuser"], (command[0],))
		targetuserInQuestion_id = command[0]
		
		del command[0]
		
		if not await self.__canTouchUser(message, targetuserInQuestion_id, userlevel_int, targetuserdata) or targetuserInQuestion_id in config["botownerrecord"]:
			return False
		
		dbhelper.sendToPostgres(config["updatecomment"], (" ".join(command), int(targetuserInQuestion_id)))
		for i in targetuserdata:
			targetuserdata = targetuserdata[i]
		await self.__reply(message, "Comment about [{}](tg://user?id={}) changed".format(targetuserdata["displayname"], str(targetuserInQuestion_id)))
	
	async def testme(self, client, message, userlevel, userlevel_int, userdata):
		await self.__replySilence(message, "Tested me!")
	
	async def changelevel(self, client, message, userlevel, userlevel_int, userdata): # belongs to fosmbot's core
		targetuserdata = {}
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			newcommand = [message.reply_to_message.from_user.id]
			for i in command:
				newcommand.append(i)
			command = newcommand
		
		if not len(command) == 2:
			await self.__replySilence(message, "Syntax: `/changelevel <username or id> <level>`. To have `<username or id>` to be automatically filled out, reply the command to a message from the user in question")
			return False
		
		try:
			levelToPromoteTo_int = config["LEVELS"].index(command[1])
		except:
			await self.__replySilence(message, "Level `{}` does not exist!".format(command[1]))
		
		if not levelToPromoteTo_int > userlevel_int: # if true, then the user who issued that command has no rights to promote <user> to <level>
			return False # user does not have the right to promote <user> to <level>
		
		command[0] = str(command[0])
		userToPromote = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0], targetuserdata = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userToPromote)
				return False
		if len(targetuserdata) == 0:
			targetuserdata = dbhelper.sendToPostgres(config["getuser"], (command[0],))
		
		if not await self.__canTouchUser(message, command[0], userlevel_int, targetuserdata) or command[0] in config["botownerrecord"]:
			return False
		
		dbhelper.sendToPostgres(config["changelevel"], (command[1], command[0]))
		for i in targetuserdata:
			targetuserdata = targetuserdata[i]
		for i in userdata:
			userdata = userdata[i]
		await self.__logGroup(message, "User [{}](tg://user?id={}) is now a `{}` one as requested by [{}](tg://user?id={}) with level `{}`".format(targetuserdata["displayname"], command[0], command[1], userdata["displayname"], message.from_user.id, userlevel))
	
	async def demoteme(self, client, message, userlevel, userlevel_int, userdata): # belongs to fosmbot's core
		if not message.chat.type == "private":
			return False
		
		if userlevel_int == 0:
			await self.__ownerCannotDo(message)
		else:
			dbhelper.sendToPostgres(config["changelevel"], ("user", message.from_user.id))
			await self.__reply(message, "You are now powerless! Thank You for your effort to cut down spammers!")
	
	async def funban(self, client, message, userlevel, userlevel_int, userdata):
		targetuserdata = {}
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			newcommand = [message.reply_to_message.from_user.id]
			for i in command:
				newcommand.append(i)
			command = newcommand
		
		if len(command) == 0:
			await self.__reply(message, "Syntax: `/funban <username or id>`. To have `<username or id>` to be automatically filled out, reply the command to a message from the user in question")
			return False
		
		command[0] = str(command[0])
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0], targetuserdata = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userinput)
				return False
		if len(targetuserdata) == 0:
			targetuserdata = dbhelper.sendToPostgres(config["getuser"], (command[0],))
		
		if not dbhelper.userHasLevel(command[0], "banned", targetuserdata):
			await self.__replySilence(message, "User [{}](tg://user?id={}) hasn't been banned or they are immun against bans".format(userinput, str(command[0])))
			return False
		
		dbhelper.sendToPostgres(config["updatecomment"], ("unbanned", int(command[0])))
		dbhelper.sendToPostgres(config["updateissuedbyid"], (message.from_user.id, int(command[0])))
		dbhelper.sendToPostgres(config["changelevel"], ("user", int(command[0])))
		
		await self.__performUnban(message, command[0], userdata, targetuserdata)
	
	async def fban(self, client, message, userlevel, userlevel_int, userdata):
		targetuserdata = {}
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			newcommand = [message.reply_to_message.from_user.id]
			for i in command:
				newcommand.append(i)
			command = newcommand
		
		if not len(command) > 1:
			await self.__replySilence(message, "Please provide a reason to ban a user for {} days. Syntax: `/fban <username or id> <reason>`. To have `<username or id>` to be automatically filled out, reply the command to a message from the user in question".format(str(config["daystoban"])))
			return False
		
		command[0] = str(command[0])
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0], targetuserdata = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userinput)
				return False
		if len(targetuserdata) == 0:
			targetuserdata = dbhelper.sendToPostgres(config["getuser"], (command[0],))
		toban = int(command[0])
		del command[0]
		
		if not await self.__canTouchUser(message, toban, userlevel_int, targetuserdata):
			return False
		
		if dbhelper.userHasLevel(toban, "banned", targetuserdata):
			await self.__replySilence(message, "User [{}](tg://user?id={}) already banned".format(userinput, toban))
			return False
		
		toban_level, targetuserdata = dbhelper.getuserlevel(toban, targetuserdata)
		if "immunity" in config and toban_level in config["immunity"] or toban in config["botownerrecord"]:
			await self.__userisimmun(message, userinput, toban, targetuserdata);
			return False
		
		dbhelper.sendToPostgres(config["updatecomment"], (" ".join(command), toban))
		dbhelper.sendToPostgres(config["updateissuedbyid"], (message.from_user.id, toban))
		dbhelper.sendToPostgres(config["changelevel"], ("banned", toban))
		
		await self.noncmd_performBan(message, toban, userdata, targetuserdata)
		
	async def newowner(self, client, message, userlevel, userlevel_int, userdata): # belongs to fosmbot's core
		targetuserdata = {}
		command = message.command
		
		if len(command) == 0:
			await self.__reply(message, "Command to transfer Ownership of 'osmallgroups' federation. Syntax: `/newowner <username or id>`")
			return False
		if not userlevel_int == 0:
			return False
		
		command[0] = str(command[0])
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0], targetuserdata = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__reply(message, "Command to transfer Ownership of 'osmallgroups' federation issued but couldn't execute it:")
				await self.__userNotFound(message, userinput)
				return False
		if len(targetuserdata) == 0:
			targetuserdata = dbhelper.sendToPostgres(config["getuser"], (command[0],))
		
		if not dbhelper.userExists(int(command[0]), targetuserdata):
			await self.__userNotFound(message, userinput)
			return False
		
		dbhelper.sendToPostgres(config["changelevel"], ("user", message.from_user.id))
		dbhelper.sendToPostgres(config["changelevel"], (config["LEVELS"][0], int(command[0])))
		
		changeOwnerInFile(command[0])
		config["botowner"] = int(command[0])
		config["botownerrecord"] = targetuserdata
		for i in targetuserdata:
			targetuserdata = targetuserdata[i]
		for i in userdata:
			userdata = userdata[i]
		await self.__logGroup(message, "Ownership changed from [{}](tg://user?id={}) to [{}](tg://user?id={}). The new ownership will be ensured by a file on the server".format(userdata["displayname"], message.from_user.id, targetuserdata["displayname"], command[0]))
	
	async def addgroup(self, client, message, userlevel, userlevel_int, userdata): # belongs to fosmbot's core
		if message.chat.type == "private" or message.chat.type == "channel":
			return False
		
		out = dbhelper.sendToPostgres(config["getgroup"], (message.chat.id,))
		if len(out) == 0:
			username = self.noncmd_getChatUsername(message)
			dbhelper.sendToPostgres(config["authorizegroup"], (message.chat.id, username))
			config["groupslist"][message.chat.id] = {"id": message.chat.id, "username": username}
			await self.__logGroup(message, "Added group [{}](tg://group?id={}). Now it belongs to the federation 'osmallgroups'".format(message.chat.title, message.chat.id))
	
	async def removegroup(self, client, message, userlevel, userlevel_int, userdata): # belongs to fosmbot's core
		if message.chat.type == "private" or message.chat.type == "channel":
			return False
		
		out = dbhelper.sendToPostgres(config["getgroup"], (message.chat.id,))
		if len(out) > 0:
			dbhelper.sendToPostgres(config["deauthorizegroup"], (message.chat.id,))
			del config["groupslist"][message.chat.id]
			await self.__logGroup(message, "Removed group [{}](tg://group?id={}). It does not longer belong to the federation 'osmallgroups'. Past fbans won't be recovered for that group.".format(message.chat.title, message.chat.id))
	
	async def search(self, client, message, userlevel, userlevel_int, userdata):
		if not message.chat.type == "private":
			return False
		
		command = message.command
		if len(command) == 0:
			await self.__reply(message, "Syntax: `/search <display name>`")
			return False
		
		output = dbhelper.sendToPostgres(config["getusersbydisplayname"], ("%" + " ".join(command) + "%",))
		
		users = []
		for user in output:
			users.append(output[user])
		
		output = ["Search results for users having or containing the name '{}':".format(" ".join(command))]
		for user in users:
			output.append("- [{}](tg://user?id={}) (**level:** {}), @{} (`{}`)".format(user["displayname"], user["id"], user["level"], user["username"], user["id"]))
		
		await self.__reply(message, "\n".join(output))
		
	async def __returnusers(self, message, level):
		if not message.chat.type == "private":
			return False
		output = []
		
		user = True
		cursor = dbhelper.getCursor(config["getusersbylevel"], (level,))
		while user is not None:
			user = dbhelper.getOneRow(cursor)
			if user == None:
				break
			for userid in user:
				output.append("- [{}](tg://user?id={}), @{} (`{}`)\n".format(user[userid]["displayname"], userid, user[userid]["username"], userid))
		dbhelper.closeCursor(cursor)
		
		if len(output) > 0:
			await self.__reply(message, "- ".join(output))
		else:
			await self.__reply(message, "No data available!")
	
	async def owners(self, client, message, userlevel, userlevel_int, userdata):
		await self.__returnusers(message, config["LEVELS"][0])
		
	async def fedadmins(self, client, message, userlevel, userlevel_int, userdata):
		await self.__returnusers(message, "fedadmin")
	
	async def superadmins(self, client, message, userlevel, userlevel_int, userdata):
		await self.__returnusers(message, "superadmin")
	
	async def viewbanreason(self, client, message, userlevel, userlevel_int, userdata):
		if not message.chat.type == "private":
			return False
		
		if dbhelper.userHasLevel(message.from_user.id, "banned", userdata):
			await self.mystat(client, message, userlevel, userlevel_int, userdata)
		else:
			await self.__reply(message, "You are not a banned one!")
	
	async def fbanlist(self, client, message, userlevel, userlevel_int, userdata):
		output = ["id,username,displayname,reason,issued"]
		
		banned = True
		cursor = dbhelper.getCursor(config["getusersbylevel"], ("banned",))
		while banned is not None:
			banned = dbhelper.getOneRow(cursor)
			if banned == None:
				break
			for userid in banned:
				line = []
				row = banned[userid]
				for field in row:
					line.append("\"" + field + "\"")
				output.append(",".join(line))
		dbhelper.closeCursor(cursor)
		
		sfile = open("files/fbanlist.csv", "w")
		sfile.write("\n".join(output))
		sfile.close()
		
		await message.reply_document("files/fbanlist.csv")
	
	async def userstat(self, client, message, userlevel, userlevel_int, userdata, exclude=[]):
		targetuserdata = {}
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			newcommand = [message.reply_to_message.from_user.id]
			for i in command:
				newcommand.append(i)
			command = newcommand
		
		if len(command) == 0:
			await self.__reply(message, "Syntax `/userstat <username or id>` not used.")
			return True
		
		command[0] = str(command[0])
		userinput = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0], targetuserdata = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				await self.__userNotFound(message, userinput)
				return False
		if int(command[0]) in userdata:
			targetuserdata = userdata
		if len(targetuserdata) == 0:
			targetuserdata = dbhelper.sendToPostgres(config["getuser"], (command[0],))
		for i in targetuserdata:
			targetuserdata = targetuserdata[i]
		
		output = ["[{}](tg://user?id={}):".format(targetuserdata["displayname"], targetuserdata["id"])]
		columntrans = {"id": "Telegram id", "username": "Username", "displayname": "Name", "level": "Access level", "comment": "Comment", "issuedbyid": "Comment by", "ts": "Record created at", "pseudoProfile": "Profile won't be saved", "groups": "In groups"}
		for i in targetuserdata:
			label = i
			if i == "groups":
				groupslist = []
				for g in targetuserdata["groups"]:
					groupslist.append("@" + targetuserdata["groups"][g])
				targetuserdata["groups"] = ", ".join(groupslist)
			if label in columntrans:
				label = str(columntrans[i])
			if not i in exclude:
				output.append("**{}**: {}".format(label, targetuserdata[i]))
		
		await self.__reply(message, "\n".join(output))
	
	async def mystat(self, client, message, userlevel, userlevel_int, userdata):
		message.command = [message.from_user.id]
		await self.userstat(client, message, userlevel, userlevel_int, userdata, ["issuedbyid"])
	
	async def mylevel(self, client, message, userlevel, userlevel_int, userdata):
		if not message.chat.type == "private":
			return False
		
		await self.__reply(message, "You are {}".format(userlevel))
	
	async def groupid(self, client, message, userlevel, userlevel_int, userdata): # belongs to fosmbot's core
		if "chat" in dir(message) and message.chat is not None:
			await self.__replySilence(message, "Chat id: `{}`".format(str(message.chat.id)))
	
	async def myid(self, client, message, userlevel, userlevel_int, userdata): # belongs to fosmbot's core
		if not message.chat.type == "private":
			return False
		
		await self.__replySilence(message, "Your id: `{}`".format(str(message.from_user.id)))
		
	async def execCommand(self, command, client, message, userlevel, userlevel_int, userdata): # belongs to fosmbot's core
		if not command[0].startswith("__") or not command[0].startswith("noncmd"):
			func = message.command[0]
			del message.command[0]
			await self.__getattribute__(func)(client, message, userlevel, userlevel_int, userdata)

def main(): # belongs to fosmbot's core
	global config, dbhelper, commander, allcommands, app
	
	config = {}
	logging.basicConfig(format='[fosmbot]: %(asctime)s %(message)s', level=logging.INFO, datefmt="%m/%d/%Y %I:%M:%S %p")
	app = pyrogram.Client("fosm")
	
	logging.info("loading 'fosmbot.yml' configuration...")
	sfile = open("fosmbot.yml", "r")
	config = yaml.safe_load(sfile)
	sfile.close()
	
	logging.info("loading available commands...")
	for level in config["LEVELS"]:
		for command in config["LEVEL_" + level.upper()]:
			allcommands.append(command)
	logging.info("Available commands: '{}'".format(", ".join(allcommands)))
	
	if not "dbconnstr" in config:
		logging.info("generating 'dbconnstr'...")
		config["dbconnstr"] = "host={} port={} user={} password={} dbname={}".format(config["DATABASE_HOST"], config["DATABASE_PORT"], config["DATABASE_USER"], config["DATABASE_USER_PASSWD"], config["DATABASE_DBNAME"])
	else:
		logging.info("using predefined 'dbconnstr' instead of generating one...")
	
	logging.info("ensuring owner...")
	config["botowner"] = int(readOwner())
	if not "immunity" in config:
		config["immunity"] = config["LEVELS"][0]
	
	logging.info("perform automatic set up...")
	dbsetup.setupDB(config)
	logging.info("automatic set up performed!")
	
	logging.info("connecting to database...")
	dbhelper = database.helper(config)
	
	commander = commandControl()
	
	logging.info("downloading list of groups...")
	config["groupslist"] = dbhelper.sendToPostgres(config["getgroups"])

if __name__ == "__main__":
	main()

def addUserToDatabase(chat, user): # belongs to fosmbot's core
	if user is None:
		return False
	displayname = commander.noncmd_getDisplayname(user)
	canReturn = False
	out = {}
	if user.username is None:
		user.username = str(user.id)
	
	if not user.is_self and not user.is_deleted and not user.is_bot and not user.is_support:
		userexists, out = dbhelper.userExists(user.id)
		if not userexists and not chat == "private" and not chat == "channel" or not userexists and user.id == config["botowner"]:
			dbhelper.sendToPostgres(config["adduser"], (user.id, user.username.lower(), displayname, commander.createTimestamp()))
		elif userexists:
			dbhelper.sendToPostgres(config["updatedisplayname"], (displayname, user.id))
			canReturn = True
	
	if not canReturn:
		out = {user.id: {"id": user.id, "username": str(user.username), "displayname": displayname, "level": "user", "comment": "", "issuedbyid": None, "groups": {}, "ts": commander.createTimestamp()}}
	if chat == "private" and not userexists or chat == "channel" and not userexists:
		out[user.id]["pseudoProfile"] = True
	
	if user.id == config["botowner"]:
		config["botownerrecord"] = out
		if not dbhelper.userHasLevel(config["botowner"], config["LEVELS"][0], out):
			dbhelper.sendToPostgres(config["changelevel"], (config["LEVELS"][0], int(config["botowner"])))
			if len(out) > 1:
				out[user.id]["level"] = config["LEVELS"][0]
			logging.info("Ensuring Ownership of user '{}' ({}) as {}".format(displayname, user.id, config["LEVELS"][0]))
	
	return out

def addToGroup(message, user):
	username = commander.noncmd_getChatUsername(message)
	dbhelper.sendToPostgres(config["addgrouptouser"], ("{\"" + str(message.chat.id) + "\": \"" + username + "\"}", user["id"]))
	user["groups"][message.chat.id] = username

@app.on_message(pyrogram.Filters.command(allcommands))
async def precommandprocessing(client, message): # belongs to fosmbot's core
	user = addUserToDatabase(message.chat.type, message.from_user)
	command = message.command
	if command is str:
		command = [command]
		message.command = [message.command]
	
	userlevel, user = dbhelper.getuserlevel(message.from_user.id, user)
	if userlevel.startswith("error"):
		userlevel = config["LEVELS"][len(config["LEVELS"])-1]
	
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
						await commander.execCommand(command, client, message, userlevel, rightlevel, user)
						return True
					else:
						await message.reply("Command not available to you. It is either just executable in a specified group or just available for a specified user.", parse_mode="md")
						return False
			
			await commander.execCommand(command, client, message, userlevel, rightlevel, user)
			return True
	
	out = ["Insufficient rights. You are: {}".format(userlevel)]
	if "pseudoProfile" in user:
		out.append("This Bot does not have any data about you stored. It will generate a pseudo profile everytime you chat with it because it is not necessary to create a profile for you yet!")
	await message.reply("\n".join(out), disable_web_page_preview=True, parse_mode="md")

@app.on_message(pyrogram.Filters.new_chat_members)
async def userjoins(client, message): # belongs to fosmbot's core
	newmembers = message.new_chat_members
	if type(newmembers) is not list:
		newmembers = [newmembers]
	
	for member in newmembers:
		user = addUserToDatabase(message.chat.type, member)
		if user is None:
			continue
		
		if message.chat.type == "channel" or not dbhelper.isAuthorizedGroup(message.chat.id, config["groupslist"]):
			continue
		
		for i in user:
			user = user[i]
		
		if user["level"] == "banned" and not message.chat.type == "channel":
			try:
				await app.kick_chat_member(int(message.chat.id), toban, int(time.time() + 60*60*24*int(config["daystoban"]))) # kick chat member and automatically unban after ... days
			except:
				app.send_message(int(group), "User [{}](tg://user?id={}) has been banned from federation 'osmallgroups'. However that user couldn't be banned from this group. **Do I have the right to ban them here?**".format(user["displayname"], user["id"]))
			return False
		addToGroup(message, user)

@app.on_message(pyrogram.Filters.left_chat_member)
async def userleave(client, message):
	user = dbhelper.sendToPostgres(config["getuser"], message.left_chat_member.id)
	if len(user) == 0:
		return False
	for i in user:
		user = user[i]
	
	if message.chat.type == "channel":
		return False
	
	for i in user:
		user = user[i]
	
	if len(groups) == 0 or not message.chat.id in user["groups"]:
		return False
	
	dbhelper.sendToPostgres(config["removegroupfromuser"], (str(message.chat.id), user["id"]))

@app.on_message()
async def messageFromUser(client, message): # belongs to fosmbot's core
	user = addUserToDatabase(message.chat.type, message.from_user)
	if user is None:
		return False
	
	for i in user:
		user = user[i]
	
	if not message.chat.id in user["groups"] and not message.chat.type == "private" and not message.chat.type == "channel":
		addToGroup(message, user)
	
	if "forward_from" in dir(message) and message.forward_from is not None:
		if not "pseudoProfile" in user:
			message.chat.type = "group"
		addUserToDatabase(message.chat.type, message.forward_from)
	
	if message.chat.type == "channel" or message.chat.type == "private" or not dbhelper.isAuthorizedGroup(message.chat.id, config["groupslist"]):
		return False

if __name__ == "__main__":
	logging.info("Scheduling database cleanup...")
	clean = dbcleanup()
	clean.start()
	threads.append(clean)
	
	logging.info("starting fosmbot...")
	app.run()
	
	logging.info("Bot stopped! Stopping database cleanup...")
	exitFlag = 1
	for i in threads:
		i.join()
	
	logging.info("Closing connection to database...")
	dbhelper.tearDown()
	
	logging.info("All operations stopped! Bye, see you soon :)")
	
