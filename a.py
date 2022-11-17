import os
import sys
import subprocess
from subprocess import Popen
import json
import multiprocessing


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
moved [number]                      Mark [number] as having moved directories
config                              Open the mpv config file
log                                 Print the log of the last play
refresh                             Refresh the index
clear                               Clears output
code                                Opens the python file
quit                                Quits program
help                                Print this help message"""

def makeIndex(switch=False):
    global dirty
    stream = os.popen('dir\n')
    output = stream.readlines()
    global options
    oldOptions = options.copy()
    options = []
    for line in output:
        if line[-5:-1] in {".mkv", ".mp4"}:
            name = line[39:-1]
            options.append(name)
    stream.close()
    if not (inDir or switch):
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
    return subprocess.Popen(command, stdout=subprocess.PIPE, errors="ignore", shell=True)

# TODO: merge these functionalities properly    
    
def runCommandOnce(command):
    Popen(command, stdout=subprocess.PIPE, errors="ignore")

def outDirList():
    toBeShown = "Directories:\n"
    for (i, dirName) in enumerate(directories):
        buffer = "   " if i + 1 < 10 else "  "
        entry = f"{buffer}{i+1}: {dirName}\n"
        toBeShown += entry
    return toBeShown[:-1]

def inquirePlaying(finishPlaying, sender, inDir):
    playingFile = ""
    pathToSocat = "C:\\Users\\ianpe\\Documents\\Books\\Fun` Books\\Other\\m\\socat.ps1"
    socket = "\\\\.\\pipe\\mpvsocket"
    message = '{ "command": [\\"get_property\\", \\"path\\"] }'
    command = f'powershell "{pathToSocat}" {socket} \'{message}\''
    while not finishPlaying.is_set():
        proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            sender.send(playingFile)
            return
        if proc.returncode == 0:
            outs = proc.stdout.read()
            try:
                playingFile = json.loads(outs.decode("utf-8"))["data"]
            except KeyError:
                print("Error in decoding JSON response:")
                print(outs)
                sender.send(playingFile)
        else:
            print(proc.stdout.read().decode("utf-8"))
        finishPlaying.wait(10)
    sender.send(playingFile)

def verifyFileNumber(numString):
    try:
        num = int(numString)
    except ValueError:
        return None
    if not (1 <= num <= len(options)):
        return None
    return num

def verifyDirNumber(numString):
    try:
        num = int(numString)
    except ValueError:
        return None
    if not (1 <= num <= len(directories)):
        return None
    return num

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
    global dirty
    invalidChoice = "Please enter a number from 1 to " + str(len(options))
    if len(tokens) == 1:
        lastOut = invalidChoice
        return
    choice = verifyFileNumber(tokens[1])
    if choice is None:
        lastOut = invalidChoice
        return
    
    print("Press q during playback to quit...")
    title = options[choice - 1]
   
    proc = runCommand(f'mpv "{title}"')
    proc.wait()
    log = f"Playing file: {options[choice - 1]}\n{proc.stdout.read()}"
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
    choice = verifyFileNumber(tokens[1])
    if choice is None:
        lastOut = invalidChoice
        return
        
    print(f'Are you sure you want to delete {"unwatched" if options[choice - 1] not in watched else ""} "{options[choice-1]}"?\nY to confirm: ', end = "")
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
    runCommandOnce(f"notepad++ {appdata}\\mpv\\mpv.conf")
    lastOut = "Config file opened"
    
def handleCode(tokens):
    global lastOut
    runCommandOnce("notepad++ \"C:\\Users\\Ianpe\\documents\\books\\fun books\\other\\m\\a.py")
    lastOut = "Code file opened"

def handlePlaylist(tokens):
    global lastOut
    global log
    global filePlaying
    global dirty
    
    invalidChoice = "Please enter numbers from 1 to " + str(len(options))
    if len(tokens) < 3:
        lastOut = "Please enter the start and end of the playlist"
        return
    start, end = verifyFileNumber(tokens[1]), verifyFileNumber(tokens[2])
    if start is None or end is None:
        lastOut = invalidChoice
        return
    if start > end:
        print("Playing from lower choice")
        start, end = end, start

    L = [(s + "\n") for s in options[start-1:end]]
    with open("playlist.txt", "w") as file:
        file.writelines(L)
    file.close()

    print("Press q during playback to quit, < and > to change file...")
    
    # hell    
    finishPlaying = multiprocessing.Event()
    sender, receiver = multiprocessing.Pipe()
    inquireProcess = multiprocessing.Process(target=inquirePlaying, args=(finishPlaying, sender, inDir))
    inquireProcess.start()
    
    mpvProcess = runCommand('mpv --playlist=playlist.txt --input-ipc-server=.\\pipe\\mpvsocket')
    mpvProcess.wait()
    log = mpvProcess.stdout.read()
    
    finishPlaying.set()
    filePlaying = receiver.recv()
    receiver.close()
    log += f"\nLast played file: {filePlaying}"
    lastOut = ""
    if filePlaying != "":
        for played in options[start-1:end]:
            watched.add(played)
            if played == filePlaying:
                break
    dirty = True
    os.remove("playlist.txt")
    
    
     
def handleClear(tokens):
    global lastOut
    lastOut = ""

def handleMove(tokens):
    global lastOut
    invalidChoice = "Please enter numbers from 1 to " + str(len(options))
    if len(tokens) < 3:
        lastOut = "Please enter the item and destination to move to"
        return
    start, end = verifyFileNumber(tokens[1]), verifyFileNumber(tokens[2])
    if start is None or end is None:
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
    num = 1
    if not inDir:
        directories = []  
        for entry in os.scandir():
            if entry.is_dir() and entry.name != "m":
                directories.append(entry.name)
    toBeShown = outDirList()
    lastOut = toBeShown
    
def handleMoveDir(tokens):
    global lastOut
    if inDir:
        lastOut = "Moving files between directories is not supported"
        return
    if len(tokens) < 3:
        lastOut = "Please enter a file and directory number"
        return
    if len(tokens) < 4:
        fileNum, dirNum = verifyFileNumber(tokens[1]), verifyDirNumber(tokens[2])
        if fileNum is None:
            lastOut = f"Please select a file from 1 to {len(options)}"
            return
        if dirNum is None:
            lastOut = f"Please select a directory from 1 to {len(directories)}"
            return
            
        command = "move \"" + options[fileNum - 1] + "\" \"" + directories[dirNum - 1] + "\""
        result = runCommand(command)
        result.wait()
        if result.returncode != 0:
            lastOut = "Error, oops!"
        else:
            lastOut = "Moved " + options[fileNum - 1] + " to " + directories[dirNum - 1]
    else:
        fileNum1, fileNum2, dirNum = verifyFileNumber(tokens[1]), verifyFileNumber(tokens[2]), verifyDirNumber(tokens[3])
        if fileNum1 is None or fileNum2 is None:
            lastOut = f"Please select a file from 1 to {len(options)}"
            return
        if dirNum is None:
            lastOut = f"Please select a directory from 1 to {len(directories)}"
            return
        if fileNum2 < fileNum1:
            fileNum1, fileNum2 = fileNum2, fileNum1
        completed = True
        for i in range(fileNum1, fileNum2 + 1):
            command = "move \"" + options[i - 1] + "\" \"" + directories[dirNum - 1] + "\""
            result = runCommand(command)
            result.wait()
            if result.returncode != 0:
                lastOut = "encountered an error, quitting"
                completed = False
                break
        if completed:
            lastOut = "Moved " + str(fileNum2 - fileNum1 + 1) + " files to " + directories[dirNum - 1]
    makeIndex()
            
def handlemkDir(tokens):
    global lastOut
    
    if inDir:
        lastOut = "Operation not supported in inspect mode"
        return
    watchedFiles = set()
    if len(tokens) < 3:
        print("Making a new empty directory")
        name = input("Name for new directory: ")
        os.system("mkdir \"" + name + "\"")
        lastOut = "Directory '" + name + "' created"
    else:
        invalidChoice = "Please enter numbers from 1 to " + str(len(options))
        start, end = verifyFileNumber(tokens[1]), verifyFileNumber(tokens[2])
        if start is None or end is None:
            lastOut = invalidChoice
            return
        if start > end:
            start, end = end, start
        print("Making a new directory from files " + str(start) + " to " + str(end))
        name = input("Name for new directory: ")
        os.system(f'mkdir "{name}"')
        completed = True
        for i in range(start, end + 1):
            fileName = options[i-1]
            if fileName in watched:
                watchedFiles.add(fileName)
            command = f'move "{fileName}" "{name}"'
            result = runCommand(command)
            result.wait()
            if result.returncode != 0:
                lastOut = "Encountered an error, quitting"
                completed = False
                break
        if completed:
            lastOut = f'Directory "{name}" created'
    makeIndex()
    watched.update(watchedFiles)
    handleDir(tokens)
            
def handlePlayDir(tokens):
    global lastOut
    global log
    global inDir
    
    if inDir:
        lastOut = "Please use 'back' first, until functionality is added"
        return
    if len(tokens) < 2:
        lastOut = "Specify a directory. Use 'dir' for a list of directories"
        return
    
    choice = verifyDirNumber(tokens[1])
    if choice is None:
        lastOut = f"Please select a directory from 1 to {len(directories)}"
        return
    try:
        os.chdir(directories[choice - 1])
    except:
        lastOut = "Invalid directory, somehow. Use 'dir' to update directories"
        return
        
    inDir = True
    makeIndex()
    handlePlaylist((None, 1, len(options)))
    os.chdir("..")
    inDir = False
    makeIndex(True)
    return
    
def handleInspect(tokens):
    global lastOut
    global inDir
    global dirNumber
    if len(tokens) < 2:
        lastOut = "Specify a directory. Use 'dir' for a list of directories."
        return
    choice = verifyDirNumber(tokens[1])
    if choice is None:
        lastOut = f'Please enter a directory number, 1 to {len(directories)}'
        return
    try:
        os.chdir(f'{".." if inDir else "."}\{directories[choice - 1]}')
    except:
        lastOut = "Invalid directory, somehow. Use 'dir' to update directories."
        return
    inDir = True
    makeIndex()
    dirNumber = choice - 1
    lastOut = ""

def handleBack(tokens):
    global lastOut
    global inDir
    if not inDir:
        return
    os.chdir("..")
    inDir = False
    makeIndex(True)
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
    
    vidfile, subfile = verifyFileNumber(tokens[1]), verifyFileNumber(tokens[2])
    if vidfile is None or subfile is None:
        lastOut = f'Please enter file numbers, 1 to {len(options)}'
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
    mkvmergeProcess = runCommand("mkvmerge @DoingSubtitle.json")
    mkvmergeProcess.wait()
    log = mkvmergeProcess.stdout.read()
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
    choiceA = verifyFileNumber(tokens[1])
    choiceB = 0 if len(tokens) < 3 else verifyFileNumber(tokens[2])
    if choiceA is None or choiceB is None:
        lastOut = invalidChoice
        return
    if choiceB == 0:
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
    choiceA = verifyFileNumber(tokens[1])
    choiceB = 0 if len(tokens) < 3 else verifyFileNumber(tokens[2])
    if choiceA is None or choiceB is None:
        lastOut = invalidChoice
        return
    if choiceB == 0:
        watched.discard(options[choiceA - 1])
        lastOut = f"Unwatched {options[choiceA - 1]}"
    else:
        if choiceA > choiceB:
            choiceA, choiceB = choiceB, choiceA
        for i in range(choiceA, choiceB + 1):
            watched.discard(options[i - 1])
        lastOut = f"Unwatched {choiceB - choiceA + 1} files"
    dirty = True
   
def handleMoved(tokens):
    global lastOut
    if len(tokens) < 2:
        lastOut = "Please specify a moved file"
        return
    movedFile = verifyFileNumber(tokens[1])
    if movedFile is None:
        lastOut = f'Please select a file number from 1 to {len(options)}'
        return
    options.pop(movedFile - 1)
    
    

def printScreen():
    os.system("cls")
    if inDir:
        fileStatement = f"Files in \"{directories[dirNumber]}\":"
        print(fileStatement)
    else:
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
            "directories":handleDirectories, # debug
            "movedir":handleMoveDir,
            "sub":handleSub,
            "watched":handleWatched,
            "unwatched":handleUnwatched,
            "moved":handleMoved
            }

def mainLoop():
    global dirty
    while True:
        printScreen()
        if dirty:
            with open(f'{".." if inDir else "."}\m\watched.json', 'w') as file:
                json.dump(list(watched), file)
            dirty = False
        tokens = getInput()
        if (len(tokens) == 0):
            continue
        handlers.get(tokens[0], handleInvalid)(tokens)
        
if __name__ == "__main__":
    init()
    mainLoop()