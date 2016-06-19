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

Expressions:
>>> eo = EoParser(' [ "a" "b" "c" ] ')
>>> eo.parse()
'abc'

>>> eo = EoParser(' [ "a" "b" = "ab" ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ 01 + 02 ] ')
>>> ord(eo.parse())
3

>>> eo = EoParser(' [ 02 + 03 = 05 ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ 05 - 03 ] ')
>>> ord(eo.parse())
2

>>> eo = EoParser(' [ 09 * 03 ] ')
>>> ord(eo.parse())
27

>>> eo = EoParser(' [ 06 / 02 ] ')
>>> ord(eo.parse())
3

>>> eo = EoParser(' [ 05 % 02 ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ 03 = 03 ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ 03 != 04 ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ 05 > 04 ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ 02 < 04 ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ 05 >= 04 ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ 03 <= 04 ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ "a" && "" ] ')
>>> eo.parse()
''

>>> eo = EoParser(' [ "a" || "" ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ 02 & 03 ] ')
>>> ord(eo.parse())
2

>>> eo = EoParser(' [ 02 | 03 ] ')
>>> ord(eo.parse())
3

>>> eo = EoParser(' [ 02 ^ 03 ] ')
>>> ord(eo.parse())
1

>>> eo = EoParser(' [ 02 << 02 ] ')
>>> ord(eo.parse())
8

>>> eo = EoParser(' [ 08 >> 02 ] ')
>>> ord(eo.parse())
2

>>> eo = EoParser(' @red { "color" } [ red = "name" ? "red is a name" ] [ red = "color" ? "red is a color" ] ')
>>> eo.parse()
'red is a color'

