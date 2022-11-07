import os
import sys
import subprocess
from subprocess import Popen
import json

debug = False
numOpts = 0
options = []
directories = []
inDir = False
dirNumber = 0
log = "No file played"
invalidCommand = "Please entire a valid command. Use 'help' for a list of commands"
prompt = ">"
lastOut = ""
watched = set()
dirty = False

helpMessage = """Commands:
play [number]                       Play file [number]
playlist [start] [end]              Play files from [start] to [end]
delete [number]                     Delete file [number]
dir                                 List the available directories
playdir [number]                    Play all files in directory [number]
inspect [number]                    List the files in directory [number]
back                                Return to main listing from inspection
move [number] [dest]                Move file [number] to spot [dest]
movedir [number] [dest]             Move the file [number] to directory [dest]
movedir [start] [end] [dest]        Move files [start] to [end] to directory [dest]
mkdir                               Make a new empty directory
mkdir [start] [end]                 Make a new directory with files [start] to [end]
sub [video] [subtitle]              Make a new file with from [video] and [subtitle]
watched [number]                    Mark [number] as watched
watched [start] [end]               Mark [start] through [end] as watched
unwatched [number]                  Mark [number] as unwatched
unwatched [start] [end]             Mark [start] through [end] as unwatched
config                              Open the mpv config file
log                                 Print the log of the last play
refresh                             Refresh the index
clear                               Clears output
code                                Opens the python file
quit                                Quits program
help                                Print this help message"""

def makeIndex():
    global dirty
    stream = os.popen('dir\n')
    output = stream.readlines()
    global options
    oldOptions = options.copy()
    options = []
    for line in output:
        if line[-5:-1] in [".mkv", ".mp4"]:
            name = line[39:-1]
            options.append(name)
    stream.close()
    if not inDir:
        for title in (x for x in oldOptions if x not in options):
            watched.discard(title)
            dirty = True
       
def printIndex():
    
    for (i, title) in enumerate(options):
        buffer = "  " if (i+1) < 10 else " "
        unwatched = " " if title in watched else "*"
        number = str(i + 1)
        entry = f"{unwatched}{buffer}{number}: {title}"
        print(entry)
        
def init():
    global lastOut
    global watched
    os.system("cls")
    os.system("mode con: cols=120 lines=60")
    makeIndex()
    handleDir([])
    try:
        with open("m/watched.json", 'r') as file:
            try:
                jsonWatched = json.load(file)
                watched = set(jsonWatched)
            except: #JSON error I don't know the name of off the top of my head
                pass #give up
    except FileNotFoundError:
        pass

def getInput():
    answer = input()
    tokens = answer.strip().lower().split(' ')
    return tokens
    
def runCommand(command):
    # with Popen(command, stdout=subprocess.PIPE, errors="ignore") as process:
        # for line in process.stdout:
            # print(line)
    # process = Popen(command, stdout=subprocess.PIPE, errors="ignore")
    # for line in process.stdout:
        # print(line)
        
    return subprocess.run(command, stdout=subprocess.PIPE, errors="ignore", shell=True)
            
def runCommandOnce(command):
    Popen(command, stdout=subprocess.PIPE, errors="ignore")

def outDirList():
    toBeShown = "Directories:\n"
    for (i, dirName) in enumerate(directories):
        buffer = " " if i + 1 < 10 else ""
        entry = f"{buffer}{i+1}: {dirName}\n"
        toBeShown += entry
    return toBeShown[:-1]

def handleQuit(tokens):
    print('Goodbye!')
    quit()
    
def handleRefresh(tokens):
    global lastOut
    os.system("mode con: cols=120 lines=60")
    makeIndex()
    
def handleHelp(tokens):
    global lastOut
    lastOut = helpMessage
    
def handleLog(tokens):
    global lastOut
    lastOut = log
    
def handlePlay(tokens):
    global lastOut
    global log
    invalidChoice = "Please enter a number from 1 to " + str(len(options))
    if len(tokens) == 1:
        lastOut = invalidChoice
        return
    choice = 0
    try:
        choice = int(tokens[1])
    except ValueError:
            lastOut = invalidChoice
            return
    if not (choice >= 0 and choice <= len(options)):
        lastOut = invalidChoice
        return
    print("Press q during playback to quit...")
    title = options[choice - 1]
    
    log = runCommand(f'mpv "{title}"').stdout
    if title not in watched:
        watched.add(options[choice - 1])
        dirty = True
    lastOut = ""
    
