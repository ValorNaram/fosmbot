#!/usr/bin/env python3
from lib.database import management
import copy

def setupDB(APIconf):
	queries = {"users": "createtable", "groups": "createtable"}
	cmds = {"createdb": """psql -c "CREATE DATABASE {};" """, "exeSQL": "psql --dbname={} --file={}"}
	sqls = {"createtable": "CREATE TABLE {} ({})"}
	
	print("connecting to the database with the following dbconnstr:")
	print("  ", APIconf["dbconnstr"])
	dbhelper = management(APIconf["dbconnstr"])
	if not dbhelper.error == "":
		print("\033[1;mDatabase does not exist\033[0;m")
		
		dbconnstr = []
		dbname = ""
		for item in APIconf["dbconnstr"].split(" "):
			key, value = item.split("=", 1)
			if not key == "dbname":
				dbconnstr.append("{}={}".format(key, value))
			else:
				dbname = value
		dbhelper = management(" ".join(dbconnstr))
		
		print("creating database '{}'...".format(dbname))
		dbhelper.createDatabase(dbname)
		
		print("restarting...")
		return setupDB(APIconf)
	else:
		print("\033[1;mDatabase does exist\033[0;m")
	
	print("checking existence of requirred tables...")
	for i in queries:
		if dbhelper.tableExists(i):
			print("\033[0;32m  '{}' exists...\033[0;m".format(i))
		else:
			print("\033[0;31m  '{}' does not exist\033[0;m".format(i))
			if "table_" + i in APIconf:
				print("  creating table '{}'...".format(i))
				dbhelper.executeCMD(sqls[queries[i]].format(i, ",\n".join(APIconf["table_" + i])))
			else:
				print("\033[0;31mtable scheme not specified in fosmbot.yml!\033[0;m")
			
	print("syncing columns (insert/remove)...")
	changes = False
	for i in queries:
		if "table_" + i in APIconf:
			cols = copy.copy(APIconf["table_" + i])
			for n, content in enumerate(cols):
				colname, coltype = content.split(" ")
				cols[n] = (colname, coltype)
			changes = dbhelper.alterTable(i, cols)
	
	print("disconnecting from database...")
	dbhelper.tearDown()
