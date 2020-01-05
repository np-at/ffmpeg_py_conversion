#!/bin/python3

import os
from json import JSONDecodeError
from typing import Dict, Any

import ffmpeg
import requests
import json
import subprocess
import shutil
import re
import argparse
from pathlib import Path
import sys
import logging
import threading
from datetime import datetime, timedelta
import pytz
import plexapi
import concurrent.futures
import concurrent.futures.thread
import time


"""  """
global SONARR_URL
SONARR_URL = "http://[SONARR URL/IP ADDRESS ]:8989/api/"  # sonarr
global SONARR_APIKEY_PARAM
SONARR_APIKEY_PARAM = "?apikey=[SONARR API KEY]"
global RADARR_URL
global RADARR_APIKEY_PARAM
RADARR_URL = 'http://[RADARR URL/IP ]:7878/api/'
RADARR_APIKEY_PARAM = "?apikey=[RADARR API KEY HERE]"
global SeriesCache
SeriesCache = None
global RadarrCache
RadarrCache = None
global lastCacheRefreshTime
lastCacheRefreshTime = datetime.utcnow()
global P_Counter
P_Counter = 0
global P_Limit
P_Limit = 0
PLEX_URL = 'http://[PLEX URL/IP HERE]:32400'
PLEX_TOKEN = '[PLEX TOKEN HERE]'

g_vars: Dict[Any, str] = dict(SONARR_URL=SONARR_URL, SONARR_API_KEY=SONARR_APIKEY_PARAM, RADARR_URL=RADARR_URL,
                              RADARR_API_KEY=RADARR_APIKEY_PARAM, PLEX_URL=PLEX_URL, PLEX_TOKEN=PLEX_TOKEN)


def create_arg_parser():
    """"Creates and returns the ArgumentParser object."""

    parser = argparse.ArgumentParser(description='Description of your app.')
    parser.add_argument('--background', '-b',
                        help="run with 1 thread to allow other processes to work in parallel \
                          will run with 1 thread per flag present",

                        action='count')
    parser.add_argument('--daemon', '-d',
                        help='run as ongoing process, consider using with -O and/or -p',
                        action='store_true')
    parser.add_argument('--plex', '-p',
                        help="check and wait for there to be 0 plex clients before starting a transcode",

                        action='store_true')
    parser.add_argument('--worker', '-w',
                        help='the number of duplicate worker processes spawned',
                        default=1,
                        action='count')
    parser.add_argument('--limit',
                        '-l',
                        help='limit this to processing X items',
                        type=int,
                        default=0)
    parser.add_argument('--verbose',
                        '-v',
                        help="increase verbosity",
                        action='store_true')
    parser.add_argument('--offpeak',
                        '-O',
                        help="start worker threads that will only run during off peak hours",
                        action='store_true')
    parser.add_argument('--ignore_movies', '-m',
                        help='skip fetching movie paths for transcoding',
                        action='store_true')
    parser.add_argument('--adaptive', '-a',
                        help='try to scale number of threads based on active plex sessions',
                        action='store_true')
    # parser.add_argument('--outputDirectory',
    # help='Path to the output that contains the resumes.')

    return parser


def sonarr_get(apiType, queryParam=None):
    global SeriesCache
    queryString = ""
    if queryParam is not None:
        for q in queryParam:
            queryString += "&{}={}".format(q, queryParam[q])

    r = requests.get(g_vars['SONARR_URL'] + apiType + '?apikey=' + g_vars['SONARR_API_KEY'] + queryString)
    if r.status_code == 401:
        logging.critical(f'Recieved \'Unauthorized\' response from Sonarr.  Verify Credentials are accurate and try '
                         f'again')
        raise ConnectionRefusedError(r)
    jds = json.loads(r.content)
    SeriesCache = jds
    return jds


