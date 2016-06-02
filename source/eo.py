#! /usr/bin/python

"""
Parsing eo sources.

Bytes:
>>> eo = EoParser("65 6F 20 6C 61 6E 67")
>>> eo.parse()
'eo lang'
"""

from StringIO import StringIO
import argparse
import os


class Byte(object):

	def __init__(self, char, infile):
		self.value = char + infile.read(1)

	def __radd__(self, string):
		return string + chr(int(self.value, 16))


class EoParser(object):

	def __init__(self, infile):
		if type(infile) == str:
			self.infile = StringIO(infile)
		else:
			self.infile = infile
		self.infile.seek(0, os.SEEK_END)
		self.length = self.infile.tell()
		self.infile.seek(0)

	def parse(self):
		result = str()
		while self.infile.tell() < self.length:
			char = self.infile.read(1)
			if char in "0123456789ABCDEF":
				byte = Byte(char, self.infile)
				result += byte
		return result


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("infile", nargs="?", type=argparse.FileType("r"))
	args = parser.parse_args()
