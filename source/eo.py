#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Parsing eo sources.

Bytes:
>>> eo = EoParser("65 6F 20 6C 61 6E 67")
>>> eo.parse()
'eo lang'

Strings:
>>> eo = EoParser(' "string in eo lang" ')
>>> eo.parse()
'string in eo lang'

Functions:
>>> eo = EoParser(' @last_name { "Nuffer" } "Ângelo " last_name ')
>>> eo.parse()
'\\xc3\\x82ngelo Nuffer'
"""

from StringIO import StringIO
import argparse
import os
import re


class Byte(object):

	def __init__(self, char, infile):
		self.value = char + infile.read(1)

	def __radd__(self, string):
		return string + chr(int(self.value, 16))


class String(object):

	def __init__(self, infile):
		self.value = str()
		char = infile.read(1)
		while char != '"':
			self.value += char
			char = infile.read(1)

	def __radd__(self, string):
		return string + self.value


class Function(object):

	def __init__(self, infile):
		self.name = str()
		char = infile.read(1)
		while char not in " {":
			self.name += char
			char = infile.read(1)
		while char != "{":
			char = infile.read(1)
		char = infile.read(1)
		content = str()
		while char != "}":
			content += char
			char = infile.read(1)
		self.content = EoParser(content).parse()


class EoParser(object):

	VAR_TOKEN = r"[a-z_]"

	def __init__(self, infile):
		if type(infile) == str:
			self.infile = StringIO(infile)
		else:
			self.infile = infile
		self.infile.seek(0, os.SEEK_END)
		self.length = self.infile.tell()
		self.infile.seek(0)
		self.functions = list()

	def parse(self):
		result = str()
		while self.infile.tell() < self.length:
			char = self.infile.read(1)
			if char in "0123456789ABCDEF":
				byte = Byte(char, self.infile)
				result += byte
			elif char == '"':
				string = String(self.infile)
				result += string
			elif char == "@":
				function = Function(self.infile)
				self.functions.append(function)
			elif re.match(EoParser.VAR_TOKEN, char):
				name = str()
				while re.match(EoParser.VAR_TOKEN, char):
					name += char
					char = self.infile.read(1)
				for function in self.functions:
					if name == function.name:
						result += function.content
		return result


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("infile", nargs="?", type=argparse.FileType("r"))
	args = parser.parse_args()