def radarr_get(apiType, queryParam=None):
    global RadarrCache
    queryString = ""
    if queryParam is not None:
        for q in queryParam:
            queryString += "&{}={}".format(q, queryParam[q])

    r = requests.get(g_vars['RADARR_URL'] + apiType + '?apikey=' + g_vars['RADARR_API_KEY'] + queryString)
    if r.status_code == 401:
        logging.critical(f'Recieved \'Unauthorized\' response from Radarr.  Verify Credentials are accurate and try '
                         f'again')
        print(f'Recieved \'Unauthorized\' response from Radarr.  Verify Credentials are accurate and try '
                         f'again')
        raise ConnectionRefusedError(r)
    jds = json.loads(r.content)
    RadarrCache = jds
    return jds


def GetRadarrMoviePaths():
    radarr_get('movie')
    Pathlist = list()
    for movie in RadarrCache:
        if movie['hasFile']:
            movDir = movie['path']
            filePath = movDir + '/' + movie['movieFile']['relativePath']
            Pathlist.append(filePath)
    return Pathlist


def NotifySonarrOfSeriesUpdate(seriesId: int = None):
    body: dict
    if seriesId is not None:
        body = {"name": "RefreshSeries", 'seriesId': seriesId}
    else:
        body = {"name": "RefreshSeries"}

    jsonbody = json.dumps(body)
    print("commanding sonarr to rescan")
    r = requests.post(g_vars['SONARR_URL'] + "command" + '?apikey=' + g_vars['SONARR_API_KEY'], jsonbody)
    print("response: {}".format(r.text))


def GetPlexSessions() -> int:
    from plexapi.server import PlexServer
    try:
        plex = PlexServer(g_vars['PLEX_URL'], g_vars['PLEX_TOKEN'])
        plexSessions = plex.sessions()
        return len(plexSessions)
    except Exception as ex:
        logging.critical(ex)
        print(ex)
        raise ConnectionError()


def GetSeriesTitles(jsonInput) -> dict:
    titleList = {'key': 'title'}
    for thing in jsonInput:
        seriesTitle = thing["title"]
        seriesId = thing["id"]
        newItem = {seriesTitle: seriesId}
        titleList.update(newItem)
    return titleList


def GetSeriesEpisodeList(seriesId):
    qp = {'seriesId': '{}'.format(seriesId)}
    req = sonarr_get("episode", qp)
    return req


def ProbeVideoFile(filePath):
    if not os.path.exists(filePath):
        if parsed_args.verbose:
            logging.debug(f'{filePath} does not exist')
        return 0
    try:
        fileMeta = ffmpeg.probe(filePath, analyzeduration='200M', probesize='200M')
    except Exception as ex:
        logging.error(ex)
        print(ex)
        return 1
    else:
        return fileMeta


def GetSeriesFilePaths(seriesId):
    epList = GetSeriesEpisodeList(seriesId)
    pathList = list()
    for e in epList:
        if e['hasFile']:
            epFile = e['episodeFile']['path']
            pathList.append(epFile)
    return pathList


def GetMasterFilePathList():
    global P_Counter
    global P_Limit
    global SeriesCache
    global RadarrCache
    filePaths = list()

    if not parsed_args.ignore_movies:
        moviePaths = GetRadarrMoviePaths()
        if moviePaths is not None and len(moviePaths) > 0:
            filePaths.extend(moviePaths)
    for series in SeriesCache:
        i = series['id']
        seriesFilePaths = GetSeriesFilePaths(i)
        if seriesFilePaths is None or len(seriesFilePaths) < 1:
            pass
        else:
            filePaths.extend(seriesFilePaths)
    return filePaths


def ProcessFile(filePath):
    # double check the file
    global P_Counter
    global P_Limit

    PROCESS_THIS = False

    # limit check
    if P_Limit != 0:
        # if parsed_args.verbose == True:
        #     logging.debug("P_Count is {};; P_Limit is {}".format(P_Counter, P_Limit))
        if P_Counter >= P_Limit:
            if parsed_args.verbose:
                print("limit exceeded, skipping")
            return '-'

    meta = ProbeVideoFile(filePath)
    if meta == 1 or meta == 0:
        return None
    # if container is not mp4 then we need to convert anyway
    if re.search(".mp4$", filePath) is None:
        PROCESS_THIS = True

    if PROCESS_THIS == False and meta is not None:
        streams = meta['streams']
        for s in streams:
            if s['codec_type'] == 'audio':
                if s['codec_name'] != 'aac':
                    PROCESS_THIS = True
                    break
            if s['codec_type'] == 'video':
                if s['codec_name'] != 'h264':
                    PROCESS_THIS = True
                    break

    if PROCESS_THIS:
        if parsed_args.verbose:
            logging.info(
                "{} is candidate for processing (P_Count is {}, P_Limit is {})".format(filePath, P_Counter,
                                                                                       P_Limit))
        returnCode = convertVideoFile(filePath)
        if returnCode == 0:
            return 0
    else:
        # if not a candidate, return none
        return None


