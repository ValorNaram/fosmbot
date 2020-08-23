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

def addUser(userid, username, displayname):
	dbhelper.sendToPostgres(config["adduser"], (str(userid), str(username).lower(), displayname, commander.createTimestamp()))

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
		
		logging.info("Database clean up performed. Repeat in '{0[DATABASE_CLEANUP_HOUR]:.0f}' hour(s)".format(config))
	
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
	def telegramidorusername(self, userid):
		userid = str(userid).replace("@", "")
		try:
			userid = str(int(userid))
			return userid # is telegram id
		except:
			return "@" + userid # is telegram username
	
	def noncmd_createtempuserrecord(self, userid, username, displayname):
		userid = str(userid)
		return {"id": userid, "username": str(username.lower().replace("@", "")), "displayname": displayname, "level": "user", "level_int": config["LEVELS"].index("user"), "comment": "", "issuedbyid": None, "groups": {}, "ts": self.createTimestamp()}
	async def __canTouchUser(self, message, issuer_level_int, targetuser):
		"""
		Checks, if the user can touch the user in question
		
		Parameters:
		  - `message` _object_: message object as returned by Pyrogram (https://docs.pyrogram.org/api/types/Message?highlight=message).
		  - `userInQuestion` _string_: the telegram id of the user which the issuer wants to touch.
		  - `issuer_level` _int_: the level of the user which executes this command (issuer).
		  - `targetuser` _dict_: the record the bot has about the user which the issuer wants to touch.
		Checks, if the user which executes the command ('issuer_level') has the right to touch the user (to change the record of them) (`userInQuestion`, `targetuser`)
		
		Returns:
		  Boolean indicating if the issuer can touch the user in question or not
		
		Example:
		You have the telegram id `5678` and level `1`
		The user from which you want to change the record has the telegram id `1234` and the level `2`
		    
		    self.__canTouchUser(message, 1234, , {1234: {"id": 1234, "username": "foobar", "displayname": "Foo Bar", "level": "fedadmin", "comment": "", "issuedbyid": None, "groups": {}, "ts": "2020-12-01 00:00:00"}})
		
		Returns:
		  True
		
		Answer:
		  It returns `True` which means that the issuer can touch the user (`userInQuestion`, `targetuser`)
		"""
		userInQuestion_level_int = config["LEVELS"].index(targetuser["level"])
		if userInQuestion_level_int > issuer_level_int: # if true, then the user (issuer_level) who issued that command has rights to touch user in question (userInQuestion)
			return True
		await self.__replySilence(message, "You don't have the necessary rights to touch the user!")
		return False
	
	def noncmd_createAnonymousRecord(self, userid):
		"""
		Creates an anoymous record for `userid` _int_ (telegram id) in cases the issuer wants to perform an operation on an user the bot does not know.
		
		It returns `targetuser` _dict_:
		
		```python3
		{"id": 1234, "username": "foobar", "displayname": "Foo Bar", "level": "fedadmin", "comment": "", "issuedbyid": None, "groups": {}, "ts": "2020-12-01 00:00:00"}}
		```
			
		"""
		displayname = "Anonymous User " + str(userid)

		tscreated = commander.createTimestamp()
		addUser(userid, userid, displayname)
		
		return self.noncmd_createtempuserrecord(userid, userid, displayname)
	
	async def noncmd_userHasLocalChatPermission(self, message, pg_user, permission, obeyChatPermission=True):
		"""
		Checks, if the issuer is an admin in a group which the specified right `permission` (see 'Parameters' at https://docs.pyrogram.org/api/types/ChatMember) applies to.
		
		Parameters:
		  - `message` _object_: message object as returned by Pyrogram (https://docs.pyrogram.org/api/types/Message?highlight=message).
		  - `user` _object_: a user object as returned by Pyrogram (https://docs.pyrogram.org/api/types/User#pyrogram.User)
		  - `permission` _string_: permission to check, if the user has it. See also 'Parameters' at https://docs.pyrogram.org/api/types/ChatMember
		  - `obeyChatPermission` __bool__: If true (default), then check the permissions of a group which are valid for all and do not require a higher user level. If False, then don't check that case.
		
		Example:
		
		
		`self.noncmd_userHasLocalChatPermission(message, user, "can_change_info")`
		`commander.noncmd_userHasLocalChatPermission(message, user, "can_change_info")`
		
		"""
		if obeyChatPermission:
			if "chat" in dir(message) and "permissions" in dir(message.chat):
				if permission in dir(message.chat.permissions):
					return True
		
		try:
			member = await message.chat.get_member(pg_user.id)
		except:
			self.__reply(message, "Couldn't get user [{0[displayname]}](tg://user?id={0[id]})".format(pg_user))
			return False
		
		if member is not None:
			if permission in dir(member):
				return True
		
		return False
	
	def noncmd_getChatUsername(self, message):
		username = ""
		if "username" in dir(message.chat) and message.chat.username is not None:
			username = message.chat.username
		else:
			username = str(message.chat.id)
		
		return username.lower()
	
	async def noncmd_performBan(self, message, issuer, targetuser): # belongs to fosmbot's core
		targetuser["id"] = self.telegramidorusername(targetuser["id"])
		targetuser["username"] = self.telegramidorusername(targetuser["username"])
		
		for group in targetuser["groups"]:
			if not int(group) in config["groupslist"]:
				continue
			try:
				await app.kick_chat_member(int(group), targetuser["id"], int(time.time() + 60*60*24*int(config["daystoban"]))) # kick chat member and automatically unban after ... days
			except (pyrogram.errors.ChatAdminRequired):
				await app.send_message(int(group), "[{0[displayname]}](tg://user?id={0[id]}) **banned** user [{1[displayname]}](tg://user?id={1[id]}) from federation 'osmallgroups'. However that user couldn't be banned from this group. **Do I have the right to ban them here?**".format(issuer, targetuser))
			except (pyrogram.errors.ChatWritePermission, pyrogram.errors.ChannelPrivate):
				commander.removegroup(None, message, None, None, None)
			except:
				pass
			
		target = self.telegramidorusername(targetuser["id"])
		await self.__logGroup(message, "[{0[displayname]}](tg://user?id={0[id]}) **banned** user [{1[displayname]}](tg://user?id={1[id]}) ( {2} ) from federation 'osmallgroups' for 365 days.\n**Reason:** `{1[comment]}`".format(issuer, targetuser, target))
	
	async def __performUnban(self, message, issuer, targetuser):
		targetuser["id"] = self.telegramidorusername(targetuser["id"])
		targetuser["username"] = self.telegramidorusername(targetuser["username"])
		
		for group in targetuser["groups"]:
			if not int(group) in config["groupslist"]:
				continue
			try:
				app.unban_chat_member(int(group), targetuser["id"])
			except (pyrogram.errors.ChatAdminRequired):
				await app.send_message(int(group), "[{0[displayname]}](tg://user?id={0[id]}) **unbanned** user [{1[displayname]}](tg://user?id={1[id]}) from federation 'osmallgroups'. However that user couldn't be unbanned from this group. **Do I have the right to unban them here?**".format(issuer, targetuser))
			except (pyrogram.errors.ChatWritePermission, pyrogram.errors.ChannelPrivate):
				commander.removegroup(None, message, None, None, None)
			except:
				pass
		
		target = self.telegramidorusername(targetuser["id"])
		await self.__logGroup(message, "[{0[displayname]}](tg://user?id={0[id]}) **unbanned** user [{1[displayname]}](tg://user?id={1[id]}) ( {2} ) from federation 'osmallgroups'.".format(issuer, targetuser, target))
	
	async def __ownerCannotDo(self, message):
		await message.reply("An owner cannot do this", disable_web_page_preview=True, parse_mode="md")
	
	async def __userNotFound(self, message, user):
		await message.reply("User '{}' does not exist in the database".format(user), disable_web_page_preview=True, disable_notification=True, parse_mode="md")
		
	async def __reply(self, message, text): # belongs to fosmbot's core
		start = 0
		stop = 4096
		while len(text) > start:
			await message.reply(text[start:stop], disable_web_page_preview=True, parse_mode="md")
			stop += 4096
			start += 4096
	
	async def __replySilence(self, message, text): # belongs to fosmbot's core
		start = 0
		stop = 4096
		while len(text) > start:
			await message.reply(text, disable_web_page_preview=True, disable_notification=True, parse_mode="md")
			stop += 4096
			start += 4096
	
	async def __logGroup(self, message, text): # belongs to fosmbot's core
		if "logchannel" in config:
			await app.send_message(int(config["logchannel"]), text, disable_web_page_preview=True, parse_mode="md")
		await self.__replySilence(message, text)
	
	async def __userisimmun(self, targetuser):
		await self.__replySilence(message, "The user [{0[displayname]}](tg://user?id={0[id]}) is immun against this!".format(targetuser))
	
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
	
	async def userid(self, client, message, issuer):
		out = []
		forwarded = False
		message = message.reply_to_message
		
		if "forward_from" in dir(message) and message.forward_from is not None:
			out.append("Forwarded from [{}](tg://user?id={}) (`{}`)".format(self.noncmd_getDisplayname(message.forward_from), message.forward_from.id, message.forward_from.id))
			forwarded = True
		
		if forwarded:
			out.append("and sent by")
		else:
			out.append("Message sent by")
		
		out.append("[{}](tg://user?id={}) (`{}`)".format(self.noncmd_getDisplayname(message.from_user), message.from_user.id, message.from_user.id))
		
		await self.__replySilence(message, " ".join(out))
	
	async def viewgroups(self, client, message, issuer):
		if not message.chat.type == "private":
			return False
		
		groups = config["groupslist"]
		out = []
		
		for i in groups:
			group = groups[i]
			out.append("- @{} (`{}`)".format(group["username"], i))
		out.append("\n**{} groups** participate in the federation".format(len(groups)))
		
		await self.__reply(message, "\n".join(out))
		
	async def removerecord(self, client, message, issuer):
		if not message.chat.type == "private":
			return False
		
		targetuser = {}
		command = message.command
		
		targetuserInQuestion = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id (if applicable)
			targetuser = dbhelper.getResult(config["getuserbyusername"], (command[0].replace("@", ""),)).get()
			#command[0], targetuser = dbhelper.resolveUsername(command[0])
			if len(targetuser) == 0:
				await self.__userNotFound(message, targetuserInQuestion)
				return False
			targetuserInQuestion = command[0].replace("@", "")
		if len(targetuser) == 0:
			targetuser = dbhelper.getResult(config["getuser"], (command[0],)).get()
		
		targetuserInQuestion_id = command[0]
		del command[0]
		
		dbhelper.sendToPostgres(config["removeuser"], (targetuserInQuestion_id,))
		await self.__reply(message, "**Removed user** [{0[displayname]}](tg://user?id={0[id]}) from the known users list.".format(targetuser))
	
	async def addrecord(self, client, message, issuer):
		if not message.chat.type == "private":
			return False
		
		command = message.command
		
		if len(command) == 2:
			addUser(command[1], command[0], "Anonymous User {}".format(command[0]))
			await self.__replySilence(message, "Record for user `{}` created".format(command[0]))
		elif len(command) == 1:
			addUser(command[0], command[0], "Anonymous User {}".format(command[0]))
			await self.__replySilence(message, "Record for user `{}` created".format(command[0]))
	
	async def help(self, client, message, issuer):
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
	
	async def start(self, client, message, issuer):
		await self.help(client, message, issuer)
	
	async def mydata(self, client, message, issuer):
		if not message.chat.type == "private":
			await self.__replySilence("Please request access to insights of the data we have about you by issueing that command in private chat with me.")
			return False
		
		targetuser = dbhelper.getResult(config["getuser"], (str(message.from_user.id),)).get()
		if not len(targetuser) == 0:
			message.command = [str(message.from_user.id)]
			await self.__reply(message, "The data we have about you (nothing critical):")
			await self.userstat(client, message, user, ["issuedbyid"])
			await self.__reply(message, "One column belonging to you has been stripped off because it contains the telegram id by the user who wrote that comment about you or it has the value `NULL` meaning that no one wrote a comment about you yet. In this case the 'comment' field does not contain anything.")
		else:
			await self.__userNotFound(message, self.noncmd_getDisplayname(message.from_user))
	
	async def privacypolicy(self, client, message, issuer):
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
	
	async def changecomment(self, client, message, issuer):
		targetuser = {}
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			newcommand = [str(message.reply_to_message.from_user.id)]
			for i in command:
				newcommand.append(i)
			command = newcommand
		
		if not len(command) > 1:
			await self.__replySilence(message, "Syntax: `/changecomment <username or id> <comment>`. To have `<username or id>` to be automatically filled out, reply the command to a message from the user in question")
			return False
		
		targetuserInQuestion = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id (if applicable)
			targetuser = dbhelper.getResult(config["getuserbyusername"], (command[0].replace("@", ""),)).get()
			#command[0], targetuser = dbhelper.resolveUsername(command[0])
			if len(targetuser) == 0:
				await self.__userNotFound(message, targetuserInQuestion)
				return False
			targetuserInQuestion = command[0].replace("@", "")
		if len(targetuser) == 0:
			targetuser = dbhelper.getResult(config["getuser"], (command[0],)).get() #dbhelper.sendToPostgres(config["getuser"], (command[0],))
		targetuserInQuestion_id = command[0]
		
		del command[0]
		
		if not await self.__canTouchUser(message, issuer["level_int"], targetuser):# or targetuserInQuestion_id in config["botownerrecord"]:
			return False
		
		dbhelper.sendToPostgres(config["updatecomment"], (" ".join(command), targetuserInQuestion_id))
		await self.__reply(message, "Comment about [{0[displayname]}](tg://user?id={0[id]}) changed".format(targetuser))
	
	async def testme(self, client, message, issuer):
		await self.__replySilence(message, "Tested me!")
	
	async def changelevel(self, client, message, issuer): # belongs to fosmbot's core
		targetuser = {}
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			newcommand = [str(message.reply_to_message.from_user.id)]
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
		
		if not levelToPromoteTo_int > issuer["level_int"]: # if true, then the user who issued that command has no rights to promote <user> to <level>
			self.__replySilence(message, "You cannot use that command to promote a user to a higher level or even to your level")
			return False # user does not have the right to promote <user> to <level>
		
		command[0] = str(command[0])
		userToPromote = command[0]
		if command[0].startswith("@"): # if true, then resolve username to telegram id (if applicable)
			targetuser = dbhelper.getResult(config["getuserbyusername"], (command[0].replace("@", ""),)).get()
			#command[0], targetuser = dbhelper.resolveUsername(command[0])
			if len(targetuser) == 0:
				await self.__userNotFound(message, userToPromote)
				return False
			command[0] = command[0].replace("@", "")
		if len(targetuser) == 0:
			targetuser = dbhelper.getResult(config["getuser"], (command[0],)).get() #dbhelper.sendToPostgres(config["getuser"], (command[0],))
		
		if not await self.__canTouchUser(message, issuer["level_int"], targetuser):# or command[0] in config["botownerrecord"]:
			self.__replySilence(message, "You cannot use that command to promote a user with a higher level or even equal to yours")
			return False
		
		dbhelper.sendToPostgres(config["changelevel"], (command[1], command[0]))
		await self.__logGroup(message, "User [{0[displayname]}](tg://user?id={0[id]}) is now a `{1}` one as requested by [{2[displayname]}](tg://user?id={2[id]}) with level `{2[level]}`".format(targetuser, command[1], issuer))
	
	async def demoteme(self, client, message, issuer): # belongs to fosmbot's core
		if not message.chat.type == "private":
			return False
		
		if issuer["level_int"] == 0:
			await self.__ownerCannotDo(message)
		else:
			dbhelper.sendToPostgres(config["changelevel"], ("user", str(message.from_user.id)))
			await self.__reply(message, "You are now powerless! Thank You for your effort to cut down spammers!")
	
	async def funban(self, client, message, issuer):
		targetuser = {}
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			newcommand = [str(message.reply_to_message.from_user.id)]
			for i in command:
				newcommand.append(i)
			command = newcommand
		
		if len(command) == 0:
			await self.__reply(message, "Syntax: `/funban <username or id>`. To have `<username or id>` to be automatically filled out, reply the command to a message from the user in question")
			return False
		
		userinput = command[0].lower()
		command[0] = userinput.replace("@", "")
		if userinput.startswith("@"): # if true, then resolve username to telegram id (if applicable)
			targetuser = dbhelper.getResult(config["getuserbyusername"], (command[0],)).get()
			if len(targetuser) == 0:
				await self.__userNotFound(message, userinput)
				return False
		if len(targetuser) == 0:
			targetuser = dbhelper.getResult(config["getuser"], (command[0],)).get()
		
		if not targetuser["level"] == "banned":
			await self.__replySilence(message, "User [{}](tg://user?id={}) hasn't been banned or they are immun against bans".format(userinput, command[0]))
			return False
		
		dbhelper.sendToPostgres(config["updatecomment"], ("unbanned", command[0]))
		dbhelper.sendToPostgres(config["updateissuedbyid"], (str(message.from_user.id), command[0]))
		dbhelper.sendToPostgres(config["changelevel"], ("user", command[0]))
		
		await self.__performUnban(message, issuer, targetuser)
	
	async def fban(self, client, message, issuer):
		targetuser = {}
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			newcommand = [str(message.reply_to_message.from_user.id)]
			for i in command:
				newcommand.append(i)
			command = newcommand
		
		if len(command) == 0:
			await self.__replySilence(message, "Syntax: `/fban <username or id> <reason (optional)>`. To have `<username or id>` to be automatically filled out, reply the command to a message from the user in question")
			return False
		if not len(command) > 1:
			#await self.__replySilence(message, "Please provide a reason to ban a user for {0[daystoban]} days. Syntax: `/fban <username or id> <reason>`. To have `<username or id>` to be automatically filled out, reply the command to a message from the user in question".format(config))
			#return False
			command.append("not acting like a person with interest into OpenStreetMap or GIS or even into the community of OpenStreetMap itself")
		
		userinput = command[0].lower()
		command[0] = userinput.replace("@", "")
		if userinput.startswith("@"): # if true, then resolve username to telegram id (if applicable)
			targetuser = dbhelper.getResult(config["getuserbyusername"], (command[0],)).get()
			if len(targetuser) == 0:
				addUser(command[0], command[0], "Anonymous User {}".format(userinput))
				targetuser = self.noncmd_createtempuserrecord(command[0], command[0], "Anonymous User {}".format(userinput))
		
		if len(targetuser) == 0:
			targetuser = dbhelper.getResult(config["getuser"], (command[0],)).get()#dbhelper.sendToPostgres(config["getuser"], (command[0],))
		toban = command[0]
		del command[0]
		
		if len(targetuser) == 0:
			targetuser = self.noncmd_createAnonymousRecord(toban)
		
		if not await self.__canTouchUser(message, issuer["level_int"], targetuser):
			return False
		
		if targetuser["level"] == "banned":
			message.command = [toban, " ".join(command)]
			
			await self.changecomment(client, message, issuer)
			return False
		
		toban_level = targetuser["level"]
		if "immunity" in config and toban_level in config["immunity"]:# or toban in config["botownerrecord"]: # bug here but another security system prevents from unattended owner overwrite so it is not dramatic to deactivate this here
			await self.__userisimmun(targetuser);
			return False
		
		dbhelper.sendToPostgres(config["updatecomment"], (" ".join(command), toban))
		dbhelper.sendToPostgres(config["updateissuedbyid"], (str(message.from_user.id), toban))
		dbhelper.sendToPostgres(config["changelevel"], ("banned", toban))
		
		targetuser["comment"] = " ".join(command)
		targetuser["issuedbyid"] = str(message.from_user.id)
		
		await self.noncmd_performBan(message, issuer, targetuser)
		
	async def newowner(self, client, message, issuer): # belongs to fosmbot's core
		targetuser = {}
		command = message.command
		
		if len(command) == 0:
			await self.__reply(message, "Command to transfer Ownership of 'osmallgroups' federation. Syntax: `/newowner <username or id>`")
			return False
		if not issuer["level_int"] == 0:
			return False
		
		userinput = command[0].lower()
		command[0] = userinput.replace("@", "")
		if userinput.startswith("@"): # if true, then resolve username to telegram id (if applicable)
			targetuser = dbhelper.getResult(config["getuserbyusername"], (command[0],)).get()
			if len(targetuser) == 0:
				await self.__reply(message, "Command to transfer Ownership of 'osmallgroups' federation issued but couldn't execute it:")
				await self.__userNotFound(message, userinput)
				return False
			
			try:
				int(command[0])
			except:
				await self.__reply(message, "Command to transfer Ownership of 'osmallgroups' federation issued but couldn't execute it: Couldn't convert username to telegram id")
				return False
		command[0] = int(command[0])
		
		if len(targetuser) == 0:
			targetuser = dbhelper.getResult(config["getuser"], (command[0],)).get()#dbhelper.sendToPostgres(config["getuser"], (command[0],))
		
		if not len(targetuser) == 0:
			await self.__userNotFound(message, userinput)
			return False
		
		dbhelper.sendToPostgres(config["changelevel"], ("user", str(message.from_user.id)))
		dbhelper.sendToPostgres(config["changelevel"], (config["LEVELS"][0], command[0]))
		
		changeOwnerInFile(command[0])
		config["botowner"] = command[0]
		config["botownerrecord"] = targetuser
		
		await self.__logGroup(message, "Ownership changed from [{0[displayname]}](tg://user?id={0[id]}) to [{0[displayname]}](tg://user?id={0[id]}). The new ownership will be ensured by a file on the server".format(issuer, targetuser))
	
	async def addgroup(self, client, message, issuer): # belongs to fosmbot's core
		if message.chat.type == "private" or message.chat.type == "channel":
			return False
		
		out = dbhelper.sendToPostgres(config["getgroup"], (message.chat.id,))
		if len(out) == 0:
			username = self.noncmd_getChatUsername(message)
			dbhelper.sendToPostgres(config["authorizegroup"], (message.chat.id, username))
			config["groupslist"][message.chat.id] = {"id": message.chat.id, "username": username}
			await self.__logGroup(message, "Added group [{}](tg://group?id={}). Now it belongs to the federation 'osmallgroups'".format(message.chat.title, message.chat.id))
	
	async def removegroup(self, client, message, issuer): # belongs to fosmbot's core
		if message.chat.type == "private" or message.chat.type == "channel":
			return False
		
		out = dbhelper.sendToPostgres(config["getgroup"], (message.chat.id,))
		if len(out) > 0:
			dbhelper.sendToPostgres(config["deauthorizegroup"], (message.chat.id,))
			del config["groupslist"][message.chat.id]
			await self.__logGroup(message, "Removed group [{}](tg://group?id={}). It does not longer belong to the federation 'osmallgroups'. Past fbans won't be recovered for that group.".format(message.chat.title, message.chat.id))
	
	async def search(self, client, message, issuer):
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
		
		output = ["Case-Insensitive search results for users having or containing the name '{}':".format(" ".join(command))]
		for user in users:
			user["id"] = self.telegramidorusername(user["id"])
			user["username"] = self.telegramidorusername(user["username"])
			output.append("- [{0[displayname]}](tg://user?id={0[id]}) (**level:** {0[level]}), {0[username]} (`{0[id]}`)".format(user))
		
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
				user[userid]["id"] = self.telegramidorusername(user[userid]["id"])
				user[userid]["username"] = self.telegramidorusername(user[userid]["username"])
				output.append("- [{0[displayname]}](tg://user?id={0[id]}), {0[username]} (`{0[id]}`)".format(user[userid]))
		dbhelper.closeCursor(cursor)
		
		if len(output) > 0:
			await self.__reply(message, "\n".join(output))
		else:
			await self.__reply(message, "No data available!")
	
	async def owners(self, client, message, issuer):
		await self.__returnusers(message, config["LEVELS"][0])
		
	async def fedadmins(self, client, message, issuer):
		await self.__returnusers(message, "fedadmin")
	
	async def superadmins(self, client, message, issuer):
		await self.__returnusers(message, "superadmin")
	
	async def viewbanreason(self, client, message, issuer):
		if not message.chat.type == "private":
			return False
		
		if issuer["level"] == "banned":
			await self.mystat(client, message, issuer)
		else:
			await self.__reply(message, "You are not a banned one!")
	
	async def fbanlist(self, client, message, issuer):
		output = ["id,username,displayname,reason,issued by,kicked from groups"]
		fields = ["id", "username", "displayname", "comment", "issuedbyid", "groups"]
		
		banned = True
		cursor = dbhelper.getCursor(config["getusersbylevel"], ("banned",))
		while banned is not None:
			banned = dbhelper.getOneRow(cursor)
			if banned == None:
				break
			for userid in banned:
				line = []
				row = banned[userid]
				for field in fields:
					if field == "groups":
						dic = []
						for g in row[field]:
							dic.append("@" + row[field][g])
						line.append("\"{}\"".format(" ".join(dic)))
					else:
						line.append("\"{}\"".format(row[field]))
				output.append(",".join(line))
		dbhelper.closeCursor(cursor)
		
		sfile = open("files/fbanlist.csv", "w")
		sfile.write("\n".join(output))
		sfile.close()
		
		await message.reply_document("files/fbanlist.csv")
	
	async def userstat(self, client, message, issuer, exclude=[]):
		targetuser = {}
		command = message.command
		
		if "reply_to_message" in dir(message) and message.reply_to_message is not None:
			newcommand = [str(message.reply_to_message.from_user.id)]
			for i in command:
				newcommand.append(i)
			command = newcommand
		
		if len(command) == 0:
			await self.__reply(message, "Syntax `/userstat <username or id>` not used.")
			return True
		
		userinput = command[0].lower()
		command[0] = userinput.replace("@", "")
		if userinput.startswith("@"): # if true, then resolve username to telegram id (if applicable)
			targetuser = dbhelper.getResult(config["getuserbyusername"], (command[0],)).get()
			#command[0], targetuser = dbhelper.resolveUsername(command[0])
			if len(targetuser) == 0:
				await self.__userNotFound(message, userinput)
				return False
		if command[0] in issuer["id"]:
			targetuser = issuer
		if len(targetuser) == 0:
			targetuser = dbhelper.getResult(config["getuser"], (command[0],)).get()#dbhelper.sendToPostgres(config["getuser"], (command[0],))
			if len(targetuser) == 0:
				await self.__userNotFound(message, userinput)
				return False
		
		output = ["[{0[displayname]}](tg://user?id={0[id]}):".format(targetuser)]
		columntrans = {"id": "Telegram id", "username": "Username", "displayname": "Name", "level": "Access level", "comment": "Comment", "issuedbyid": "Comment by", "ts": "Record created at", "pseudoProfile": "Profile won't be saved", "groups": "In groups"}
		for i in targetuser:
			targetuser["id"] = self.telegramidorusername(targetuser["id"])
			targetuser["username"] = self.telegramidorusername(targetuser["username"])
			label = i
			if i == "groups":
				groupslist = []
				for g in targetuser["groups"]:
					groupslist.append("@" + targetuser["groups"][g])
				targetuser["groups"] = ", ".join(groupslist)
			if label in columntrans:
				label = str(columntrans[i])
			if not i in exclude:
				output.append("**{}**: {}".format(label, targetuser[i]))
		
		await self.__reply(message, "\n".join(output))
	
	async def mystat(self, client, message, issuer):
		message.command = [str(message.from_user.id)]
		await self.userstat(client, message, issuer, ["issuedbyid"])
	
	async def mylevel(self, client, message, issuer):
		if not message.chat.type == "private":
			return False
		
		await self.__reply(message, "You are {}".format(issuer["level"]))
	
	async def groupid(self, client, message, issuer): # belongs to fosmbot's core
		if "chat" in dir(message) and message.chat is not None:
			await self.__replySilence(message, "Chat id: `{}`".format(message.chat.id))
	
	async def myid(self, client, message, issuer): # belongs to fosmbot's core
		if not message.chat.type == "private":
			return False
		
		await self.__replySilence(message, "Your id: `{}`".format(message.from_user.id))
	
	async def groupauthorized(self, client, message, issuer):  # belongs to fosmbot's core
		if message.chat.id in config["groupslist"]:
			await self.__replySilence(message, "This group is an authorized one!")
		else:
			await self.__replySilence(message, "This group is **not** an authorized one!")
	
	async def execCommand(self, command, client, message, issuer): # belongs to fosmbot's core
		if "entities" in dir(message) and message.entities is not None:
			for entity in message.entities:
				if entity.type == "text_mention": # support for 'text_mention's
					text = " ".join(message.command)
					text = text.replace(self.noncmd_getDisplayname(entity.user), "")
					message.command = text.split(" ")
					message.command[1] = int(entity.user.id)
		
		if not command[0].startswith("__") or not command[0].startswith("noncmd"):
			func = message.command[0]
			del message.command[0]
			await self.__getattribute__(func)(client, message, issuer)

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
		config["dbconnstr"] = "host={0[DATABASE_HOST]} port={0[DATABASE_PORT]} user={0[DATABASE_USER]} password={0[DATABASE_USER_PASSWD]} dbname={0[DATABASE_DBNAME]}".format(config)
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
	group = True
	config["groupslist"] = {}
	cur = dbhelper.getCursor(config["getgroups"])
	while group is not None:
		group = dbhelper.getOneRow(cur)
		if group is not None:
			for groupid in group:
				config["groupslist"][groupid] = group[groupid]

