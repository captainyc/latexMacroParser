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

import sys
import re
import os
import multiprocessing
import time
import argparse
import glob
import tarfile
from itertools import repeat
import time
import shutil

def cut_extension(filename, ext):
    file = filename
    index = filename.rfind(ext)
    if 0 <= index and len(file)-len(ext) == index:
        file = file[:index]
    return file

def find_token(string):
    string = re.search(r"^\s*(.*)",string).group(1)
    token = ''
    rest = ''
    if string == '':
        pass
    elif re.search(r"^{",string):
        left = 1 
        right = 0
        for i in range(1,len(string)):
            if string[i] == '{':
                left += 1
            elif string[i] == '}':
                right += 1
            if left == right:
                token = string[0:i+1]
                rest = string[i+1:]
                break
    else:
        match = re.search(r"^(\\\W|\\[A-Za-z]+)(.*)",string)
        if match:
            token = match.group(1)
            rest = match.group(2)
        else:
            token = string[0]
            if len(string)>1:
                rest = string[1:]
    return [token,rest]

newcPat = re.compile( r"^\s*\\newcommand\*?\s*{?\s*\\(\W|[A-Za-z0-9@]+)\s*}?\s*([^%\n]*)")
renewcPat = re.compile( r"^\s*\\renewcommand\*?\s*{?\s*\\(\W|[A-Za-z0-9@]+)\s*}?\s*([^%\n]*)")
defPat = re.compile( r"^\s*\\def\s*{?\s*\\(\W|[A-Za-z0-9@]+)\s*}?\s*([^%\n]*)")
mathPat = re.compile( r"\\DeclareMathOperator\*?{?\\([A-Za-z]+)}?{((:?[^{}]*{[^}]*})*[^}]*)}" )