def ffmpegArgumentAssembly(sanitizedFileName: str, jsonFileMeta, containerType: str):
    argList = list()
    argList.append("-y")
    argList.append("-map 0")
    argList.append("-copy_unknown")
    argList.append('-analyzeduration 800M')
    argList.append('-probesize 800M')

    vArgs = ffmpegVideoConversionArgument(jsonFileMeta)
    if vArgs is not None:
        argList.extend(vArgs)
    elif vArgs is None:
        argList.append('-vcodec copy')
    aArgs = ffmpegAudioConversionArgument(jsonFileMeta)
    if aArgs is not None:
        argList.extend(aArgs)
    elif aArgs is None:
        argList.append('-acodec copy')
    sArgs = ffmpegSubtitleConversionArgument(jsonFileMeta, containerType)
    if sArgs is not None:
        argList.extend(sArgs)
    tArgs = ffmpegAdaptiveThreadCountArgument()
    if tArgs is not None:
        argList.extend(tArgs)
    # if parsed_args.background is not None:
    #     argList.append(f'-threads {parsed_args.background}')
    # force file overwrite
    # argList.append("-map_metadata 0")
    # add input file
    # if parsed_args.verbose == True:
    #     logging.debug(f"vArgs is {vArgs}; aArgs is {aArgs}; file ends with .mp4 bools is
    #     {sanitizedFileName.endswith('.mp4')}")
    if vArgs is None and aArgs is None and re.search(".mp4$|.mkv$", sanitizedFileName) is not None:
        # if all three conditions are met, then we don't need to convert
        return 2
    separator = " "
    if re.search(".mp4$|.mkv$", sanitizedFileName) is not None:
        # assemble ffmpeg command with argument list and output file name
        joinedArgString = f"ffmpeg -i \'{sanitizedFileName}\' {separator.join(argList)} \'{sanitizedFileName + '.converting' + containerType}\' "
    else:
        joinedArgString = f"ffmpeg -i \'{sanitizedFileName}\' {separator.join(argList)} \'{sanitizedFileName + '.converting.mkv'}\' "

    # if parsed_args.verbose == True:
    print(f'{joinedArgString}')
    logging.debug(joinedArgString)
    return joinedArgString


def ffmpegAdaptiveThreadCountArgument() -> set:
    availThreads = os.cpu_count()
    plexClients = GetPlexSessions()
    threadArgs = set()
    if parsed_args.adaptive:
        if plexClients == 0:
            if parsed_args.background is None or parsed_args.background == 0:
                threadArgs.add(f'-threads {availThreads - 1}')
                return threadArgs
            else:
                threadArgs.add(f'-threads {parsed_args.background}')
                return threadArgs
        elif 1 >= plexClients > 0:
            threadArgs.add(f'-threads {availThreads // 1.5}')
            # if parsed_args.verbose:
            #     print(f'running with {(availThreads // 1.5)} threads')
            return threadArgs
        elif 2 >= plexClients > 1:
            threadArgs.add(f'-threads {availThreads // 2}')
            # if parsed_args.verbose:
            #     print(f'running with {(availThreads // 2)} threads')
            return threadArgs

        elif plexClients > 2:
            threadArgs.add(f'-threads {availThreads // 3}')
            # if parsed_args.verbose:
            #     print(f'running with {availThreads // 3} threads')
            return threadArgs
    else:
        if parsed_args.background is None or parsed_args.background == 0:
            return None
        else:
            threadArgs.add(f'-threads {parsed_args.background}')
            return threadArgs


