#!/usr/bin/python

"""
Copyright (c) 2010, John Burwell
All rights reserved.

Redistribution and use in source and binary forms, with or without 
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the John Burwell nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE 
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
POSSIBILITY OF SUCH DAMAGE.
"""

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

    """
    Configures logging for the utility.  Log are captured in a file named
    <process_id>.log -- allowing correlation of log information to actual runs of
    the utility. Normally, error and information messages are sent to the log file
    while error messages are sent to the console.   In verbose mode, error, information,
    and debug messages are sent to the log file, and error messages are sent to the
    console.
    """

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

    """
    Creates the context used through the utility based on the command line
    parameters passed.  If the command line arguments fail to validate then the
    appliction will abend and display a standard usage message.
    """

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

    if is_blank(aContext.getSearchPath()) == True:

       aParser.error ("A search path is required")

    elif os.path.exists(aContext.getSearchPath()) == False:

       aParser.error("Search path " + aContext.getSearchPath() + " does not exist.")

    if aContext.getSearchText()  == None:

       aParser.error("Search text must be specified")

    if aContext.getReplacementText() == None:

       aParser.error("Replacement text must be specified")

    if aContext.getSearchText() == aContext.getReplacementText():

       aParser.error("The search and replacement text must differ")

    return aContext

class Context(object):

    """
    The value object containing runtime context for the utility.  A class is
    preferred over a tuple or passing flags around in order to gain expressiveness
    and extensibility without breaking internal contracts.

    All executions of the utility create a unique process id in order to
    provide a correlation identifier and distinguish logs and backup files for
    individual execution runs.
    """

    def __init__(self, aVerboseFlag, aBackupFlag, aSearchPath, theSearchText, theReplacementText):

        self.myProcessId = datetime.now().strftime('%m%d%Y-%H%M%S')
        self.myVerboseFlag = aVerboseFlag
        self.myBackupFlag = aBackupFlag
        self.mySearchPath = aSearchPath
        self.mySearchText = theSearchText
        self.myReplacementText = theReplacementText

    def getProcessId(self):

        """
        Accessor for the current process ID.
        """

        return self.myProcessId

    def isVerbose(self):

        """
        Accessor for the flag indicating whether or not execution is verbose.
        """

        return self.myVerboseFlag

    def performBackup(self):

        """
        Accessor indicating whether or not a backup files should be created.
        """

        return self.myBackupFlag

    def getSearchPath(self):
        
        """
        Accessor for the current search path.
        """

        return self.mySearchPath

    def getSearchText(self):

        """
        Accessor for the current search text.
        """
        return self.mySearchText

    def getReplacementText(self):

        """
        Accessor for the current replacement text.
        """
        return self.myReplacementText

    def __str__(self):

        return "Context: processId=" + self.myProcessId + \
            " verbose=" + str(self.myVerboseFlag) + \
            " backup=" + str(self.myBackupFlag) + \
            " rootDirectory=" + str(self.mySearchPath) + \
            " findText=" + str(self.mySearchText) + \
            " replacementText=" + str(self.myReplacementText)

class TextReplacer:

    """
    Replaces all occurences of a whole word in a directory of files.  It ignores
    backup files created by this utility, and will optionally, create backups of
    files.
    """

    def __init__(self, aContext):

        # Backup files for a particular run of the utility will not clober
        # backups from previous runs ...
        self.myBackupExt = aContext.performBackup() and "." + \
            aContext.getProcessId() + "." + BACKUP_EXT_SUFFIX or None

        # Match words respecting punctionation
        anExpression = "\\b" + aContext.getSearchText() + "\\b"
        self.myFindExpression = re.compile(anExpression)
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

def main():

    # Spin up the execution context.  It is outside the try block because it
    # has its own error handling and exit procedure ...
    aContext = create_context()

    try:

        # Spin up the logging framework and recording the initial state --
        # placing the process id the log to support diagnostic efforts ...
        configure_logging(aContext)

        logging.info('Started text replacement process %s with configuration %s', 
            aContext.getProcessId(), aContext)

        # Recursively walk the search path and replace occurences of the passed
        # search text in each file using a TextReplacer instance ...
        os.path.walk(aContext.getSearchPath(), 
            lambda theArguments, aDirectoryName, theFileNames :
                TextReplacer(aContext).replace(aDirectoryName, theFileNames), 
            None)

        logging.info("Completed replacement operation.")
        return 0

    except:

        logging.exception("An error occurred during the replacement operation")

        return 2 

if __name__ == "__main__":
    sys.exit(main())