if __name__ == "__main__":
	main()

def addUserToDatabase(chat, user): # belongs to fosmbot's core
	if user is None:
		return {}
	displayname = commander.noncmd_getDisplayname(user)
	canReturn = False
	userexists = False
	out = dbhelper.getResult(config["getuser"], (str(user.id),), limit=1).get()
	if len(out) > 0:
		userexists = True
		
	if user.username is None:
		user.username = str(user.id)
	
	if user.is_self or user.is_deleted or user.is_bot or user.is_support:
		return {}
	
	if not userexists:
		output = dbhelper.getResult(config["getuserbyusername"], (user.username.lower(),), limit=1).get()
		if len(output) > 0:
			out = output
			userexists = True
			dbhelper.sendToPostgres(config["updateuserid"], (str(user.id), user.username.lower()))
	
	if not userexists and not chat == "private" and not chat == "channel" or not userexists and user.id == config["botowner"]:
		addUser(user.id, user.username, displayname)
	elif userexists:
		dbhelper.sendToPostgres(config["updateuserinfo"], (user.username.lower(), displayname, str(user.id)))
		canReturn = True
	
	if not canReturn:
		out = commander.noncmd_createtempuserrecord(str(user.id), user.username, displayname)
	
	if user.id == config["botowner"]:
		config["botownerrecord"] = out
		out["level_int"] = 0
		if not out["level"] == config["LEVELS"][0]:
			dbhelper.sendToPostgres(config["changelevel"], (config["LEVELS"][0], str(config["botowner"])))
			if len(out) > 1:
				out["level"] = config["LEVELS"][0]
			logging.info("Ensuring Ownership of user '{}' ({}) as {}".format(displayname, user.id, config["LEVELS"][0]))
	else:
		out["level_int"] = config["LEVELS"].index(out["level"])
	if chat == "private" and not userexists or chat == "channel" and not userexists:
		out["pseudoProfile"] = True
	
	return out

