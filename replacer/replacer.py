#!/usr/bin/python

import fileinput
import logging
import os
import os.path
import re
import sys

from datetime import datetime
from optparse import OptionParser

def configure_logging(aProcessId, verbose):

    # Configure the logger based on the verbose option.  All logging goes to
    # console by default ...
    aLogLevel = logging.INFO
    if verbose == True:
        aLogLevel = logging.DEBUG

    aLogFile = aProcessId + '-replacement.log'
    logging.basicConfig(level=verbose and logging.DEBUG or logging.INFO,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        filename=aLogFile,
                        filemode='w')

    #TODO Configure console logging for errors
    aConsoleHandler = logging.StreamHandler();
    aConsoleHandler.setLevel(verbose and logging.INFO or logging.ERROR)
    aConsoleHandler.setFormatter(logging.Formatter('%(message)s'))

    logging.getLogger('').addHandler(aConsoleHandler)

class TextReplacer:

    def __init__(self, aProcessId, aBackupFlag, theFindText,
    theReplacementText):

        self.myProcessId = aProcessId
        self.myBackupExt = aBackupFlag and "." + aProcessId + ".bak" or None

        # Match whole word by checking before the phase -- not after.  This
        # approacj prevents the last words of sentences from getting missed
        self.myFindExpression = re.compile(r"\b" + theFindText)
        self.myReplacementText = theReplacementText

    def replace(self, aDirectoryName, theFileNames):

        logging.debug("Visting directory %s", aDirectoryName)

        # Create fully quailified paths -- ensuring we do append a redundant OS
        # separator as we build the path ...
        theFiles = map(aDirectoryName.endswith(os.sep) and
                        (lambda aFileName: aDirectoryName + aFileName) or
                        (lambda aFileName: aDirectoryName + os.sep + aFileName),
                      theFileNames)
        logging.debug("Scanning through %s", theFiles)

        # TODO Support backups ...
        for aLine in fileinput.input(theFiles, inplace=1, backup=self.myBackupExt):

            # Perform the replacement and write out the results.
            aProcessedLine = self.myFindExpression.sub(self.myReplacementText, aLine)
            sys.stdout.write(aProcessedLine)

            # Log changes
            if aLine != aProcessedLine:

                logging.info("Replaced line '%s' with '%s' in %s", aLine.replace(os.linesep, ""),
                        aProcessedLine.replace(os.linesep, ""), fileinput.filename())

def main():

    # Configure the  option parser to extract and control command line parsing
    aParser = OptionParser(usage="usage: %prog [options] search_path search_text replacement_text")
    aParser.add_option("-b", "--backup", dest="backup", action="store_true", 
                       default=False, help="backup files before modification")
    aParser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                       default=False, help="print additional diagnostics information regarding the utility's operation")

    # Parse out the comand line options and arguments
    (theOptions, theArguments) = aParser.parse_args()
    aParser.destroy()

    aProcessId = datetime.now().strftime('%m%d%Y-%H%M%S')

    configure_logging(aProcessId, theOptions.verbose)

    # TODO Validate that the directory exists

    logging.info('Started text replacement process %s with options %s on search path %s to replace %s with %s', 
        aProcessId, theOptions, theArguments[0], theArguments[1], theArguments[2])

    aTextReplacer = TextReplacer(aProcessId, theOptions.backup, theArguments[1], theArguments[2])

    os.path.walk(theArguments[0], 
                 lambda theArguments, aDirectoryName, theFileNames : aTextReplacer.replace(aDirectoryName, theFileNames),
                 None)


if __name__ == "__main__":
    sys.exit(main())