def ffmpegVideoConversionArgument(jsonFileMeta):
    # define the rules for video conversion here
    try:
        videoArgs = set()
        streams = jsonFileMeta['streams']

        for s in streams:
            try:
                if s['codec_type'] == 'video':
                    # currently only care about it being h264
                    # TODO: add resolution and fps

                    if s['codec_name'] != 'h264':
                        videoArgs.add('-vcodec h264')
                    fps: float
                    fpsFrac = s['r_frame_rate']
                    if len(fpsFrac) == 0:
                        fps = fpsFrac
                    else:
                        splitFrac = fpsFrac.split('/')
                        fps = int(splitFrac[0]) / int(splitFrac[1])
                    if fps >= 32:
                        videoArgs.add('-framerate 24')
                    try:
                        if s['tags'] is not None:
                            if s['tags']['mimetype'] is not None:
                                if s['tags']['mimetype'] == 'image/jpeg':
                                    videoArgs.add(f"-map -0:{s['index']}")

                    except Exception as ex:
                        pass
                else:
                    pass
            except Exception as ex:
                logging.error(f"error processing video args: {ex}")
        if len(videoArgs) == 0:
            return None
        else:
            videoArgs.add('-vsync 2')
            videoArgs.add('-r 24')
            videoArgs.add('-max_muxing_queue_size 9999')
            videoArgs.add('-preset slow')
            return videoArgs
    except Exception as ex:
        logging.error(f"error processing video args: {ex}")


def ffmpegAudioConversionArgument(jsonFileMeta):
    # define the rules for audio conversion here
    try:
        audioArgs = set()
        streams = jsonFileMeta['streams']

        for s in streams:
            if s['codec_type'] == 'audio':
                # we want everything to be in 2 channel aac
                if s['codec_name'] != 'aac':
                    audioArgs.add("-acodec aac")
                if s['channels'] != 2:
                    audioArgs.add("-ac 2")
            else:
                pass
    except Exception as ex:
        logging.error(f"error processing audio args; error: {ex}")

    otherargspresent: bool
    if len(audioArgs) == 0:
        otherargspresent = False
    else:
        otherargspresent = True
    try:
        # if there are multiple audio streams, and one has language= english, then set it as the default stream for playback
        audiostreamlist = list(
            filter(lambda x: x['codec_type'] == 'audio' and x['tags']['language'] is not None, streams))
        if len(audiostreamlist) > 1:
            engStreams = list(filter(lambda x: x['tags']['language'] == 'eng', audiostreamlist))
            if len(engStreams) > 1:
                # look for "commentary in the list of english streams to weed out commentary tracks"
                for s in engStreams:
                    trackTitle = s['tags']['title']
                    if trackTitle is not None:
                        commentary = re.search("commentary", str(trackTitle), re.RegexFlag.IGNORECASE)
                        if commentary is not None:
                            engStreams.remove(s)

            if len(engStreams) == 1:
                # remove the default designation from all audio streams except our chosen one
                removeDefaultList = list(filter(lambda x: x['disposition']['default'] == 1, audiostreamlist))
                try:
                    removeDefaultList.remove(engStreams[0])
                except ValueError:
                    pass
                if len(removeDefaultList) >= 1:
                    for r in removeDefaultList:
                        audioArgs.add(f"-disposition:{r['index']} 0")
                if engStreams[0]['disposition']['default'] == 0:
                    audioArgs.add(f"-disposition:{engStreams[0]['index']} default")
    except Exception as ex:
        logging.error(ex)

    if len(audioArgs) == 0:
        return None

    if otherargspresent is False:
        audioArgs.add("-acodec copy")

    return audioArgs


def ffmpegSubtitleConversionArgument(jsonFileMeta, containerType: str):
    # define the rules for audio conversion here
    # if re.search(".mkv$", containerType) is None:
    try:
        subtArgs = set()
        streams = jsonFileMeta['streams']
        for s in streams:
            if s['codec_type'] == 'subtitle':
                if s['codec_name'] == 'dvd_subtitle' or s['codec_name'] == 'hdmv_pgs_subtitle':
                    subtArgs.add(f'-scodec copy')

                #  subtArgs.add(f"-map -0:{s['index']}")

                # remove subtitle stream mappings
                # if s['channels'] != 2:
                #     subtArgs.append("-ac 2")

                # for now just copy subtitles

                # if len(subtArgs) == 0:
                # tell it not to map subtitles, mp4 doesn't support them as streams anyway
                #  subtArgs.append("-scodec copy")
            else:
                pass
        return subtArgs
    except Exception as ex:
        print(ex)
        logging.error(f'error: {ex}')


