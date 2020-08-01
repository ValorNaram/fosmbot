#!/usr/bin/env python3
import os
class readConfig():
	def keyvaluepair(self, entries):
		if entries[1] == "" and len(self.lines) > self.index:
			self.triggers["  -"] = entries[0]
		else:
			key, value = entries
			self.config[key.strip()] = value.strip()
		
	def items(self, key, value):
		itemList = []
		if key in self.config:
			itemList = self.config[key]
		itemList.append(value.strip())
		self.config[key] = itemList
	
	def readIncluded(self, file):
		if os.path.exists(file):
			return readConfig(os.path.join(self.curdir, file)).config
		else:
			print("\033[0;31mWARNING: Configuration file '{}' does not exists\033[0;m".format(os.path.join(self.curdir, file)))
	def __init__(self, inp):
		"""
		not thread-safe
		"""
		
		self.curdir = os.path.dirname(inp)
		self.config = {}
		self.triggers = {}
		
		sfile = open(inp, "r")
		inp = sfile.read()
		sfile.close()
		
		self.lines = inp.split("\n")
		
		for index, line in enumerate(self.lines):
			self.index = index
			if line.startswith("include"):
				new = self.readIncluded(line.split(" ", 1)[1])
				if type(new) is dict:
					self.config.update(new)
			if line.find(":") > -1:
				self.keyvaluepair(line.split(":", 1))
			elif line.startswith("  -"):
				self.items(self.triggers["  -"], line.replace("  -", "", 1))
