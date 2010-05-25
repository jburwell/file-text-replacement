#!/usr/bin/python

import fileinput
import logging
import os
import os.path
import re
import sys

from datetime import datetime
from optparse import OptionParser, OptionError
from timeit import Timer

BACKUP_EXT_SUFFIX = "rbak"

safe_get = lambda aList, anIndex : anIndex < len(aList) and aList[anIndex] or None

def is_blank(aString):

    if aString != None and len(aString.strip()) > 0:

        return False

    return True

def configure_logging(aContext):

    logging.basicConfig(level=aContext.isVerbose() and logging.DEBUG or logging.INFO,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        filename=aContext.getProcessId() + '-replacement.log',
                        filemode='w')

    aConsoleHandler = logging.StreamHandler();
    aConsoleHandler.setLevel(logging.ERROR)
    aConsoleHandler.setFormatter(logging.Formatter('%(message)s'))

    logging.getLogger('').addHandler(aConsoleHandler)

def create_context():

    # Configure the  option parser to extract and control command line parsing
    aParser = OptionParser(usage="usage: %prog [options] search_path search_text replacement_text")
    aParser.add_option("-b", "--backup", dest="backup", action="store_true",
           default=False, help="backup a file before modification in form of <filename>.<process_id>." + BACKUP_EXT_SUFFIX)
    aParser.add_option("-v", "--verbose", dest="verbose", action="store_true",
           default=False, help="print additional diagnostic information")

    # Parse out the comand line options and arguments
    (theOptions, theArguments) = aParser.parse_args()

    aContext = Context(theOptions.verbose, theOptions.backup,
                   safe_get(theArguments, 0),
                   safe_get(theArguments, 1),
                   safe_get(theArguments, 2))

    if is_blank(aContext.getRootDirectory()) == True:

       aParser.error ("A search path is required")

    elif os.path.exists(aContext.getRootDirectory()) == False:

            aParser.error("Search path " + aContext.getRootDirectory() + " does not exist.")

    if aContext.getFindText()  == None:

        aParser.error("Search text must be specified")

    if aContext.getReplacementText() == None:

        aParser.error("Replacement text must be specified")

    if aContext.getFindText() == aContext.getReplacementText():

        aParser.error("The search and replacement text must differ")

    return aContext

class Context(object):

    def __init__(self, aVerboseFlag, aBackupFlag, aRootDirectory, theFindText, theReplacementText):

        self.myProcessId = datetime.now().strftime('%m%d%Y-%H%M%S')
        self.myVerboseFlag = aVerboseFlag
        self.myBackupFlag = aBackupFlag
        self.myRootDirectory = aRootDirectory
        self.myFindText = theFindText
        self.myReplacementText = theReplacementText

    def getProcessId(self):

        return self.myProcessId

    def isVerbose(self):

        return self.myVerboseFlag

    def performBackup(self):

        return self.myBackupFlag

    def getRootDirectory(self):

        return self.myRootDirectory

    def getFindText(self):

        return self.myFindText

    def getReplacementText(self):

        return self.myReplacementText

    def __str__(self):

        return "Context: processId=" + self.myProcessId + \
            " verbose=" + str(self.myVerboseFlag) + \
            " backup=" + str(self.myBackupFlag) + \
            " rootDirectory=" + str(self.myRootDirectory) + \
            " findText=" + str(self.myFindText) + \
            " replacementText=" + str(self.myReplacementText)

class TextReplacer:

    def __init__(self, aContext):

        self.myBackupExt = aContext.performBackup() and "." + \
            aContext.getProcessId() + "." + BACKUP_EXT_SUFFIX or None

        # Match whole word by checking before the phase -- not after.  This
        # approacj prevents the last words of sentences from getting missed
        self.myFindExpression = re.compile(r"\b" + aContext.getFindText())
        self.myReplacementText = aContext.getReplacementText()

    def replace(self, aDirectoryName, theFileNames):

        logging.debug("Visting directory %s", aDirectoryName)

        # Create fully quailified paths -- ensuring we do append a redundant OS
        # separator as we build the path and skipping over previously created
        # backup files ...
        theFiles = filter(lambda aFileName: not aFileName.endswith(BACKUP_EXT_SUFFIX),
                        map(aDirectoryName.endswith(os.sep) and
                            (lambda aFileName: aDirectoryName + aFileName) or
                            (lambda aFileName: aDirectoryName + os.sep + aFileName),
                        theFileNames))
        logging.debug("Scanning through %s", theFiles)

        for aLine in fileinput.input(theFiles, inplace=1, backup=self.myBackupExt):

            # Perform the replacement and write out the results.
            aProcessedLine = self.myFindExpression.sub(self.myReplacementText, aLine)
            sys.stdout.write(aProcessedLine)

            # Log changes
            if aLine != aProcessedLine:

                logging.info("Replaced line '%s' with '%s' in %s", aLine.replace(os.linesep, ""),
                        aProcessedLine.replace(os.linesep, ""), fileinput.filename())

class Usage(Exception):

    def __init__(self, theMessages):

        self.msg = (len(theMessages) > 0) and (lambda :
os.linesep.join(theMessages)) or ""


def main():


    aContext = create_context()

    try:

        configure_logging(aContext)

        logging.info('Started text replacement process %s with configuration %s', 
            aContext.getProcessId(), aContext)


        aTextReplacer = TextReplacer(aContext)

        os.path.walk(aContext.getRootDirectory(), 
            lambda theArguments, aDirectoryName, theFileNames : aTextReplacer.replace(aDirectoryName, theFileNames), 
            None)

    except:

        logging.exception("An error occurred during the replacement operation")
        return 2 

    else:

        logging.info("Completed replacement operation.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
