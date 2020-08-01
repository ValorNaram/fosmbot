#!/usr/bin/env python3
from lib import database
import logging, yaml, pyrogram, time

config = {}

logging.basicConfig(format='[osmallgroups Bot]: %(asctime)s %(message)s', level=logging.DEBUG, datefmt="%m/%d/%Y %I:%M:%S %p")

app = pyrogram.Client("fosm")

class commandControl():
	def __init__(self):
		pass
	
	def reply(message, self, message, text):
		message.reply(message, text, disable_web_page_preview=True)
	
	def replySilence(message, self, message, text):
		message.reply(message, text, disable_web_page_preview=True, disable_notification=True)
	
	def createTimestamp(self):
		return time.strftime("%Y-%m-%d")
	
	def changeLevel(self, client, message, userlevel, userlevel_int):
		command = message.command
		if not len(command) == 2:
			self.replySilence(message, "Syntax: `/changeLevel <level> <user>`")
			return False
		
		
		levelToPromoteTo_int = config["levels"].index(command[0])
		if not levelToPromoteTo_int > userlevel_int: # if true, then the user who issued that command has no rights to promote <user> to <level>
			return False # user does not have the right to promote <user> to <level>
		
		userToPromote = command[1]
		if command[1].startswith("@"): # if true, then resolve username to telegram id
			command[1] = dbhelper.resolveUsername(command[1])
			if command[1].startswith("error"):
				self.replySilence(message, "User '{}' does not exist in the database".format(userToPromote))
		
		userToPromote_int = config["levels"].index(dbhelper.getuserlevel(command[1]))
		if not userToPromote_int > userlevel_int: # if true, then the user who issued that command has no rights to promote <user> to <level>
			return False
		
		dbhelper.sendToPostgres(config["changeLevel"], (command[0], int(command[1])))
	
	def demoteme(self, client, message, userlevel, userlevel_int):
		if not message.chat.type == "private":
			return False
		
		if not userlevel = "owner":
			dbhelper.sendToPostgres(config["changeLevel"], ("user", userlevel_int))
		
		self.reply(message, "You are now powerless! Thank You for your effort to cut down spammers")
	
	def funban(self, client, message, userlevel, userlevel_int):
		command = message.command
		
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				self.replySilence(message, "User '{}' does not exist in the database".format(userToPromote))
				return False
		
		dbhelper.sendToPostgres(config["updatecomment"], ("unbanned"))
		dbhelper.sendToPostgres(config["updateissuedbyid"], (message.from_user.id, command[0]))
		dbhelper.sendToPostgres(config["changeLevel"], ("user", command[0]))
		
		groups = dbhelper.sendToPostgres(config["getgroups"])
		for group in groups:
			app.unban_chat_member(group, command[0])
	
	def fban(self, client, message, userlevel, userlevel_int):
		command = message.command
		
		if not len(command) > 2:
			self.replySilence(message, "Please provide a reason to ban a user for 365 days. Syntax: `/fban <username> <reason>".format(userToPromote))
			return False
		
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[0].startswith("error"):
				self.replySilence(message, "User '{}' does not exist in the database".format(userToPromote))
				return False
		toban = int(command[0])
		del command[0]
		
		dbhelper.sendToPostgres(config["updatecomment"], (" ".join(command)))
		dbhelper.sendToPostgres(config["updateissuedbyid"], (message.from_user.id, toban))
		dbhelper.sendToPostgres(config["changeLevel"], ("banned", toban))
		
		groups = dbhelper.sendToPostgres(config["getgroups"])
		for group in groups:
			app.kick_chat_member(group, toban, int(time.time() + 31536000)) # kick chat member and automatically unban after 365 days
		
	def newowner(self, client, message, userlevel, userlevel_int):
		if not message.chat.type == "private":
			return False
		
		command = message.command
		
		if not userlevel_int == 0:
			return False
		
		if command[0].startswith("@"): # if true, then resolve username to telegram id
			command[0] = dbhelper.resolveUsername(command[0])
			if command[1].startswith("error"):
				self.replySilence(message, "User '{}' does not exist in the database".format(userToPromote))
		
		dbhelper.sendToPostgres(config["changeLevel"], ("owner", int(command[0])))
		dbhelper.sendToPostgres(config["changeLevel"], ("user", int(command[0])))
		self.replySilence(message, "Ownership changed")
	
	def addgroup(self, client, message, userlevel, userlevel_int):
		dbhelper.sendToPostgres(config["authorizegroup"], (message.chat.id))
		self.reply(message, "Added group. Now it belongs to the federation 'osmallgroups'")
	
	def removegroup(self, client, message, userlevel, userlevel_int):
		dbhelper.sendToPostgres(config["deauthorizegroup"], (message.chat.id))
		self.reply(message, "Removed group. Now it no longer belongs to the federation 'osmallgroups'")
	
	def __returnusers(self, message, level):
		if not message.chat.type == "private":
			return False
		output = []
		
		users = dbhelper.sendToPostgres(config["getusersbylevel"], (level))
		for userid in users:
			output.append(users[userid]["username"] + "<br />")
		
		self.reply(message, "- ".join(output))
	
	def owners(self, client, message, userlevel, userlevel_int):
		self.__returnusers(message, "owner")
		
	def fedadmins(self, client, message, userlevel, userlevel_int):
		self.__returnusers(message, "fedadmin")
	
	def superadmins(self, client, message, userlevel, userlevel_int):
		self.__returnusers(message, "superadmin")
	
	def fbanlist(self, client, message, userlevel, userlevel_int):
		output = ["id", "username", "displayname", "reason", "issued"]
		banned = dbhelper.sendToPostgres(config["getusersbylevel"], ("banned"))
		
		for userid in banned:
			line = []
			row = banned[userid]:
			for field in row:
				line.append("\"" + field + "\"")
			output.append(",".join(output))
		
		sfile = open("fbanlist.csv", "w")
		sfile.write("\n".join(output))
		sfile.close()
		
		message.reply_document("fbanlist.csv")
	
	def fstat(self, client, message, userlevel, userlevel_int)
	def mylevel(self, client, message, userlevel, userlevel_int):
		if not message.chat.type == "private":
			return False
		
		message.reply(userlevel)
		
	def execCommand(self, command, client, message, userlevel, userlevel_int):
		if not command[0].startswith("__"):
			del message.command[0]
			self.__getattribute__(command)(client, message, userlevel, userlevel_int)

