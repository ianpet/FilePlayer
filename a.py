import os
import subprocess
import json
import multiprocessing
from typing import Callable, Optional
import re
import datetime
import time
import keyboard

numOpts = 0
options: list[str] = []
alphaOptions: list[str] = []
recentOptions: list[str] = []
doRecent = False
directories: list[str] = []
series: set[str] = set()
inDir = False
dirNumber = 0
log = "No file played"
invalidCommand = "Please entire a valid command. Use 'help' for a list of commands"
prompt = ">"
lastOut = ""
watched: set[str] = set()
dirty = False
lastFileRegex = re.compile(r"^Playing: (.*)$", re.MULTILINE)
seriesEpisodeRegex = re.compile(r"^(?:\[.*\] )?(.*) - (\d+).*\.mkv")
filter = ""
max = 0
min = 0


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
filter [word]                       Display titles containing [word], case-insensitive
filter                              Reset the filter, displaying all files
max [number]                        Show files up to [number]
max                                 Unlimit maximum number
range                               Display all files
range [min]                         Display set number of files from [min]
range [min] [max]                   Display files from [min] to [max]
config                              Open the mpv config file
log                                 Print the log of the last play
refresh                             Refresh the index
clear                               Clears output
code                                Opens the python file
quit                                Quits program
help                                Print this help message"""

# General use functions

def makeIndex(switch=False):
    global dirty
    stream = os.popen('dir\n')
    output = stream.readlines()
    global options
    global alphaOptions
    global recentOptions
    oldOptions = alphaOptions.copy()
    alphaOptions = []
    recentOptions = []
    series.clear()
    for line in output:
        if line[-5:-1] in {".mkv", ".mp4"} or line[-6:-1] == ".flac":
            name = line[39:-1]
            match = re.match(seriesEpisodeRegex, name)
            if match:
                series.add(match.groups()[0])
            alphaOptions.append(name)
            recentOptions.append((name, datetime.datetime.strptime(line[:20], "%m/%d/%Y %I:%M %p")))
    stream.close()
    recentOptions = [recentOpt[0] for recentOpt in sorted(recentOptions, key = lambda x: x[1])]
    
    options = recentOptions if doRecent else alphaOptions
    
    if not (inDir or switch):
        for title in (x for x in oldOptions if x not in alphaOptions):
            watched.discard(title)
            dirty = True
       
def printIndex():
    index = options
    max_length = len(str(len(index)))
    for (i, title) in enumerate(index):
        number = i + 1
        if number < min:
            continue
        if max and number > max:
            return
        if filter != "" and filter not in title.lower():
            continue
        buffer = " " * (max_length - len(str(number)) + 1)
        unwatched = " " if title in watched else "*"
        entry = f"{unwatched}{buffer}{number}: {title}"
        print(entry)
        
def init():
    global lastOut
    global watched
    os.system("cls")
    os.system("mode con: cols=120 lines=70")
    makeIndex()
    handleDir()
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
    subprocess.Popen(command, stdout=subprocess.PIPE, errors="ignore")

def outDirList():
    toBeShown = "Directories:\n"
    for (i, dirName) in enumerate(directories):
        buffer = "   " if i + 1 < 10 else "  "
        entry = f"{buffer}{i+1}: {dirName}\n"
        toBeShown += entry
    return toBeShown[:-1]

def inquirePlaying(finishPlaying, sender):
    playingFile = ""
    pathToSocat = "C:\\Users\\ianpe\\Documents\\Books\\Fun` Books\\Other\\m\\socat.ps1"
    socket = "\\\\.\\pipe\\mpvsocket"
    message = '{ "command": [\\"get_property\\", \\"path\\"] }'
    command = f'powershell "{pathToSocat}" {socket} \'{message}\''
    while not finishPlaying.is_set():
        proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        assert proc.stdout
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            print("Playlist subprocess timed out")
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
                return
        else:
            print(f"Playlist subprocess failed, err={proc.returncode}")
            print(proc.stdout.read().decode("utf-8"))
        finishPlaying.wait(10)
    sender.send(playingFile)

def verifyFileNumber(numString: str | int):
    try:
        num = int(numString)
    except ValueError:
        return None
    if not (1 <= num <= len(options)):
        return None
    return num

def verifyDirNumber(numString: str | int):
    try:
        num = int(numString)
    except ValueError:
        return None
    if not (1 <= num <= len(directories)):
        return None
    return num

# Handler functions for each command

def handleQuit(*tokens):
    print('Goodbye!')
    quit()
    
def handleRefresh(*tokens):
    global lastOut
    os.system("mode con: cols=120 lines=60")
    makeIndex()
    lastOut = ""
    
def handleHelp(*tokens):
    global lastOut
    lastOut = helpMessage
    
def handleLog(*tokens):
    global lastOut
    lastOut = log
    
def handlePlay(fileNumStr: Optional[str] = None, *tokens):
    global lastOut
    global log
    global dirty
    invalidChoice = "Please enter a number from 1 to " + str(len(options))
    if fileNumStr is None:
        lastOut = invalidChoice
        return
    choice = verifyFileNumber(fileNumStr)
    if choice is None:
        lastOut = invalidChoice
        return
    
    print("Press q during playback to quit...")
    title = options[choice - 1]
   
    proc = runCommand(f'mpv "{title}"')
    proc.wait()
    assert proc.stdout
    log = f"Playing file: {options[choice - 1]}\n{proc.stdout.read()}"
    if title not in watched:
        watched.add(options[choice - 1])
        dirty = True
    lastOut = ""
    
def handleDelete(fileNumStr: Optional[str] = None, *tokens):
    global lastOut
    global dirty
    invalidChoice = "Please enter a number from 1 to " + str(len(options))
    if fileNumStr is None:
        lastOut = invalidChoice
        return
    choice = verifyFileNumber(fileNumStr)
    if choice is None:
        lastOut = invalidChoice
        return
    prompt = f'Are you sure you want to delete {"unwatched " if options[choice - 1] not in watched else ""}"{options[choice-1]}"?\nY to confirm: '
    response = input(prompt)
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
        
def handleInvalid(*tokens):
    global lastOut
    lastOut = invalidCommand

def handleConfig(*tokens):
    global lastOut
    appdata = os.getenv('APPDATA')
    runCommandOnce(f"notepad++ {appdata}\\mpv\\mpv.conf")
    lastOut = "Config file opened"
    
def handleCode(*tokens):
    global lastOut
    runCommandOnce(f'notepad++ "{__file__}"')
    lastOut = "Code file opened"

def handlePlaylist(startFileStr: Optional[str | int] = None, endFilestr: Optional[str | int] = None, *tokens):
    global lastOut
    global log
    global filePlaying
    global dirty
    
    invalidChoice = "Please enter numbers from 1 to " + str(len(options))
    if startFileStr is None or endFilestr is None:
        lastOut = "Please enter the start and end of the playlist"
        return
    start, end = verifyFileNumber(startFileStr), verifyFileNumber(endFilestr)
    if start is None or end is None:
        lastOut = invalidChoice
        return
    if start > end:
        print("Playing from lower choice")
        start, end = end, start

    L = [(s + "\n") for s in options[start-1:end]]
    with open("playlist.txt", "w") as file:
        file.writelines(L)

    print("Press q during playback to quit, < and > to change file...")
    
    # hell    
    finishPlaying = multiprocessing.Event()
    sender, receiver = multiprocessing.Pipe()
    inquireProcess = multiprocessing.Process(target=inquirePlaying, args=(finishPlaying, sender))
    inquireProcess.start()

    mpvProcess = runCommand('mpv --playlist=playlist.txt --input-ipc-server=.\\pipe\\mpvsocket')
    mpvProcess.wait()
    assert mpvProcess.stdout
    log = mpvProcess.stdout.read()
    
    finishPlaying.set()
    filePlaying = receiver.recv()
    receiver.close()

    if filePlaying == "" and (regexMatches := re.findall(lastFileRegex, log)):
        filePlaying = regexMatches[len(regexMatches) - 1]

    log += f"\nLast played file: {filePlaying}"


    lastOut = ""
    if filePlaying != "":
        for played in options[start-1:end]:
            watched.add(played)
            if played == filePlaying:
                break
    dirty = True
    os.remove("playlist.txt")  
     
def handleClear(*tokens):
    global lastOut
    lastOut = ""

def handleMove(startLocStr: Optional[str] = None, endLocStr: Optional[str] = None, *tokens):
    global lastOut
    invalidChoice = "Please enter numbers from 1 to " + str(len(options))
    if startLocStr is None or endLocStr is None:
        lastOut = "Please enter the item and destination to move to"
        return
    start, end = verifyFileNumber(startLocStr), verifyFileNumber(endLocStr)
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

def handleDir(*tokens):
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
    
def handleMoveDir(fileNumStr: Optional[str] = None, secondArg: Optional[str] = None, dirNumString: Optional[str] = None, *tokens):
    global lastOut
    if inDir:
        lastOut = "Moving files between directories is not supported"
        return
    if fileNumStr is None or secondArg is None:
        lastOut = "Please enter a file and directory number"
        return
    if dirNumString is None:
        fileNum, dirNum = verifyFileNumber(fileNumStr), verifyDirNumber(secondArg)
        if fileNum is None:
            lastOut = f"Please select a file from 1 to {len(options)}"
            return
        if dirNum is None:
            lastOut = f"Please select a directory from 1 to {len(directories)}"
            return
            
        command = f'move "{options[fileNum - 1]}" "{directories[dirNum - 1]}"'
        result = runCommand(command)
        result.wait()
        if result.returncode != 0:
            lastOut = "Error in moving file."
        else:
            lastOut = f"Moved {options[fileNum - 1]} to {directories[dirNum - 1]}"
    else:
        startFileNum, endFileNum, dirNum = verifyFileNumber(fileNumStr), verifyFileNumber(secondArg), verifyDirNumber(dirNumString)
        if startFileNum is None or endFileNum is None:
            lastOut = f"Please select a file from 1 to {len(options)}"
            return
        if dirNum is None:
            lastOut = f"Please select a directory from 1 to {len(directories)}"
            return
        if endFileNum < startFileNum:
            startFileNum, endFileNum = endFileNum, startFileNum
        completed = True
        for i in range(startFileNum, endFileNum + 1):
            command = f'move "{options[i - 1]}" "{directories[dirNum - 1]}"'
            result = runCommand(command)
            result.wait()
            if result.returncode != 0:
                lastOut = "encountered an error, quitting"
                completed = False
                break
        if completed:
            lastOut = f"Moved {str(endFileNum - startFileNum + 1)} files to {directories[dirNum - 1]}"
    makeIndex(True)

def handlemkDir(startLocStr: Optional[str] = None, endLocString: Optional[str] = None, *tokens):
    global lastOut
    if inDir:
        lastOut = "Operation not supported in inspect mode"
        return
    watchedFiles = set()
    if startLocStr is None or endLocString is None:
        print("Making a new empty directory")
        name = input("Name for new directory: ")
        os.system(f'mkdir "{name}"')
        lastOut = f'Directory "{name}" created'
    else:
        invalidChoice = "Please enter numbers from 1 to " + str(len(options))
        start, end = verifyFileNumber(startLocStr), verifyFileNumber(endLocString)
        if start is None or end is None:
            lastOut = invalidChoice
            return
        if start > end:
            start, end = end, start
        print(f'Making a new directory from files {start} to {end}')
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
    handleDir()

def handlePlayDir(dirNumStr: Optional[str] = None, *tokens):
    global lastOut
    global log
    global inDir
    
    if inDir:
        lastOut = "Please use 'back' first, until functionality is added"
        return
    if dirNumStr is None:
        lastOut = "Specify a directory. Use 'dir' for a list of directories"
        return
    
    choice = verifyDirNumber(dirNumStr)
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
    handlePlaylist(1, len(options))
    os.chdir("..")
    inDir = False
    makeIndex(True)
    return
    
def handleInspect(dirNumStr: Optional[str] = None, *tokens):
    global lastOut
    global inDir
    global dirNumber
    if dirNumStr is None:
        lastOut = "Specify a directory. Use 'dir' for a list of directories."
        return
    choice = verifyDirNumber(dirNumStr)
    if choice is None:
        lastOut = f'Please enter a directory number, 1 to {len(directories)}'
        return
    try:
        os.chdir(f'{".." if inDir else "."}\\{directories[choice - 1]}')
    except:
        lastOut = "Invalid directory, somehow. Use 'dir' to update directories."
        return
    inDir = True
    makeIndex()
    dirNumber = choice - 1
    lastOut = ""

def handleBack(*tokens):
    global lastOut
    global inDir
    if not inDir:
        return
    os.chdir("..")
    inDir = False
    makeIndex(True)
    lastOut = outDirList()

def handleDirectories(*tokens):
    global lastOut
    lastOut = str(directories)

def handleSub(vidFileStr: Optional[str] = None, subFileStr: Optional[str] = None, *tokens):
    global lastOut
    global log
    if vidFileStr is None or subFileStr is None:
        lastOut = "Please specify a video file and a subtitle file."
        return
    
    vidfile, subfile = verifyFileNumber(vidFileStr), verifyFileNumber(subFileStr)
    if vidfile is None or subfile is None:
        lastOut = f'Please enter file numbers, 1 to {len(options)}'
        return
    newFileName = input("Name for new file: ")
    with open(f'{".." if inDir else "."}\\m\\SubtitleOptions.json', 'r') as file:
        optionsString = file.read()
    optionsString = optionsString.replace("XX", newFileName)
    optionsString = optionsString.replace("YY", options[vidfile-1])
    optionsString = optionsString.replace("ZZ", options[subfile-1])
    with open("DoingSubtitle.json", 'w') as file:
        file.write(optionsString)
    print("Processing...")
    mkvmergeProcess = runCommand("mkvmerge @DoingSubtitle.json")
    mkvmergeProcess.wait()
    assert mkvmergeProcess.stdout
    log = mkvmergeProcess.stdout.read()
    os.remove("DoingSubtitle.json")
    lastOut = "Made new file"
    makeIndex()

def handleWatched(firstFileStr: Optional[str] = None, lastFileStr: Optional[str] = None, *tokens):
    global lastOut
    global dirty
    invalidChoice = "Please enter a number from 1 to " + str(len(options))
    if firstFileStr is None:
        lastOut = invalidChoice
        return
    firstChoice = verifyFileNumber(firstFileStr)
    if firstChoice is None:
        lastOut = invalidChoice
        return
    if lastFileStr is None:
        title = options[firstChoice - 1]
        watched.add(title)
        lastOut = f"Watched {title}"
    else:
        lastChoice = verifyFileNumber(lastFileStr)
        if lastChoice is None:
            lastOut = invalidChoice
            return
        if firstChoice > lastChoice:
            firstChoice, lastChoice = lastChoice, firstChoice
        for i in range(firstChoice, lastChoice + 1):
            watched.add(options[i - 1])
        lastOut = f"Watched {lastChoice - firstChoice + 1} files"
    dirty = True

def handleUnwatched(firstFileStr: Optional[str] = None, lastFileStr: Optional[str] = None, *tokens):
    global lastOut
    global dirty
    invalidChoice = "Please enter a number from 1 to " + str(len(options))
    if firstFileStr is None:
        lastOut = invalidChoice
        return
    firstChoice = verifyFileNumber(firstFileStr)
    if firstChoice is None:
        lastOut = invalidChoice
        return
    if lastFileStr is None:
        title = options[firstChoice - 1]
        watched.discard(title)
        lastOut = f"Unwatched {title}"
    else:
        lastChoice = verifyFileNumber(lastFileStr)
        if lastChoice is None:
            lastOut = invalidChoice
            return
        if firstChoice > lastChoice:
            firstChoice, lastChoice = lastChoice, firstChoice
        for i in range(firstChoice, lastChoice + 1):
            watched.discard(options[i - 1])
        lastOut = f"Unwatched {lastChoice - firstChoice + 1} files"
    dirty = True
    
def handleMoved(fileNumStr: Optional[str] = None, *tokens):
    global lastOut
    if fileNumStr is None:
        lastOut = "Please specify a moved file"
        return
    movedFile = verifyFileNumber(fileNumStr)
    if movedFile is None:
        lastOut = f'Please select a file number from 1 to {len(options)}'
        return
    options.pop(movedFile - 1)

def handleFilter(filterStr: Optional[str] = None, *tokens):
    global filter
    global lastOut
    if filterStr:
        filter = filterStr
        lastOut = f"Filtering files by \"{filterStr}\""
    else:
        filter = ""
        lastOut = "No filter applied"
    return
    
def handleMax(maxStr: Optional[str] = None, *tokens):
    global lastOut
    global max
    if maxStr is None:
        max = 0
        lastOut = "Viewing all files"
        return
    try: # can select 0 for all
        maxInt = int(maxStr)
    except (ValueError, TypeError):
        lastOut = f"Please provide a number"
        return
    max = maxInt
    lastOut = f"Showing files up to {maxStr}"
    
def handleRange(minStr: Optional[str] = None, maxStr: Optional[str] = None, *tokens):
    global lastOut
    global min
    global max
    if minStr is None:
        min = 0
        max = 0
        lastOut = "Viewing all files"
        return
    minFile = verifyFileNumber(minStr)
    if minFile is None:
        lastOut = f"Please select a minimum number from 1 to {len(options)}"
        return
    if maxStr is None:
        min = minFile
        max = minFile + 50
        lastOut = f"Viewing files from {minFile}"
        return
    maxFile = verifyFileNumber(maxStr)
    if maxFile is None:
        lastOut = f"Please select a maximum number from 1 to {len(options)}"
        return
    min = minFile
    max = maxFile
    lastOut = f"Viewing files from {min} to {max}"
    
# won't work as is - save for complete rewrite
# def scrollUp():
    # curMin = min if min != 0 else len(options) - 50
    # newMin = 1 if curMin <= 50 else curMin - 50
    # handleRange(newMin)
    
    
# def scrollDown():
    # curMin = min if min != 0 else len(options) - 50
    # newMin = curMin + 50
    # handleRange(newMin)
    
# keyboard.on_press_key(",", lambda _: scrollUp())
# keyboard.on_press_key(".", lambda _: scrollDown())

def handleSeries(*tokens):
    global lastOut
    lastOut = "\n".join(f"{i+1}: {sName}" for i, sName in enumerate(sorted(list(series))))

def handleRecent(*tokens):
    global doRecent
    global lastOut
    global options
    doRecent = not doRecent
    options = recentOptions if doRecent else alphaOptions
    lastOut = f"Sorting by {'alphabetical' if not doRecent else 'chronological'} "
 
 
# main functions

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

var = printScreen

handlers: dict[str, Callable[..., None]] = {"quit":handleQuit,
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
            "moved":handleMoved,
            "filter":handleFilter,
            "max":handleMax,
            "range":handleRange,
            "series":handleSeries,
            "recent":handleRecent,
            }

def mainLoop():
    global dirty
    while True:
        printScreen()
        if dirty:
            with open(f'{".." if inDir else "."}\\m\\watched.json', 'w') as file:
                json.dump(list(watched), file)
            dirty = False
        tokens = getInput()
        if (len(tokens) == 0):
            continue
        handlers.get(tokens[0], handleInvalid)(*tokens[1:])
        
if __name__ == "__main__":
    init()
    mainLoop()