def handleDelete(tokens):
    global lastOut
    global dirty
    invalidChoice = "Please enter a number from 1 to " + str(len(options))
    if len(tokens) == 1:
        lastOut = invalidChoice
        return
    choice = 0
    try:
        choice = int(tokens[1])
    except ValueError:
            lastOut = invalidChoice
            return
    if not (choice >= 0 and choice <= len(options)):
        lastOut = invalidChoice
        return
    
    print("Are you sure you want to delete " + ("unwatched " if options[choice - 1] not in watched else "") +"\"" + options[choice-1] + "\"?\nY to confirm: ", end = "")
    response = input()
    if response.lower() != 'y':
        lastOut = "Deletion canceled"
        return
    
    try:
        os.remove(options[choice-1])
        watched.discard(options[choice - 1])
        dirty = True
    except PermissionError:
        lastOut = "File open in another process"
        return
    except FileNotFoundError:
        lastOut = "File already deleted"
        makeIndex()
        return
    lastOut = "File deleted"
    makeIndex()
        
def handleInvalid(tokens):
    global lastOut
    lastOut = invalidCommand

def handleConfig(tokens):
    global lastOut
    appdata = os.getenv('APPDATA')
    # os.system("notepad++ %APPDATA%\mpv\mpv.conf")
    # doesn't work, env. variable invalid: 
    # runCommand("notepad++ %APPDATA%\mpv\mpv.conf")
    runCommandOnce("notepad++ " + appdata + "\\mpv\\mpv.conf")
    lastOut = "Config file opened"
    
def handleCode(tokens):
    global lastOut
    # os.system("notepad++ m\\a.py")
    runCommandOnce("notepad++ \"C:\\Users\\Ianpe\\documents\\books\\fun books\\other\\m\\a.py")
    lastOut = "Code file opened"

def handlePlaylist(tokens):
    global lastOut
    global log
    invalidChoice = "Please enter numbers from 1 to " + str(len(options))
    if len(tokens) < 3:
        lastOut = "Please enter the start and end of the playlist"
        return
    try:
        start = int(tokens[1])
        end = int(tokens[2])
    except ValueError:
        lastOut = invalidChoice
        return
    isValid = start >= 1 and start <= len(options)
    isValid2 = end >= 1 and end <= len(options)
    if not (isValid and isValid2):
        lastOut = invalidChoice
        return
    if start > end:
        lastOut = "Start must come before end"
        return
    file = open("playlist.txt", "w")
    L = [(s + "\n") for s in options[start-1:end]]
    file.writelines(L)
    file.close()
    print("Press q during playback to quit, < and > to change file...")
    log = runCommand('mpv --playlist=playlist.txt').stdout
    os.remove("playlist.txt")
    lastOut = ""
     
def handleClear(tokens):
    global lastOut
    lastOut = ""

def handleMove(tokens):
    global lastOut
    invalidChoice = "Please enter numbers from 1 to " + str(len(options))
    if len(tokens) < 3:
        lastOut = "Please enter the item and destination to move to"
        return
    try:
        start = int(tokens[1])
        end = int(tokens[2])
    except ValueError:
        lastOut = invalidChoice
        return
    isValid = start >= 1 and start <= len(options)
    isValid2 = end >= 1 and end <= len(options)
    if not (isValid and isValid2):
        lastOut = invalidChoice
        return
    if start == end:
        lastOut = "No move done"
        return
    if start < end:
        options.insert(end, options[start-1])
        options.pop(start-1)
    else:
        options.insert(end-1, options.pop(start-1))
    lastOut = ""

def handleDir(tokens):
    global lastOut
    global directories
    # global debug
    directories = []  
    # dirs = os.listdir()
    num = 1
    if not inDir:
        for entry in os.scandir():
            if entry.is_dir() and entry.name != "m":
                directories.append(entry.name)
    toBeShown = outDirList()
    lastOut = toBeShown
    debug = True
    
