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

Arguments:
>>> eo = EoParser(' @tac a b { b " " a } tac "abc" "def" ')
>>> eo.parse()
'def abc'

Comments:
>>> eo = EoParser(' "Ângelo" (first name) " " (space) "Nuffer" (last name) ')
>>> eo.parse()
'\\xc3\\x82ngelo Nuffer'

Conditional:
>>> eo = EoParser(' @red { "color" } [ red = "name" ? "red is a name" ] [ red = "color" ? "red is a color" ] ')
>>> eo.parse()
'red is a color'
"""

from StringIO import StringIO
import argparse
import os
import re

VAR_TOKEN = r"[a-z_]"


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
		infile = file_or_string(infile)
		self.name = str()
		char = infile.read(1)
		while char not in " {":
			self.name += char
			char = infile.read(1)
		self.arguments = list()
		while char != "{":
			char = infile.read(1)
			if re.match(VAR_TOKEN, char):
				name = read_name(infile, char)
				self.arguments.append(name)
		char = infile.read(1)
		self.source = str()
		while char != "}":
			self.source += char
			char = infile.read(1)

	def __call__(self, infile, functions):
		arguments = list()
		for argument in self.arguments:
			value = read_value(infile, functions)
			arguments.append(Function('%s { "%s" }' % (argument, value.value)))
		return EoParser(self.source, arguments).parse()


class Comment(object):

	def __init__(self, infile):
		char = infile.read(1)
		while char != ")":
			char = infile.read(1)

	def __radd__(self, string):
		return string


class Conditional(object):

	def __init__(self, infile, functions):
		char = infile.read(1)
		value1 = str()
		while char != "=":
			value1 += char
			char = infile.read(1)
		char = infile.read(1)
		value2 = str()
		while char != "?":
			value2 += char
			char = infile.read(1)
		source = str()
		while char != "]":
			source += char
			char = infile.read(1)
		if EoParser(value1, functions).parse() == EoParser(value2, functions).parse():
			self.value = EoParser(source, functions).parse()
		else:
			self.value = str()

	def __radd__(self, string):
		return string + self.value


class EoParser(object):

	def __init__(self, infile, functions=None):
		self.infile = file_or_string(infile)
		self.infile.seek(0, os.SEEK_END)
		self.length = self.infile.tell()
		self.infile.seek(0)
		if type(functions) is list:
			self.functions = functions
		else:
			self.functions = list()

	def parse(self):
		result = str()
		while self.infile.tell() < self.length:
			value = read_value(self.infile, self.functions)
			if type(value) == Function:
				self.functions.append(value)
			else:
				result += value
		return result


def file_or_string(infile):
	if type(infile) == str:
		return StringIO(infile)
	return infile

def read_name(infile, char):
	name = str()
	while re.match(VAR_TOKEN, char):
		name += char
		char = infile.read(1)
	return name

def read_value(infile, functions):
	char = infile.read(1)
	if char == "":
		return ""
	elif char == "(":
		return Comment(infile)
	elif char in "0123456789ABCDEF":
		return Byte(char, infile)
	elif char == '"':
		return String(infile)
	elif char == "@":
		return Function(infile)
	elif char == "[":
		return Conditional(infile, functions)
	elif re.match(VAR_TOKEN, char):
		name = read_name(infile, char)
		for function in functions:
			if name == function.name:
				return function(infile, functions)
		raise BaseException(name)
	else:
		return read_value(infile, functions)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("infile", nargs="?", type=argparse.FileType("r"))
	args = parser.parse_args()