def SaniString(sInput: str):
    # splitString = sInput.split()
    # outputString: str
    # outputString = ""
    # for e in splitString:
    #     outputString += e + "\ "
    # outputString = outputString.strip()
    # outputString = outputString.strip("\\")
    # outputString = outputString.replace("\'", '\\' + "'")
    # outputString = outputString.replace('\&', '\&\&')
    # ampsplitstring = outputString.split('&')
    # newOutputstring = ""
    # for a in ampsplitstring:
    #     newOutputstring += a + '\\&'
    # newOutputstring = newOutputstring.strip('\\&')
    sInput = sInput.replace("\'", '\'' + "\\'" + "\'")
    return sInput


def convertVideoFile(file):
    global P_Counter

    sanitizedString = SaniString(file)
    try:
        convArgs: str
        jsonFileMeta = ProbeVideoFile(file)
        if jsonFileMeta == 1 or jsonFileMeta == 0:
            return 1
        containerType: str
        if re.search(".mp4$", sanitizedString) is not None:
            containerType = ".mp4"
        elif re.search(".mkv$", sanitizedString) is not None:
            containerType = ".mkv"
        else:
            containerType = ".mkv"
        convArgs = ffmpegArgumentAssembly(sanitizedString, jsonFileMeta, containerType)
        if convArgs == 2:
            # if parsed_args.verbose == True:
            #     logging.debug(f'{file} already meets criteria, skipping')
            return 0

        # if parsed_args.verbose == True:
        #     logging.debug(f'args: \n {convArgs} \n')
        # newArgs = convArgs.replace('&', '\&')
        newArgs = convArgs
        # if parsed_args.verbose == True:
        #     logging.debug(f'args:: \\n {newArgs} \\n')
        convProcess: p = subprocess.Popen(newArgs,
                                          stdout=subprocess.PIPE,
                                          shell=True)
        (output, err) = convProcess.communicate()
        print(output)
        print(err)
        logging.error(err)
        p_status = convProcess.wait()
        if convProcess.returncode == 0:
            logging.info("success converting {}".format(file))
            P_Counter = P_Counter + 1

        elif convProcess.returncode == 1:
            print(f"error converting {file}")
            logging.error(f"error converting {file}")
            try:
                os.remove.file(sanitizedString + '.converting' + containerType)
                if parsed_args.verbose:
                    print(f'cleaning up incomplete conversion file')
            except Exception:
                pass
            P_Counter = P_Counter + 1
            raise ChildProcessError
        else:
            print("return code is {}".format(convProcess.returncode))
            P_Counter = P_Counter + 1
            raise EnvironmentError

    except Exception as ex:
        print(ex)
        logging.critical(ex)
        return 1
    else:
        try:
            # path is not literal, so we don't want the 'sanitized' version
            if containerType == '.mkv' or containerType == '.mp4':
                tempFileName_unsanitized = file + '.converting' + containerType
            else:
                tempFileName_unsanitized = file + '.converting.mkv'
            if re.search(".mkv$", file):
                newFileName = file

                shutil.move(tempFileName_unsanitized, newFileName)
                if parsed_args.verbose:
                    print(f'moved {tempFileName_unsanitized} over {newFileName}')
                    logging.debug(f'moved {tempFileName_unsanitized} over {newFileName}')
            elif re.search(".avi$", file):
                newFileName = file.strip(".avi")
                newFileName += ".mp4"
                shutil.move(tempFileName_unsanitized, newFileName)
                if parsed_args.verbose:
                    print(f'moved {tempFileName_unsanitized} over {newFileName}')
                    logging.debug(f'moved {tempFileName_unsanitized} over {newFileName}')
            else:
                shutil.move(tempFileName_unsanitized, file)
                if parsed_args.verbose:
                    print(f'moved {tempFileName_unsanitized} over {file}')
                    logging.debug(f'moved {tempFileName_unsanitized} over {file}')
                return 0
        except Exception as ex:
            logging.critical(f"error during post processing; internal error: {ex}")
            print(f"error during post-processing; error: {ex}")
            return 1
        else:
            if file != newFileName:
                os.remove(file)  # THIS WILL REMOVE THE NEW ONE IF NEWFILE NAME AND OLDFILE NAME ARE THE SAME!!!!
                if parsed_args.verbose:
                    print(f'deleting original file: {file}')
                    logging.debug(f'deleting original file: {file}')

            logging.debug("completed processing of {}".format(file))
            return 0


