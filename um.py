import os
import sys

os.popen("cd ..")
stream = os.popen('dir\n')
output = stream.readlines()
numOpts = len(output) - 10
for i in range(8, numOpts + 8):
    if i - 7 >= 10:
        print(str(i - 7) + ": " + output[i][39:-1])
    else:
        print("0" + str(i - 7) + ": " + output[i][39:-1])