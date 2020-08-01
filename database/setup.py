#!/usr/bin/env python3
import sys, os, copy
sys.path.append(os.path.join(os.path.dirname(os.getcwd())))
os.chdir(os.path.join(os.path.dirname(os.getcwd())))
from lib.config import readConfig
from lib.database import management

APIconf = {}
queries = {"users": "createtable", "groups": "createtable"}
cmds = {"createdb": """psql -c "CREATE DATABASE {};" """, "exeSQL": "psql --dbname={} --file={}"}
sqls = {"createtable": "CREATE TABLE {} ({})"}

def main():
	global APIconf, queries, cmds
	
	print("loading mentorAPI configuration...")
	APIconf = readConfig(os.path.join(os.getcwd(), "mentorapi.yml")).config
	
	print("connecting to the database with the following dbconnstr:")
	print("  ", APIconf["dbconnstr"])
	dbhelper = management(APIconf["dbconnstr"])
	if not dbhelper.error == "":
		print("\033[1;mDatabase does not exist\033[0;m")
		
		print("creating database '{}'...".format(APIconf["dbname"]))
		dbhelper.createDatabase(APIconf["dbname"])
		
		print("restarting...")
		return main()
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
				print("\033[0;31mtable scheme not specified in osmallgroupsbot.yml!\033[0;m")
			
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

if "__main__" == __name__:
	main()
