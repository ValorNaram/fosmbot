#!/usr/bin/env python3
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extensions import ISOLATION_LEVEL_DEFAULT
from psycopg2 import sql
import psycopg2

class Record():
	def __toDict(self, table):
		data = {}
		index = 0
		if self.cur.rowcount == 0:
			return data
		
		for row in table:
			col = {}
			for i in range(0, len(self.columns)):
				col[self.columns[i]] = row[i]
			data[index] = col
			index += 1
		return data
	
	def __init__(self, conn, query, params=(), limit=1):
		self.conn = conn
		self.cur = self.conn.cursor()
		self.limit = limit
		
		if params == ():
			self.cur.execute(query)
		else:
			self.cur.execute(query, params)
		
		self.columns = []
		if not self.cur.description == None:
			for col in self.cur.description:
				self.columns.append(col.name)
		
	def __iter__(self):
		return self
	
	def __next__(self):
		if self.limit == 1:
			result = self.cur.fetchone()
			if result == None:
				self.cur.close()
				raise StopIteration
			
			return self.__toDict([result])[0]
		else:
			result = self.cur.fetchmany(self.limit)
			if result == None:
				self.cur.close()
				raise StopIteration
			
			return self.__toDict(result)
	
	def cancel(self):
		self.cur.close()
	
	def get(self):
		try:
			return self.__next__()
		except StopIteration:
			return {}

class helper(): # thread safe
	def __init__(self, conf):
		self.conf = conf
		self.conn = psycopg2.connect(conf["dbconnstr"])
		self.lock = False
		self.canShutdown = True
			
	def toJSON(self, table, columns, curs):
		return self.__toJSON(table, columns, curs)
	
	def __toJSON(self, table, columns, curs): # for backward compactibility, legacy code support
		data = {}
		if curs.rowcount == 0:
			return data
		
		for row in table:
			col = {}
			ident = ""
			for i in range(0, len(columns)):
				if columns[i] == "id":
					ident = row[i]
				col[columns[i]] = row[i]
			data[ident] = col
		return data
	
	"""def userExists(self, userid, data={}):
		if userid in data:
			return True
		
		result = False
		cur = self.conn.cursor()
		
		cur.execute(self.conf["getuser"], (str(userid),))
		if cur.rowcount == 1:
			result = True
		else:
			result = False
		
		if result:
			if not cur.description == None:
				columns = []
				for col in cur.description:
					columns.append(col.name)
			out = self.toJSON([cur.fetchone()], columns, cur)
			cur.close()
			return result, out
		cur.close()
		return result, {}"""
	
	def isAuthorizedGroup(self, groupid, output=None): # legacy code support
		if output == None:
			output = self.sendToPostgres(self.conf["getgroup"], (groupid,))
			if len(output) > 0:
				return True
			return False
		else:
			if groupid in output:
				return True
			return False
	
	"""def userHasLevel(self, userid, level, data={}):
		userid = str(userid)
		if self.userExists(userid, data):
			result, data = self.getuserlevel(userid, data)
			
			if result.startswith("error"):
				if level == self.conf["LEVELS"][len(self.conf["LEVELS"])-1]:
					return True
				else:
					return False
			
			if result == level:
				return True
		return False"""
	
	"""def resolveUsername(self, username, output={}):
		if username is int or username is float:
			return username, output
		
		username = username.lower()
		
		if len(output) == 0:
			output = self.sendToPostgres(self.conf["getuserbyusername"], (username.replace("@", ""),))
		if len(output) > 0:
			for user in output:
				return str(user), output
		
		return "error - user not existing", {}"""
	
	"""def getuserlevel(self, userid, output={}):
		if len(output) == 0:
			output = self.sendToPostgres(self.conf["getuser"], (str(userid),))
		
		if len(output) == 0:
			return "error - user not existing", {}
		for user in output:
			return output[user]["level"], output"""
	
	def getCursor(self, query, params=()): # legacy code support
		if self.lock == True:
			return None
		
		cur = self.conn.cursor()
		if params == ():
			cur.execute(query)
		else:
			cur.execute(query, params)
		
		return cur
	
	def getOneRow(self, cursor): # legacy code support
		if self.lock == True:
			self.closeCursor(cursor)
			return None
		
		columns = []
		if not cursor.description == None:
			for col in cursor.description:
				columns.append(col.name)
		result = cursor.fetchone()
		if result == None:
			return None
		return self.__toJSON([result], columns, cursor)
	
	def closeCursor(self, cursor): # legacy code support
		cursor.close()
	
	def getResult(self, query, param, limit=1):
		return Record(self.conn, query, param, limit)
	def sendToPostgres(self, query, params=(), limit=20): # legacy code support
		if self.lock == False:
			output = {}
			self.canShutdown = False
			
			with self.conn:
				with self.conn.cursor() as cursor:
					if params == ():
						cursor.execute(query)
					else:
						cursor.execute(query, params)
					if not cursor.description == None:
						columns = []
						for col in cursor.description:
							columns.append(col.name)
						output = self.__toJSON(cursor.fetchmany(limit), columns, cursor)
			
			self.canShutdown = True
			return output
		else:
			return "error - shutting down"
	
	def tearDown(self): # legacy code support
		self.lock = True
		while self.canShutdown == False:
			pass
		self.conn.close()