def handleMoveDir(tokens):
    global lastOut
    if inDir:
        lastOut = "Moving files between directories is not supported"
        return
    if len(tokens) < 3:
        lastOut = "Please enter a file and directory number"
        return
    if len(tokens) < 4:
        try:
            fileNum = int(tokens[1])
            dirNum = int(tokens[2])
        except ValueError:
            lastOut = "Please use numbers"
            return
        isValid1 = fileNum >= 1 and fileNum <= len(options)
        isValid2 = dirNum >= 1 and dirNum <= len(directories)
        if not isValid1 :
            lastOut = "Please select a file from 1 to " + len(options)
            return
        elif not isValid2:
            lastOut = "Please select a directory from 1 to " + len(directories)
            return
            
        command = "move \"" + options[fileNum - 1] + "\" \"" + directories[dirNum - 1] + "\""
        # lastOut = command
        result = runCommand(command)
        if result.returncode != 0:
            lastOut = "Error, oops!"
        else:
            lastOut = "Moved " + options[fileNum - 1] + " to " + directories[dirNum - 1]
    else:
        try:
            fileNum1 = int(tokens[1])
            fileNum2 = int(tokens[2])
            dirNum = int(tokens[3])
        except ValueError:
            lastOut = "Please use numbers"
            return
        isValid1 = fileNum1 >= 1 and fileNum1 <= len(options)
        isValid2 = fileNum2 >= 1 and fileNum2 <= len(options)
        isValid3 = dirNum >= 1 and dirNum <= len(directories)
        if not isValid1 :
            lastOut = "Please select a file from 1 to " + len(options)
            return
        elif not isValid2:
            lastOut = "Please select a file from 1 to " + len(options)
            return
        elif not isValid3:
            lastOut = "Please select a directory from 1 to " + len(directories)
            return
        if fileNum2 < fileNum1:
            fileNum1, fileNum2 = fileNum2, fileNum1
        completed = True
        for i in range(fileNum1, fileNum2 + 1):
            command = "move \"" + options[i - 1] + "\" \"" + directories[dirNum - 1] + "\""
            result = runCommand(command)
            if result.returncode != 0:
                lastOut = "encountered an error, quitting"
                completed = False
                break
        if completed:
            lastOut = "Moved " + str(fileNum2 - fileNum1 + 1) + " files to " + directories[dirNum - 1]
    makeIndex()
            
def handlemkDir(tokens):
    global lastOut
    # no args
    if inDir:
        lastOut = "Operation not supported in inspect mode"
        return
    if len(tokens) < 3:
        print("Making a new empty directory")
        name = input("Name for new directory: ")
        os.system("mkdir \"" + name + "\"")
        lastOut = "Directory '" + name + "' created"
    else:
        invalidChoice = "Please enter numbers from 1 to " + str(len(options))
        try:
            start = int(tokens[1])
            end = int(tokens[2])
        except ValueError:
            lastOut = invalidChoice
            return
        isValid = start >= 1 and start <= len(options)
        isValid2 = end >= 1 and end <= len(options)
        if not (isValid and isValid2):
            lastOut = invalidChoice
            return
        if start > end:
            start, end = end, start
        print("Making a new directory from files " + str(start) + " to " + str(end))
        name = input("Name for new directory: ")
        os.system("mkdir \"" + name + "\"")
        completed = True
        for i in range(start, end + 1):
            command = "move \"" + options[i - 1] + "\" \"" + name + "\""
            result = runCommand(command)
            if result.returncode != 0:
                lastOut = "Encountered an error, quitting"
                completed = False
                break
        if completed:
            lastOut = "Directory '" + name + "' created"
    makeIndex()
    handleDir(tokens)
            
def handlePlayDir(tokens):
    global lastOut
    global log
    global debug
    # debug = True
    if inDir:
        lastOut = "Please use 'back' first, until functionality is added"
        return
    if len(tokens) < 2:
        lastOut = "Specify a directory. Use 'dir' for a list of directories"
        return
    try:
        choice = int(tokens[1])
    except:
        lastOut = "Please enter a number, 1 to " + len(directories)
        return
    try:
        os.chdir("" + directories[choice - 1])
    except:
        lastOut = "Invalid directory, somehow. Use 'dir' to update directories"
        return
        
    
    file = open("playlist.txt", "w")
    L = [(s.name + "\n") for s in os.scandir()]
    file.writelines(L)
    file.close()
    print("Press q during playback to quit, < and > to change file...")
    # stream = subprocess.Popen('mpv --playlist=playlist.txt', stdout=subprocess.PIPE, encoding="cp850", errors="ignore")
    # maybe get this to work some day? not sure what the problem is
    # stream = os.popen('mpv --playlist=playlist.txt')
    log = runCommand('mpv --playlist=playlist.txt').stdout
    lastOut = ""
    # try: 
        # log = stream.read()
    # except UnicodeDecodeError: 
        # lastOut = "Error in reading log"
    os.remove("playlist.txt")
    os.chdir("..")
    
def handleInspect(tokens):
    global lastOut
    global inDir
    if len(tokens) < 2:
        lastOut = "Specify a directory. Use 'dir' for a list of directories."
        return
    try:
        choice = int(tokens[1])
    except:
        lastOut = "Please enter a number, 1 to " + len(directories)
        return
    try:
        os.chdir("" + directories[choice - 1])
    except:
        lastOut = "Invalid directory, somehow. Use 'dir' to update directories."
        return
    inDir = True
    makeIndex()
    dirNumber = choice - 1
    lastOut = "Inspecting directory '" + directories[choice - 1] + "'"