class macro:
    def __init__(self, line):
        self.defined = False
        self.multiline = False
        self.kill_me   = False
        
        # newcommand & renewcommand
        match = ''
        if newcPat.search(line):
            match = newcPat.search(line)
        elif renewcPat.search(line):
            match = renewcPat.search(line)

        if match:
            leftbracket = len(re.findall('{', match.group(2))) - len(re.findall(r'\\{', match.group(2)))
            rightbracket = len(re.findall('}', match.group(2))) - len(re.findall(r'\\}', match.group(2)))
            if leftbracket == rightbracket:
                if len(re.findall(r"\\newcommand(?=\W)|\\renewcommand(?=\W)|\\def(?=\W)|\\DeclareMathOperator(?=\W)", line)) > 1:
                    pass
                elif re.search(r"(\\newcommand|\\renewcommand|\\def)[^%]*\\fi\W", line):
                    pass
                elif re.search(r"@",line):
                    pass
                elif match.group(1):
                    self.name = match.group(1)
                    content = match.group(2)
                    if len(re.findall('{', content)) == 0:
                        content = '{'+content+'}'
                    match2 = re.search(r"^\s*(\[(\d)\])?\s*(\[(.*)\])?\s*{(.*)}", content)
                    if match2:
                        self.defined = True
                        if re.search(r"^{.*}$|\\begin|\\end|\\left|\\right",match2.group(5)):
                            self.definition = match2.group(5)
                        else:
                            self.definition = '{'+match2.group(5)+'}'
                        if match2.group(1):
                            self.narg = int(match2.group(2))
                            for i in range(0,self.narg):
                                if not re.search(r"#"+str(i+1),self.definition):
                                    self.defined = False
                                    break
                            if match2.group(3):
                                self.default = match2.group(4)
                            else:
                                self.default = ''
                        else:
                            self.narg = 0
                            self.default = ''
                    else:
                        self.multiline = True
            elif leftbracket > rightbracket:
                self.multiline = True
        # def
        elif defPat.search(line):
            match = defPat.search(line)
            leftbracket = len(re.findall('{', match.group(2))) - len(re.findall(r'\\{', match.group(2)))
            rightbracket = len(re.findall('}', match.group(2))) - len(re.findall(r'\\}', match.group(2)))
            if leftbracket == rightbracket:
                if len(re.findall(r"\\newcommand(?=\W)|\\renewcommand(?=\W)|\\def(?=\W)|\\DeclareMathOperator(?=\W)", line)) > 1:
                    pass
                elif re.search(r"(\\newcommand|\\renewcommand|\\def)[^%]*\\fi\W", line):
                    pass
                elif re.search(r"@",line):
                    pass
                elif match.group(1):
                    self.name = match.group(1)
                    content = match.group(2)
                    if len(re.findall('{', content)) == 0:
                        content = '{'+content+'}'
                    match2 = re.search(r"^([^{]*){(.*)}", content)
                    if match2:
                        self.defined = True
                        if re.search(r"^{.*}$|\\begin|\\end|\\left|\\right",match2.group(2)):
                            self.definition = match2.group(2)
                        else:
                            self.definition = '{'+match2.group(2)+'}'
                        if match2.group(1):
                            self.narg = len(re.findall(r"#",match2.group(1)))
                            self.default = ''
                            for i in range(0,self.narg):
                                if not re.search(r"#"+str(i+1),self.definition):
                                    self.defined = False
                                    break
                        else:
                            self.narg = 0
                            self.default = ''
                    else:
                        self.multiline = True
            elif leftbracket > rightbracket:
                self.multiline = True
        # DeclareMathOperator
        elif mathPat.search(line):
            match = mathPat.search(line)
            self.name = match.group(1)
            self.definition = '{\\operatorname{' + match.group(2) + '}}'
            self.narg = 0
            self.default = ''
            self.defined = True

    def check_already_defined(self, line):
        if re.match(r"\W", self.name):
            check = re.compile(r"(\\def|\\newcommand|\\renewcommand|\\DeclareMathOperator)[{\s]*\\\%s\W" % self.name)
        else:
            check = re.compile(r"(\\def|\\newcommand|\\renewcommand|\\DeclareMathOperator)[{\s]*\\%s\W" % self.name)
        if check.search(line):
            return True
        else:
            return False

    def match(self, line):
        if re.match(r"\W", self.name):
            mat = re.compile(r"^(.*)\\\%s(.*)" % self.name)
        else:
            mat = re.compile(r"^(.*)\\%s(?![A-Za-z0-9])(.*)" % self.name)
        return mat.search(line)

    def temp_def(self, args):
        temp = self.definition
        for i in range(0,self.narg):
            temp = temp.replace(r"#"+str(i+1),args[i])
        return temp

    def parse(self, line):
        KILL_TIME_SEC = 30
        start_time    = time.time()
        if self.check_already_defined(line):
            return [line, False]
        current = re.search(r"[^\n]*", line).group()
        match = self.match(current)
        while match:
            if time.time() - start_time > KILL_TIME_SEC:
                self.kill_me = True
                return [None, None]
            if self.narg == 0:
                current = match.group(1) + self.definition + match.group(2)
            else:
                args = []
                if not self.default:
                    rest = match.group(2)
                    for i in range(0,self.narg):
                        token = find_token(rest)
                        if not token[0]:
                            return [line, True]
                        args.append(token[0])
                        rest = token[1]
                else:
                    rest = match.group(2)
                    argmatch = re.search(r"^\s*\[([^\]])\](.*)",rest)
                    if argmatch:
                        args.append(argmatch.group(1))
                        rest = argmatch.group(2)
                    else:
                        args.append(self.default)
                    for i in range(0,self.narg-1):
                        token = find_token(rest)
                        if not token[0]:
                            return [line, True]
                        args.append(token[0])
                        rest = token[1]
                current = match.group(1) + self.temp_def(args) + rest
            match = self.match(current)
        return [current+'\n', False]

def expand_input(argv):
    inputHandler = open(argv, 'rU')
    basedir      = os.path.dirname(argv)
    contents = []
    for line in inputHandler:
        match = re.search(r"(.*)\\input{[./]*(.*?)}(.*)", line)
        if match:
            contents.append(match.group(1))
            if re.search(r"%", match.group(1)):
                pass
            else:
                inputPath = basedir + '/' + cut_extension(match.group(2),'.tex') + '.tex'
                #print "expand: " + inputPath
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
        macros = re.findall(r"\\newcommand(?=\W)|\\renewcommand(?=\W)|\\def(?=\W)|\\DeclareMathOperator(?=\W)", line)
        if len(macros) <= 1:
            temp.append(line)
        else:
            definitions = re.split(r"\\newcommand(?=\W)|\\renewcommand(?=\W)|\\def(?=\W)|\\DeclareMathOperator(?=\W)", line)
            if definitions[0]:
                temp.append(definitions[0])
            for i in range(0,len(macros)):
                if re.search(r"%",definitions[i]):
                    break
                temp.append(macros[i]+definitions[i+1]+'\n')
    contents = temp
    return contents