def FindEpisodeFileIdFromFilePath(filePath: str):
    for series in SeriesCache:
        sPath = series['path']
        if filePath.startswith(sPath):
            epList = GetSeriesEpisodeList(series['id'])
            for e in epList:
                if e['hasFile']:
                    if e['episodeFile']['path'] == filePath:
                        return e['episodeFile']['id']


def ScanVideoFiles(jsonResponse):
    for series in jsonResponse:
        i = series['id']
        filePaths = GetSeriesFilePaths(i)
        if filePaths is None:
            return
        try:
            for f in filePaths:
                outputString = "{}".format(f)
                meta = ProbeVideoFile(f)
                if meta == 1 or meta == 2:
                    pass
                else:
                    streams = meta['streams']
                    for s in streams:
                        if s['codec_type'] == 'video':
                            outputString += "|video={}".format(s['codec_name'])
                        if s['codec_type'] == 'audio':
                            outputString += "|audio={}".format(s['codec_name'])
                    print(outputString)
        except Exception as ex:
            logging.exception(ex)


def RefreshCache(duration_Seconds: int):
    global lastCacheRefreshTime
    cacheLifetime: timedelta
    cacheLifetime = datetime.utcnow() - lastCacheRefreshTime
    if cacheLifetime > timedelta(0, duration_Seconds, 0):
        sonarr_get("series")
        radarr_get("movie")
        lastCacheRefreshTime = datetime.utcnow()
        return
    else:
        return


def NotifyEndpoints():
    # notify sonarr to rescan
    Body = {"name": "RefreshSeries"}
    sonarrJsonBody = json.dumps(Body)
    r = requests.post(g_vars['SONARR_URL'] + "command" + '?apikey=' + g_vars['SONARR_API_KEY'], sonarrJsonBody)
    # notify radarr to rescan
    radarrBody = {"name": "RescanMovie"}
    radarrJsonBody = json.dumps(radarrBody)
    r = requests.post(g_vars['RADARR_URL'] + "command" + '?apikey=' +  g_vars['RADARR_API_KEY'], radarrJsonBody)
    # TODO notify plex to refresh library


def worker(event):
    global P_Counter
    global P_Limit
    global lastCacheRefreshTime
    logging.critical("testing from worker")
    lastCacheRefreshTime = datetime.utcnow()
    sonarr_get("series")
    radarr_get("movie")
    while not event.isSet():
        try:
            RefreshCache(3600)
            filePaths = GetMasterFilePathList()

            wcount = max(parsed_args.worker, 1)

            with concurrent.futures.thread.ThreadPoolExecutor(max_workers=wcount) as executor:

                for f in filePaths:
                    if not event.isSet():

                        # if parsed_args.verbose == True:
                        #     logging.debug("worker thread checking in")

                        executor.submit(workerProcess, f)

                        if P_Limit != 0:
                            if P_Counter >= P_Limit:
                                event.set()
                    else:
                        break
                NotifyEndpoints()
                event.set()

        except Exception as ex:
            logging.error(ex)


