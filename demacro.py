#!/usr/bin/python -O
"""
Parse macros in LaTeX source code. Supported macros include:
    - newcommand/renewcommand(*)
        Support various syntax, multiple-line definition, multiple arguments
        Do not support optional arguments
    - DeclareMathOperator(*)
    - def
    - input
        Combine all the input files into one

Usage:
    demacro.py <inputfile.tex> <outputfile.tex>

"""

def cut_extension(filename, ext):
    """
    If filename has extension ext (including the possible dot),
    it will be cut off.
    """
    file = filename
    index = filename.rfind(ext)
    if 0 <= index and len(file)-len(ext) == index:
        file = file[:index]
    return file

import sys
import re
import os

if __name__ == "__main__":

	inputHandler = open(sys.argv[1], 'r')
	outputHandler = open(sys.argv[2], "w")
#	outputSty = open('temp.sty', "w")
	contents = []

	for line in inputHandler:
		match = re.search(r"(.*)\\input{[./]*(.*?)}(.*)", line)
		if match:
			contents.append(match.group(1))
			if re.search(r"%", match.group(1)):
				pass
			else:
				inputPath = os.getcwd() + '/' + cut_extension(match.group(2),'.tex') + '.tex'
				if os.path.exists(inputPath):
					inputFile = open(inputPath, 'r')
					contents = contents + inputFile.readlines()
					contents.append('\n')
				contents.append(match.group(3))
		else:
			contents.append(line)
	inputHandler.close()

	newcPat = re.compile( r"^\s*\\newcommand\*?\s*{?\s*\\([A-Za-z0-9]*)\s*}?\s*([^\%^\n]*)")
	renewcPat = re.compile( r"^\s*\\renewcommand\*?\s*{?\s*\\([A-Za-z0-9]*)\s*}?\s*([^\%^\n]*)")
	defPat = re.compile( r"^\s*\\def\s*{?\s*\\([A-Za-z0-9]*)\s*}?\s*(([{\[]?\#\d[}\]]?)*){([^\%^\n]*)}" )
	mathPat = re.compile( r"\\DeclareMathOperator\*?{?\\([A-Za-z]*)}?{((:?[^{}]*{[^}]*})*[^}]*)}" )
	commandDict = {}
	mathDict = {}

	for line in contents:

		current = line

		newcMatch = newcPat.search(line)
		if newcMatch:
			if not re.search(r"@", line):
				multipleArg = re.search(r"^(\[(\d)\])?(.*){((:?[^{}]*{[^}]*})*[^}]*)}", newcMatch.group(2))
				if multipleArg.group(1):
					commandDict[newcMatch.group(1)] = [multipleArg.group(4), int(multipleArg.group(2))]
				else:
					commandDict[newcMatch.group(1)] = [multipleArg.group(4), 0]
			current = re.sub(newcPat, "", line)

		renewcMatch = renewcPat.search(line)
		if renewcMatch:
			if not re.search(r"@", line):
				if len(re.findall('{', renewcMatch.group(2)))==0:
					commandDict[renewcMatch.group(1)] = [renewcMatch.group(2), 0]
				else:
					multipleArg = re.search(r"^(\[(\d)\])?(.*){((:?[^{}]*{[^}]*})*[^}]*)}", renewcMatch.group(2))
					if multipleArg.group(1):
						commandDict[renewcMatch.group(1)] = [multipleArg.group(4), int(multipleArg.group(2))]
					else:
						commandDict[renewcMatch.group(1)] = [multipleArg.group(4), 0]
			current = re.sub(renewcPat, "", line)

		defMatch = defPat.search(line)
		if defMatch:
			if not re.search(r"@", line):
				commandDict[defMatch.group(1)] = [defMatch.group(4), len(re.findall(r"#",defMatch.group(2)))]
			current = re.sub(defPat, "", line)

		mathMatch = mathPat.search(line)
		if mathMatch:
			mathDict[mathMatch.group(1)] = mathMatch.group(2)
			current = re.sub(mathPat, "", line)

		for x in commandDict:
			if re.search(r"\\" + x + "(?![A-Za-z0-9])", current):
				if (commandDict[x][1]==0):
					#current = re.sub(r"\\" + x + "(?![A-Za-z0-9])", commandDict[x][0], current)
					match = re.search(r"^(.*)\\" + x + "(?![A-Za-z0-9])(.*)", current)
					while match:
						current = match.group(1) + commandDict[x][0] + match.group(2)
						match = re.search(r"^(.*)\\" + x + "(?![A-Za-z0-9])(.*)", current)
				else:
					pat = r"^(.*)\\" + x
					for i in range(0,commandDict[x][1]):
						pat = pat + r"\s*{((:?[^{}]*{[^}]*})*[^}]*)}"
					pat = pat + r"(.*)"
					match = re.search(pat, current)
					while match:
						definition = commandDict[x][0]
						for i in range(0,commandDict[x][1]):
							definition = re.sub(r"#"+str(i+1), match.group(i*2+2), definition)
						current = match.group(1) + definition + match.group(commandDict[x][1]*2+2)
						match = re.search(pat, current)
				current = current+'\n'

		for x in mathDict:
			#current = re.sub(r"\\" + x + "(?![A-Za-z0-9])", '\\operatorname{' + mathDict[x] + '}', current)
			#current = current.replace("\\" + x, "\\operatorname{" + mathDict[x] + "}")
			match = re.search(r"^(.*)\\" + x + "(?![A-Za-z0-9])(.*)", current)
			if match:
				while match:
					current = match.group(1) + '\\operatorname{' + mathDict[x] + '}' + match.group(2)
					match = re.search(r"^(.*)\\" + x + "(?![A-Za-z0-9])(.*)", current)
				current = current + '\n'
		
		outputHandler.write(current)

	outputHandler.close()