@app.on_message(pyrogram.Filters.new_chat_members)
def userjoins(client, message):
	newmembers = message.new_chat_members
	
	for member in newmembers:
		displayname = []
		if member.first_name: displayname.append(member.first_name)
		if member.last_name: displayname.append(member.last_name)
		
		displayname = " ".join(displayname)
		
		if not member.is_self and not member.is_deleted and not member.is_bot and not member.is_verified and not member.is_support:
			if not dbhelper.userExists(member.id):
				dbhelper.sendToPostgres(config["adduser"], (member.id, member.username, displayname, createTimestamp()))

@app.on_message(pyrogram.Filters.command(allcommands))
def postcommandprocessing(client, message):
	command = message.command
	userlevel = dbhelper.getuserlevel(message.from_user.id)
	rightlevel = config["levels"].index(userlevel)
	
	for i in range(rightlevel, len(config["levels"])):
		if command[0] in config["LEVEL_" + config["levels"][i].upper()]:
			del command[0]
			commander.execCommand(command, client, message, userlevel, rightlevel)
			return True
	
	commander.reply("Insufficient rights. You are: {}".format(userlevel))

@app.on_message()
def checkExistenceOfUser(client, message):
	message.new_chat_members = message.from_user
	userjoins(client, message)
				
def main():
	global config, dbhelper, commander, allcommands
	
	logging.info("loading 'fosmbot.yml'...")
	sfile = open("fosmbot.yml", "r")
	config = yaml.load(sfile, loader=yaml.FullLoader)
	sfile.close()
	
	for level in config["levels"]:
		for command in config["LEVEL_" + level.upper()]:
			allcommands.append(command)
	
	logging.info("connecting to database...")
	dbhelper = database.helper(config)
	
	logging.info("starting fosmbot...")
	commander = commandControl()
	app.run()

if __name__ == "__main__":
	main()