>>> eo = EoParser(' @a { 0A } @b { 0B } [ a = 0A ? [ b = 0B ? "a is 0A and b is 0B" ] ] ')
>>> eo.parse()
'a is 0A and b is 0B'
"""

from StringIO import StringIO
import argparse
import sys
import os
import re

VAR_TOKEN = r"[a-zĉĝĥĵŝŭ0-9_]"


class Byte(object):

	def __init__(self, char, infile):
		self.value = char + infile.read(1)

	def __radd__(self, string):
		return string + chr(int(self.value, 16))

	def __repr__(self):
		return self.value


class String(object):

	def __init__(self, infile):
		infile = file_or_string(infile)
		self.value = str()
		char = infile.read(1)
		while char != '"' and char != "":
			self.value += char
			char = infile.read(1)

	def __radd__(self, string):
		return string + self.value

	def __repr__(self):
		return '"%s"' % self.value


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
			arguments.append(Function('%s { %s }' % (argument, value)))
		return EoParser(self.source, arguments + functions).parse()


class Comment(object):

	def __init__(self, infile):
		char = infile.read(1)
		while char != ")":
			char = infile.read(1)

	def __radd__(self, string):
		return string


class Expression(object):

	operators = {
		"+": "add",
		"-": "subtract",
		"*": "multiply",
		"/": "divide",
		"%": "modulus",
		"=": "equals",
		"!=": "not_equals",
		">": "greater",
		"<": "less",
		">=": "greater_or_equals",
		"<=": "less_or_equals",
		"&&": "and_",
		"||": "or_",
		"&": "binary_and",
		"|": "binary_or",
		"^": "binary_xor",
		"<<": "binary_left_shift",
		">>": "binary_right_shift",
		"?": "if_",
	}

	def __init__(self, infile, functions):
		value1 = self.get_value(infile, functions)
		operator = self.get_operator(infile, functions)
		while operator:
			value2 = self.get_value(infile, functions)
			value1 = getattr(self, Expression.operators[operator])(value1, value2, functions)
			operator = self.get_operator(infile, functions)
		self.value = EoParser(value1, functions).parse()

	def __radd__(self, string):
		return string + self.value

	def __repr__(self):
		return self.value.encode("hex").upper()

	def get_value(self, infile, functions):
		char = infile.read(1)
		value = str()
		inside = 0
		while char not in map(lambda operator: operator[0], Expression.operators.keys()) + ["]"] or inside > 0:
			if char == "[":
				inside += 1
			if char == "]":
				inside -= 1
			value += char
			char = infile.read(1)
		infile.seek(-1, os.SEEK_CUR)
		return value

	def get_operator(self, infile, functions):
		operator = infile.read(1)
		if operator == "]":
			return ""
		char = infile.read(1)
		if operator + char in Expression.operators:
			operator += char
		return operator

	def add(self, value1, value2, functions):
		value1 = int(EoParser(value1, functions).parse().encode("hex"), 16)
		value2 = int(EoParser(value2, functions).parse().encode("hex"), 16)
		value = hex(value1 + value2)[2:]
		return value.zfill(len(value) + len(value) % 2 )

	def subtract(self, value1, value2, functions):
		value1 = int(EoParser(value1, functions).parse().encode("hex"), 16)
		value2 = int(EoParser(value2, functions).parse().encode("hex"), 16)
		value = hex(value1 - value2)[2:]
		return value.zfill(len(value) + len(value) % 2 )

	def multiply(self, value1, value2, functions):
		value1 = int(EoParser(value1, functions).parse().encode("hex"), 16)
		value2 = int(EoParser(value2, functions).parse().encode("hex"), 16)
		value = hex(value1 * value2)[2:]
		return value.zfill(len(value) + len(value) % 2 )

	def divide(self, value1, value2, functions):
		value1 = int(EoParser(value1, functions).parse().encode("hex"), 16)
		value2 = int(EoParser(value2, functions).parse().encode("hex"), 16)
		value = hex(value1 / value2)[2:]
		return value.zfill(len(value) + len(value) % 2 )

	def modulus(self, value1, value2, functions):
		value1 = int(EoParser(value1, functions).parse().encode("hex"), 16)
		value2 = int(EoParser(value2, functions).parse().encode("hex"), 16)
		value = hex(value1 % value2)[2:]
		return value.zfill(len(value) + len(value) % 2 )

	def equals(self, value1, value2, functions):
		if EoParser(value1, functions).parse() == EoParser(value2, functions).parse():
			return "01"
		return ""

	def not_equals(self, value1, value2, functions):
		if EoParser(value1, functions).parse() != EoParser(value2, functions).parse():
			return "01"
		return ""

	def greater(self, value1, value2, functions):
		if EoParser(value1, functions).parse() > EoParser(value2, functions).parse():
			return "01"
		return ""

	def less(self, value1, value2, functions):
		if EoParser(value1, functions).parse() < EoParser(value2, functions).parse():
			return "01"
		return ""

	def greater_or_equals(self, value1, value2, functions):
		if EoParser(value1, functions).parse() >= EoParser(value2, functions).parse():
			return "01"
		return ""

	def less_or_equals(self, value1, value2, functions):
		if EoParser(value1, functions).parse() <= EoParser(value2, functions).parse():
			return "01"
		return ""

	def and_(self, value1, value2, functions):
		if EoParser(value1, functions).parse() and EoParser(value2, functions).parse():
			return "01"
		return ""

	def or_(self, value1, value2, functions):
		if EoParser(value1, functions).parse() or EoParser(value2, functions).parse():
			return "01"
		return ""

	def binary_and(self, value1, value2, functions):
		value1 = int(EoParser(value1, functions).parse().encode("hex"), 16)
		value2 = int(EoParser(value2, functions).parse().encode("hex"), 16)
		value = hex(value1 & value2)[2:]
		return value.zfill(len(value) + len(value) % 2 )

	def binary_or(self, value1, value2, functions):
		value1 = int(EoParser(value1, functions).parse().encode("hex"), 16)
		value2 = int(EoParser(value2, functions).parse().encode("hex"), 16)
		value = hex(value1 | value2)[2:]
		return value.zfill(len(value) + len(value) % 2 )

	def binary_xor(self, value1, value2, functions):
		value1 = int(EoParser(value1, functions).parse().encode("hex"), 16)
		value2 = int(EoParser(value2, functions).parse().encode("hex"), 16)
		value = hex(value1 ^ value2)[2:]
		return value.zfill(len(value) + len(value) % 2 )

	def binary_left_shift(self, value1, value2, functions):
		value1 = int(EoParser(value1, functions).parse().encode("hex"), 16)
		value2 = int(EoParser(value2, functions).parse().encode("hex"), 16)
		value = hex(value1 << value2)[2:]
		return value.zfill(len(value) + len(value) % 2 )

	def binary_right_shift(self, value1, value2, functions):
		value1 = int(EoParser(value1, functions).parse().encode("hex"), 16)
		value2 = int(EoParser(value2, functions).parse().encode("hex"), 16)
		value = hex(value1 >> value2)[2:]
		return value.zfill(len(value) + len(value) % 2 )

	def if_(self, value1, value2, functions):
		if EoParser(value1, functions).parse() == "":
			return ""
		return value2


class Library(object):

	def __init__(self, infile, functions):
		char = infile.read(1)
		source = str()
		while char != "!":
			source += char
			char = infile.read(1)
		self.value = EoParser(open(EoParser(source, functions).parse()).read(), functions).parse()

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
				for function in self.functions:
					if function.name == value.name:
						self.functions.remove(function)
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
		return String("")
	elif char == "(":
		return Comment(infile)
	elif char in "0123456789ABCDEF":
		return Byte(char, infile)
	elif char == '"':
		return String(infile)
	elif char == "@":
		return Function(infile)
	elif char == "[":
		return Expression(infile, functions)
	elif char == "#":
		return Library(infile, functions)
	elif re.match(VAR_TOKEN, char):
		name = read_name(infile, char)
		for function in functions:
			if name == function.name:
				return String(function(infile, functions))
		raise NameError("name '%s' is not defined" % name)
	else:
		return read_value(infile, functions)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("infile", nargs="?", type=argparse.FileType("r"))
	args = parser.parse_args()
	sys.stdout.write(EoParser(args.infile).parse())