def addToGroup(message, user):
	username = commander.noncmd_getChatUsername(message)
	dbhelper.sendToPostgres(config["addgrouptouser"], ("{\"" + str(message.chat.id) + "\": \"" + username + "\"}", user["id"]))
	user["groups"][message.chat.id] = username

async def banUserIfnecessary(message, user):
	if user["level"] == "banned" and not message.chat.type == "channel":
		try:
			await app.kick_chat_member(message.chat.id, user["id"], int(time.time() + 60*60*24*int(config["daystoban"]))) # kick chat member and automatically unban after ... days
		except (pyrogram.errors.ChatAdminRequired):
			await app.send_message(group, "User [{0[displayname]}](tg://user?id={0[id]}) has been banned from federation 'osmallgroups'. However that user couldn't be banned from this group. **Do I have the right to ban them here?**".format(user))
			return False
		except (pyrogram.errors.ChatWritePermission, pyrogram.errors.ChannelPrivate):
			commander.removegroup(None, message, None, None, None)
		except:
			pass
	
	addToGroup(message, user)

@app.on_message(pyrogram.Filters.command(allcommands))
async def precommandprocessing(client, message): # belongs to fosmbot's core
	user = addUserToDatabase(message.chat.type, message.from_user)
	if len(user) == 0:
		return False
	
	command = message.command
	if command is str:
		command = [command]
		message.command = [message.command]
	
	for i in range(user["level_int"], len(config["LEVELS"])):
		if command[0] in config["LEVEL_" + config["LEVELS"][i].upper()]:
			objid = 0
			if "chat" in dir(message) and message.chat is not None:
				objid = str(message.chat.id)
			else:
				objid = str(message.from_user.id)
			
			if "groupspecified" in config:
				if command[0] in config["groupspecified"]:
					if not objid == 0 and objid in config["groupspecified"][command[0]]:
						await commander.execCommand(command, client, message, user)
						return True
					elif command[0].startswith("can_"):
						if await commander.noncmd_userHasLocalChatPermission(message, user, command[0]):
							await commander.execCommand(command, client, message, user)
							return True
						else:
							await message.reply("Command not available to you. You need the '{}' for this group.", parse_mode="md")
						return False
					else:
						await message.reply("Command not available to you. It is either just executable in a specified group or just available for a specified user.", parse_mode="md")
						return False
			
			await commander.execCommand(command, client, message, user)
			return True
	
	out = ["Insufficient rights. You are: {}".format(user["level"])]
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
		if len(user) == 0:
			continue
		
		if message.chat.type == "channel" or not dbhelper.isAuthorizedGroup(message.chat.id, config["groupslist"]):
			continue
		
		await banUserIfnecessary(message, user)

