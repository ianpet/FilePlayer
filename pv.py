import os
import sys

os.popen("cd ..")
stream = os.popen('dir\n')
output = stream.readlines()
numOpts = len(output) - 10
if len(sys.argv) == 1:
    print("Please select a number from 1 to " + str(numOpts))
    quit()
try:
    choiceNum = int(sys.argv[1])
except ValueError:
    print("Not a number")
    quit()
if choiceNum > numOpts:
    print("Number too large, max " + str(numOpts))
    quit()
choice = output[choiceNum + 7][39:-1]
os.system('mpv "' + choice + '"')