class management(): # not thread safe
	def __init__(self, dbconnstr):
		self.error = ""
		try:
			self.conn = psycopg2.connect(dbconnstr)
		except psycopg2.errors.OperationalError:
			self.error = "DOES NOT EXIST"
	
	def createDatabase(self, dbname):
		self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
		cur = self.conn.cursor()
		cur.execute("CREATE DATABASE " + dbname)
		cur.close()
		self.conn.set_isolation_level(ISOLATION_LEVEL_DEFAULT)
	
	def alterTable(self, name, desiredCols, beloud=True):
		query = []
		returnedCols = []
		desiredCols_simplified = []
		changes = False
		
		if not ("id", "text") in desiredCols:
			desiredCols = [("id", "text")] + desiredCols
		
		for i in desiredCols:
			desiredCols_simplified.append(i[0])
		
		with self.conn:
			with self.conn.cursor() as cursor:
				cursor.execute(sql.SQL("SELECT * FROM {} LIMIT 0").format(sql.Identifier(name)))
				for col in cursor.description:
					returnedCols.append(col.name)
		
		for n, i in enumerate(returnedCols):
			colname = i[0]
			if colname in returnedCols and not colname in desiredCols_simplified:
				# remove from database table `name`
				if beloud:
					print("\033[1;31mwill remove\033[0;m '{}' from database table '{}'".format(i, name))
				
				cur = self.conn.cursor()
				query.append(sql.SQL("ALTER TABLE {} DROP COLUMN {}").format(sql.Identifier(name), sql.Identifier(colname)).as_string(cur))
				cur.close()
				changes = True
		for n, i in enumerate(desiredCols):
			colname, coltype = i
			if colname in desiredCols_simplified and not colname in returnedCols:
				# add to database table `name`
				if beloud:
					print("\033[1;32mwill add\033[0;m '{}' to database table '{}'".format(i, name))
				
				cur = self.conn.cursor()
				print(colname, coltype)
				query.append(sql.SQL("ALTER TABLE {} ADD {} {}").format(sql.Identifier(name), sql.Identifier(colname), sql.Identifier(coltype)).as_string(cur))
				cur.close()
				changes = True
		
		if len(query) > 0:
			with self.conn:
				with self.conn.cursor() as cursor:
					print("executing query ('will' becomes 'do now')...")
					cursor.execute(";\n".join(query))
		return changes
	
	def executeCMD(self, query, params=()):
		error = None
		with self.conn:
			with self.conn.cursor() as cursor:
				try:
					cursor.execute(query, params)
				except Exception as e:
					error = e
					cursor.rollback()
		return error
				
	def tableExists(self, name):
		exists = False
		with self.conn:
			with self.conn.cursor() as cursor:
				try:
					cursor.execute("SELECT * FROM " + name + " LIMIT 0")
					exists = True
				except psycopg2.errors.UndefinedTable:
					exists = False
		return exists
	
	def tearDown(self):
		self.conn.close()
