#!/usr/bin/python

import fileinput
import logging
import os
import os.path
import re
import sys

from datetime import datetime
from optparse import OptionParser

BACKUP_EXT_SUFFIX = "rbak"

def is_blank(aString):

    if aString != None and len(aString.strip()) > 0:

        return False

    return True

def configure_logging(aContext):

    aLogFile = aContext.getProcessId() + '-replacement.log'
    logging.basicConfig(level=aContext.isVerbose() and logging.DEBUG or logging.INFO,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        filename=aLogFile,
                        filemode='w')

    aConsoleHandler = logging.StreamHandler();
    aConsoleHandler.setLevel(aContext.isVerbose() and logging.INFO or logging.ERROR)
    aConsoleHandler.setFormatter(logging.Formatter('%(message)s'))

    logging.getLogger('').addHandler(aConsoleHandler)

safe_get = lambda aList, anIndex : anIndex < len(aList) and aList[anIndex] or None

def create_context():

    # Configure the  option parser to extract and control command line parsing
    aParser = OptionParser(usage="usage: %prog [options] search_path search_text replacement_text")
    aParser.add_option("-b", "--backup", dest="backup", action="store_true", 
                       default=False, help="backup a file before modification in form of <filename>.<process_id>." + BACKUP_EXT_SUFFIX)
    aParser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                       default=False, help="print additional diagnostic information regarding the utility's operation")

    # Parse out the comand line options and arguments
    (theOptions, theArguments) = aParser.parse_args()

    aParser.destroy()

    return Context(theOptions.verbose, theOptions.backup,
                   safe_get(theArguments, 0),
                   safe_get(theArguments, 1),
                   safe_get(theArguments, 2))

class Context(object):

    def __init__(self, aVerboseFlag, aBackupFlag, aRootDirectory,
theFindText, theReplacementText):

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

    def validate(self):

        theMessages =  [];

        if is_blank(self.myRootDirectory) == True:

            theMessages.append("A search path is required")

        else:

            if os.path.exists(self.myRootDirectory) == False:

                theMessages.append("Search path " + self.myRootDirectory + " does not exist.")

        if self.myFindText  == None:

            theMessages.append("Search text must be specified")

        if self.myReplacementText == None:

            theMessages.append("Replacement text must be specified")

        if self.myFindText == self.myReplacementText:

            theMessages.append("The search and replacement text must differ")

        return theMessages

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
        # separator as we build the path ...
        theFiles = filter(lambda aFileName: not aFileName.endswith(BACKUP_EXT_SUFFIX), theFileNames)
        theFiles = map(aDirectoryName.endswith(os.sep) and
                        (lambda aFileName: aDirectoryName + aFileName) or
                        (lambda aFileName: aDirectoryName + os.sep + aFileName),
                      theFiles)
        logging.debug("Scanning through %s", theFiles)

        for aLine in fileinput.input(theFiles, inplace=1, backup=self.myBackupExt):

            # Perform the replacement and write out the results.
            aProcessedLine = self.myFindExpression.sub(self.myReplacementText, aLine)
            sys.stdout.write(aProcessedLine)

            # Log changes
            if aLine != aProcessedLine:

                logging.info("Replaced line '%s' with '%s' in %s", aLine.replace(os.linesep, ""),
                        aProcessedLine.replace(os.linesep, ""), fileinput.filename())

def main():

    aContext = create_context()

    configure_logging(aContext)

    logging.info('Started text replacement process %s with configuration %s', 
        aContext.getProcessId(), aContext)

    theMessages = aContext.validate()

    if len(theMessages) > 0:

        for aMessage in theMessages:

            logging.error(aMessage)

        return 1

    aTextReplacer = TextReplacer(aContext)

    # TODO Add timing

    os.path.walk(aContext.getRootDirectory(),
                 lambda theArguments, aDirectoryName, theFileNames : aTextReplacer.replace(aDirectoryName, theFileNames),
                 None)

    # TODO Add a completion message

if __name__ == "__main__":
    sys.exit(main())
