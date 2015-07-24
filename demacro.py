#!/usr/bin/python -O
"""
Parse macros in LaTeX source code. Supported macros include:
	- newcommand/renewcommand(*)
	- DeclareMathOperator(*)
	- def
	- input

Usage:
	demacro.py <inputfile.tex> <outputfile.tex>

"""

def cut_extension(filename, ext):
	file = filename
	index = filename.rfind(ext)
	if 0 <= index and len(file)-len(ext) == index:
		file = file[:index]
	return file

import sys
import re
import os
import multiprocessing
import time


def main():

	inputHandler = open(sys.argv[1], 'rU')
	outputHandler = open(sys.argv[2], "w")
	contents = []

	# Expand \input{} files
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


	temp = []
	for line in contents:
		macros = re.findall(r"\\newcommand|\\renewcommand|\\def", line)
		if len(macros) <= 1:
			temp.append(line)
		else:
			pat = "(.*)\\"+"(.*)\\".join(macros)+"([^\n]*)" 
			match = re.search(pat, line)
			if match.group(1):
				temp.append(match.group(1))
			for i in range(0,len(macros)):
				if re.search(r"%",match.group(i+1)):
					break
				temp.append(macros[i]+match.group(i+2))
	contents = temp

	# Define patterns, dictionaries
	newcPat = re.compile( r"^\s*\\newcommand\*?\s*{?\s*\\([<>|~+-=]?[A-Za-z0-9]*)\s*}?\s*([^%\n]*)")
	renewcPat = re.compile( r"^\s*\\renewcommand\*?\s*{?\s*\\([<>|~+-=]?[A-Za-z0-9]*)\s*}?\s*([^%\n]*)")
	defPat = re.compile( r"^\s*\\def\s*{?\s*\\([<>|~+-=]?[A-Za-z0-9]*)\s*}?\s*(\[?#\d\]?)*\s*([^%\n]*)" )
	mathPat = re.compile( r"\\DeclareMathOperator\*?{?\\([A-Za-z]*)}?{((:?[^{}]*{[^}]*})*[^}]*)}" )
	commandDict = {}
	mathDict = {}
	warningFlag = 0
	multilineFlag = 0		# For definitions extended to several lines



	for line in contents:

		#print line 
		#print multilineFlag

		if multilineFlag:
			multilineMatch = re.search(r"([^%\n]*)", line)
			if not multilineMatch:
				continue
			current = current + multilineMatch.group(0)
			count_left = len(re.findall('{', current))
			count_right = len(re.findall('}', current))
			if count_left == count_right:
				multilineFlag = 0
			else:
				continue
		else:
			current = line

		if  len(re.findall(r"\\newcommand|\\renewcommand|\\def", current)) > 1:
			if warningFlag == 0:
				print "Warning: possible recursive definitions not expanded"
				warningFlag = 1
			outputHandler.write(current)
			continue

		# Parse \newcommand
		newcMatch = newcPat.search(current)
		if newcMatch:
			count_left = len(re.findall('{', newcMatch.group(2))) - len(re.findall(r'\\{', newcMatch.group(2)))
			count_right = len(re.findall('}', newcMatch.group(2))) - len(re.findall(r'\\}', newcMatch.group(2)))
			if count_left == count_right:
				if re.search(r"@|\\#", current):
					pass
				elif newcMatch.group(1):
					if len(re.findall('{', newcMatch.group(2)))==0:
						commandDict[newcMatch.group(1)] = [newcMatch.group(2), 0]
					else:
						# multipleArg = re.search(r"^(\[(\d)\])?(.*){((:?[^{}]*{[^}]*})*[^}]*)}", newcMatch.group(2))
						multipleArg = re.search(r"^(\[(\d)\])?([^{]*){(.*)}", newcMatch.group(2))
						if multipleArg:
							if multipleArg.group(1):
								commandDict[newcMatch.group(1)] = [multipleArg.group(4), int(multipleArg.group(2))]
							else:
								commandDict[newcMatch.group(1)] = [multipleArg.group(4), 0]
						else:
							multilineFlag = 1
							current = newcMatch.group(0)
							continue
					current = re.sub(newcPat, "", current)
			elif count_left > count_right:
				multilineFlag = 1
				current = newcMatch.group(0)
				continue
			else:
				outputHandler.write(current)
				continue

		# Parse \renewcommand
		renewcMatch = renewcPat.search(current)
		if renewcMatch:
			count_left = len(re.findall('{', renewcMatch.group(2))) - len(re.findall(r'\\{', renewcMatch.group(2)))
			count_right = len(re.findall('}', renewcMatch.group(2))) - len(re.findall(r'\\}', renewcMatch.group(2)))
			if count_left == count_right:
				if re.search(r"@|\\#", current):
					pass
				elif renewcMatch.group(1):
					if len(re.findall('{', renewcMatch.group(2)))==0:
						commandDict[renewcMatch.group(1)] = [renewcMatch.group(2), 0]
					else:
						# multipleArg = re.search(r"^(\[(\d)\])?(.*){((:?[^{}]*{[^}]*})*[^}]*)}", renewcMatch.group(2))
						multipleArg = re.search(r"^(\[(\d)\])?([^{]*){(.*)}", renewcMatch.group(2))
						if multipleArg:
							if multipleArg.group(1):
								commandDict[renewcMatch.group(1)] = [multipleArg.group(4), int(multipleArg.group(2))]
							else:
								commandDict[renewcMatch.group(1)] = [multipleArg.group(4), 0]
						else:
							multilineFlag = 1
							current = newcMatch.group(0)
							continue
					current = re.sub(renewcPat, "", current)
			elif count_left > count_right:
				multilineFlag = 1
				current = renewcMatch.group(0)
				continue
			else:
				outputHandler.write(current)
				continue

		# Parse \def
		defMatch = defPat.search(current)
		if defMatch:
			count_left = len(re.findall('{', defMatch.group(3))) - len(re.findall(r'\\{', defMatch.group(3)))
			count_right = len(re.findall('}', defMatch.group(3))) - len(re.findall(r'\\}', defMatch.group(3)))
			if count_left == count_right:
				defContent = re.search(r"^{(.*)}$", defMatch.group(3))
				if defContent:
					defContent = defContent.group(1)
				else:
					defContent = defMatch.group(3)
				if re.search(r"@|\\#", current):
					pass
				elif defMatch.group(1):
					if defMatch.group(2):
						commandDict[defMatch.group(1)] = [defContent, len(re.findall(r"#",defMatch.group(2)))]
					else:
						commandDict[defMatch.group(1)] = [defContent, 0]
					current = re.sub(defPat, "", current)
			elif count_left > count_right:
				multilineFlag = 1
				current = defMatch.group(0)
				continue
			else:
				outputHandler.write(current)
				continue

		# Parse \DeclareMathOperator
		mathMatch = mathPat.search(current)
		if mathMatch:
			mathDict[mathMatch.group(1)] = mathMatch.group(2)
			current = re.sub(mathPat, "", current)

		candidate = set(re.findall(r"\\([A-Za-z0-9]*)", current))		# Possible commands in the current line to be parsed
		# print candidate
		# print list(set(commandDict) & candidate)
		# print list(set(mathDict) & candidate)
		for x in list(set(commandDict) & candidate):
			# print x
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
							# definition = re.sub(r"#"+str(i+1), match.group(i*2+2), definition)
							definition = definition.replace(r"#"+str(i+1),match.group(i*2+2))
						current = match.group(1) + definition + match.group(commandDict[x][1]*2+2)
						match = re.search(pat, current)
				current = current+'\n'

		for x in list(set(mathDict) & candidate):
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


if __name__ == "__main__":

	# main()
	# Start main as a process
	p = multiprocessing.Process(target=main)
	p.start()

	# Wait for 300 seconds or until process finishes
	killTime = 300
	p.join(killTime)

	# If thread is still active
	if p.is_alive():
		print "Killing process after %d seconds\nOutput file as it is" %killTime
		# Terminate
		p.terminate()
		p.join()
		inputHandler = open(sys.argv[1], 'rU')
		outputHandler = open(sys.argv[2], "w")
		contents = []
		# Expand \input{} files
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
		for line in contents:
			outputHandler.write(line)
		outputHandler.close()