def workerProcess(file: str):
    try:

        should_run = IsAllowedToRunDetermination()
        while not should_run:
            if parsed_args.verbose:
                print('run criteria not met, waiting')
            time.sleep(150)
            # after the pause, check again to see if run restrictions are met
            should_run = IsAllowedToRunDetermination()
            pass

        p = ProcessFile(file)
        if p is not None:
            if p == '-':
                pass
            elif p == 0:
                # print(" RETURN 0 \n\n")
                return 0
            elif p == 1:
                print(" RETURN 1 \n\n")
                raise ChildProcessError
                return 1
            else:
                pass
    except Exception as ex:
        logging.error(ex)
        if parsed_args.verbose:
            print(f"error while processing {file} \n error is {ex}")


def IsAllowedToRunDetermination():
    if parsed_args.offpeak:
        timeFactor = IsAllowedToRun_Time()
        if not timeFactor:
            print("waiting due to time restrictions")
            return False
        else:
            pass
    if parsed_args.plex:
        # dont run if IsPlexBusy is true
        plexFactor = (GetPlexSessions() > 0)
        if plexFactor:
            print("skipping due to plex client activity")
            return False
        else:
            pass
    # if nothing caused the check to fail, then give the green light to start processing
    return True


def IsAllowedToRun_Time():
    if parsed_args.offpeak:
        tz_LA = pytz.timezone('America/Los_Angeles')
        nowTime = datetime.now(tz_LA)
        dow = nowTime.isoweekday()
        hr = nowTime.hour
        # if it's a weekday (mon-fri)
        if 5 >= dow >= 1:
            # define weekday time constraints here
            if 17 >= hr >= 9:
                # working hours
                return True
            elif 6 >= hr >= 0:
                # sleeping hours
                return True
            elif 24 >= hr >= 22:
                return True
            else:
                return False
        # if it's the weekend: we expect video to be used during the day
        # only run during the deep night
        if 7 >= dow >= 6:
            if 8 >= hr >= 0:
                return True
            elif 24 >= hr >= 22:
                return True
            else:
                return False

        # fall through return false just in case; should never get hit
        return False
    else:
        # if we're not worried about time, then it's always allowed to run
        return True


def try_load_config_file():
    env_file = os.path.join(os.path.curdir, '.env')
    data = dict()
    if os.path.exists(env_file):
        try:
            with open(env_file) as f:
                data = json.load(f)

        except JSONDecodeError as ex:
            logging.critical(f'unable to decode {env_file}', ex)
        except Exception as exx:
            logging.critical(f'error reading {env_file}', exx)
        else:
            for key in g_vars:
                try:
                    if data[key] is not None:
                        g_vars[key] = data[key]
                except:
                    # ignore error
                    pass
            return


if __name__ == "__main__":
    global startTime
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(threadName)s %(lineno)d %(message)s",
        filename="sonarr_trans_log.log"
    )
    # logging.critical("initializing")

    P_Counter = 0
    P_Limit = 0
    startTime = datetime.utcnow()

    arg_parser = create_arg_parser()
    parsed_args = arg_parser.parse_args(sys.argv[1:])
    logging.debug(parsed_args)

    # load secrets from .env file:
    try_load_config_file()
    if parsed_args.limit is not None:
        if parsed_args.limit != 0:
            P_Limit = parsed_args.limit
    # try:
    #     # except Exception as ex:
    #     #     logging.basicConfig(
    #     #         level=logging.debug,
    #     #         format="%(asctime)s %(threadName)s %(lineno)d %(message)s"

    #     #     )
    # except Exception as ex:
    #     print(ex)
    #     logging.critical(ex)
    if parsed_args.verbose:
        print("verbose mode on")
        logging.debug("Initilizing with P_Count: {};; P_Limit: {}".format(P_Counter, P_Limit))

    event = threading.Event()
    thread = threading.Thread(target=worker, args=(event,))
    # thread_two = threading.Thread(target=worker, args=(event,))
    thread.start()

    # thread_two.start()

    while not event.isSet():
        try:
            elapsedTime = datetime.utcnow() - startTime
            if parsed_args.verbose:
                print(f'elapsed time is {elapsedTime}')

            # stop after 1 day to prevent zombie processes
            if elapsedTime > timedelta(3):
                break
            event.wait(300)
        except KeyboardInterrupt:
            event.set()
            break

    # if parsed_args.notify == True:
    #     NotifySonarrOfSeriesUpdate()
    # else:
    #     main()
    # pass
