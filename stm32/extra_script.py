Import('env')
from base64 import b64decode

#
# Dump build environment (for debug)
# print env.Dump()
#

print "Running extra_script.py"

env.Append(UPLOADCMD='bash upload.sh $SOURCES')

# uncomment line below to see environment variables
# print ARGUMENTS