def graceful_kill(input, output):
    inputHandler  = open(input, 'rU')
    basedir       = os.path.dirname(input)
    outputHandler = open(output, "w")
    contents = []
    # Expand \input{} files
    for line in inputHandler:
        match = re.search(r"(.*)\\input{[./]*(.*?)}(.*)", line)
        if match:
            contents.append(match.group(1))
            if re.search(r"%", match.group(1)):
                pass
            else:
                inputPath = basedir + '/' + cut_extension(match.group(2),'.tex') + '.tex'
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

def demacro(input, output, verbose):

    KILL_TIME_SEC   = 30
    start_time      = time.time()

    contents      = expand_input(input)
    outputHandler = open(output, "w")

    macroDict = {}
    multilineFlag = False

    for line in contents:

        #print "line = {} ".format(line)
        #print "multi = {} ".format(multilineFlag)

        if re.search(r"^%",line):
            outputHandler.write(line)
            continue

        if multilineFlag:
            current = re.search(r"^([^%\n]*)",current).group() + ' ' + line
            multilineFlag = False
        else:
            current = line

        #print "current = {}".format(current)

        candidate = set(re.findall(r"\\(\W|[A-Za-z0-9]+)", current))
        for x in list(set(macroDict) & candidate):

            if time.time()-start_time > KILL_TIME_SEC:
                print "timeout1: {}".format(output)
                outputHandler.close()
                graceful_kill(input, output)
                return

            if verbose:
                print 'Demacro  -----------'
                print x
                print macroDict[x].definition
                print macroDict[x].narg
                print macroDict[x].default
                print '-----------'

            currentParsed = macroDict[x].parse(current)

            if macroDict[x].kill_me:
                print "timeout2: {}".format(output)
                outputHandler.close()
                graceful_kill(input, output)
                return

            multilineFlag = currentParsed[1]

            if multilineFlag:
                break

            current = currentParsed[0]
            if verbose:
                print "parsed: {}, multiline: {}".format(current, multilineFlag)
        if multilineFlag:
            continue

        newmacro = macro(current)
        multilineFlag = newmacro.multiline
        if multilineFlag:
            #print "multiline2: {}".format(multilineFlag)
            continue
        elif newmacro.defined:
            macroDict[newmacro.name] = newmacro
            if verbose:
                print 'New Macro -----------'
                print current
                print newmacro.name
                print newmacro.definition
                print newmacro.narg
                print '-----------'

        else:
            #print "writing now = {}".format(current)
            outputHandler.write(current)

    outputHandler.close()
    return

def gunzip_and_demacro((tarball, outDir, verbose, keep)):

    # extract files from tarball
    if verbose:
      print "extracting " + tarball

    tar      = tarfile.open(tarball)
    tar.extractall(outDir)

    # find main file
    inputFile = 'None'
    for file in filter(lambda x: '.tex' in x, tar.getnames()):
        fh = open(os.path.join(outDir,file), 'r')
        for line in fh:
            ## TODO: ignore commented lines
            if re.search('begin{document}', line):
                inputFile = os.path.join(outDir, file)
                fh.close()
                break
        fh.close()

    if inputFile == 'None':
        print 'no main file found for ' + tarball
        tar.close()
        return

    tar.close()

    fileBase   = os.path.basename(tarball.replace('.tar.gz', '') + '.tex')
    outputFile = os.path.join(outDir, fileBase)

    #print "input = {}, output = {}".format(inputFile, outputFile)

    demacro(inputFile, outputFile, verbose)
    if not keep:
      shutil.rmtree(os.path.dirname(inputFile))
    return
        

def main():

    parser   = argparse.ArgumentParser(description='expands LaTeX macros')

    # required
    parser.add_argument('inputName',  help='input file or directory')
    parser.add_argument('outputName', help='output file or directory')

    # optional
    parser.add_argument('-d', '--directory', action='store_true', help='indicates that inputFile is a directory of tarballs and outputFile is a directory')
    parser.add_argument('-v', '--verbose' , action='store_true', help='enable verbose mode')
    parser.add_argument('-k', '--keep' , action='store_true', help='keep untarred directories in output directory')

    args     = parser.parse_args()
    

    # assume directory has tarballs
    if args.directory:
        tarballs = glob.glob(args.inputName + '/*.tar.gz')
        pool     = multiprocessing.Pool(processes=4)
        pool.map(gunzip_and_demacro, zip(tarballs, repeat(args.outputName), repeat(args.verbose), repeat(args.keep)))
    else:
        demacro(args.inputName, args.outputName, args.verbose)

    return

if __name__ == "__main__":
    main()