def handleBack(tokens):
    global lastOut
    global inDir
    if not inDir:
        return
    os.chdir("..")
    makeIndex()
    inDir = False
    lastOut = outDirList()

def handleDirectories(tokens):
    global lastOut
    lastOut = str(directories)

def handleSub(tokens):
    global lastOut
    global log
    if len(tokens) < 3:
        lastOut = "Please specify a video file and a subtitle file."
        return
    try:
        vidfile = int(tokens[1])
        subfile = int(tokens[2])
    except:
        lastOut = "Please enter a number, 1 to " + len(options)
        return
    newfilename = input("Name for new file: ")
    with open("SubtitleOptions.json", 'r') as file:
        optionsString = file.read()
    optionsString = optionsString.replace("XX", newfilename)
    optionsString = optionsString.replace("YY", options[vidfile-1])
    optionsString = optionsString.replace("ZZ", options[subfile-1])
    with open("DoingSubtitle.json", 'w') as file:
        file.write(optionsString)
    print("Processing...")
    log = runCommand("mkvmerge @DoingSubtitle.json").stdout
    os.remove("DoingSubtitle.json")
    lastOut = "Made new file"
    makeIndex()

def handleWatched(tokens):
    global lastOut
    global dirty
    invalidChoice = "Please enter a number from 1 to " + str(len(options))
    if len(tokens) == 1:
        lastOut = invalidChoice
        return
    choiceA, choiceB = 0, 0
    try:
        choiceA = int(tokens[1])
        if len(tokens) >= 3:
            choiceB = int(tokens[2])
    except ValueError:
        lastOut = invalidChoice
        return
    if not (choiceA >= 0 and choiceA <= len(options)):
        lastOut = invalidChoice
        return
    if not (choiceB >= 0 and choiceB <= len(options)):
        lastOut = invalidChoice
        return
    if len(tokens) == 2:
        title = options[choiceA - 1]
        watched.add(title)
        lastOut = f"Watched {title}"
    else:
        if choiceA > choiceB:
            choiceA, choiceB = choiceB, choiceA
        for i in range(choiceA, choiceB + 1):
            watched.add(options[i - 1])
        lastOut = f"Watched {choiceB - choiceA + 1} files"
    dirty = True
    
def handleUnwatched(tokens):
    global lastOut
    global dirty
    invalidChoice = "Please enter a number from 1 to " + str(len(options))
    if len(tokens) == 1:
        lastOut = invalidChoice
        return
    choiceA, choiceB = 0, 0
    try:
        choiceA = int(tokens[1])
        if len(tokens) >= 3:
            choiceB = int(tokens[2])
    except ValueError:
        lastOut = invalidChoice
        return
    if not (choiceA >= 0 and choiceA <= len(options)):
        lastOut = invalidChoice
        return
    if not (choiceB >= 0 and choiceB <= len(options)):
        lastOut = invalidChoice
        return
    if len(tokens) == 2:
        watched.discard(options[choiceA - 1])
        lastOut = f"Unwatched {options[choiceA - 1]}"
    else:
        if choiceA > choiceB:
            choiceA, choiceB = choiceB, choiceA
        for i in range(choiceA, choiceB + 1):
            watched.discard(options[i - 1])
        lastOut = f"Unwatched {choiceB - choiceA + 1} files"
    dirty = True
   

def printScreen():
    os.system("cls")
    print("Files:")
    printIndex()
    print()
    print(lastOut)
    print()
    print(prompt, end = '')

handlers = {"quit":handleQuit,
            "help":handleHelp,
            "log":handleLog,
            "refresh":handleRefresh,
            "play":handlePlay,
            "delete":handleDelete,
            "config":handleConfig,
            "playlist":handlePlaylist,
            "clear":handleClear,
            "move":handleMove,
            "dir":handleDir,
            "playdir":handlePlayDir,
            "code":handleCode,
            "inspect":handleInspect,
            "back":handleBack,
            "mkdir":handlemkDir,
            "directories":handleDirectories,
            "movedir":handleMoveDir,
            "sub":handleSub,
            "watched":handleWatched,
            "unwatched":handleUnwatched}

def mainLoop():
    global debug
    while True:
        printScreen()
        if debug:
            print(directories)
            debug = False
        if dirty and not inDir:
            with open("m\watched.json", 'w') as file:
                json.dump(list(watched), file)
        tokens = getInput()
        if (len(tokens) == 0):
            continue
        handlers.get(tokens[0], handleInvalid)(tokens)
        
if __name__ == "__main__":
    init()
    mainLoop()