@app.on_message(pyrogram.Filters.left_chat_member)
async def userleaves(client, message):
	user = dbhelper.sendToPostgres(config["getuser"], (str(message.left_chat_member.id),))
	logging.info("User '{}'".format(user))
	if len(user) == 0:
		return False
	
	if message.chat.type == "channel":
		return False
	
	if message.chat.id in user["groups"]:
		return False
	
	dbhelper.sendToPostgres(config["removegroupfromuser"].format(message.chat.id, user["id"])) #necessary because psycopg2 adds a trailing whitespace to negative integers causing this SQL not to work

@app.on_message()
async def messageFromUser(client, message): # belongs to fosmbot's core
	user = addUserToDatabase(message.chat.type, message.from_user)
	
	if len(user) == 0:
		return False
	
	if not message.chat.id in user["groups"] and not message.chat.type == "private" and not message.chat.type == "channel":
		addToGroup(message, user)
	
	if "forward_from" in dir(message) and message.forward_from is not None:
		if not "pseudoProfile" in user:
			message.chat.type = "group"
		addUserToDatabase(message.chat.type, message.forward_from)
		
	if "reply_to_message" in dir(message) and message.reply_to_message is not None:
		addUserToDatabase(message.chat.type, message.reply_to_message.from_user)
	
	if message.chat.type == "channel" or message.chat.type == "private" or not dbhelper.isAuthorizedGroup(message.chat.id, config["groupslist"]):
		return False
	
	await banUserIfnecessary(message, user)

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
	
