#!/bin/python3

import argparse
import concurrent.futures
import concurrent.futures.thread
import json
import logging
import os
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import Dict, Any

import ffmpeg
import pytz
import requests
import socketserver

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

#
# class RHandler(socketserver.BaseRequestHandler):
#     def handle(self):
#         # self.request is the TCP socket connected to the client
#
#         self.data = self.request.recv(1024).strip()
#         print("{} wrote:".format(self.client_address[0]))
#         print(self.data)
#         # just send back the same data, but upper-cased
#         self.request.sendall(self.data.upper())
#
#
# t_server = socketserver.TCPServer(('127.0.0.1', 6543), RHandler)


def set_up_listener():

    t_server.serve_forever()


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
    parser.add_argument('--input_file', '-i',
                        type=Path,
                        help='path to input file (to process a single file) or directory (to process all files in a '
                             'dir)')
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


def sonarr_get(api_type, query_param=None):
    global SeriesCache
    query_string = ""
    if query_param is not None:
        for q in query_param:
            query_string += "&{}={}".format(q, query_param[q])

    r = requests.get(g_vars['SONARR_URL'] + api_type + '?apikey=' + g_vars['SONARR_API_KEY'] + query_string)
    if r.status_code == 401:
        logging.critical(f'Recieved \'Unauthorized\' response from Sonarr.  Verify Credentials are accurate and try '
                         f'again')
        raise ConnectionRefusedError(r)
    jds = json.loads(r.content)
    SeriesCache = jds
    return jds


def radarr_get(api_type, query_param=None):
    global RadarrCache
    query_string = ""
    if query_param is not None:
        for q in query_param:
            query_string += "&{}={}".format(q, query_param[q])

    r = requests.get(g_vars['RADARR_URL'] + api_type + '?apikey=' + g_vars['RADARR_API_KEY'] + query_string)
    if r.status_code == 401:
        logging.critical(f'Received \'Unauthorized\' response from Radarr.  Verify Credentials are accurate and try '
                         f'again')
        print(f'Received \'Unauthorized\' response from Radarr.  Verify Credentials are accurate and try '
              f'again')
        raise ConnectionRefusedError(r)
    jds = json.loads(r.content)
    RadarrCache = jds
    return jds


def get_radarr_movie_paths():
    radarr_get('movie')
    path_list = list()
    for movie in RadarrCache:
        if movie['hasFile']:
            mov_dir = movie['path']
            file_path = mov_dir + '/' + movie['movieFile']['relativePath']
            path_list.append(file_path)
    return path_list


def notify_sonarr_of_series_update(series_id: int = None):
    body: dict
    if series_id is not None:
        body = {"name": "RefreshSeries", 'seriesId': series_id}
    else:
        body = {"name": "RefreshSeries"}

    json_body = json.dumps(body)
    print("commanding sonarr to rescan")
    r = requests.post(g_vars['SONARR_URL'] + "command" + '?apikey=' + g_vars['SONARR_API_KEY'], json_body)
    print("response: {}".format(r.text))


def get_plex_sessions() -> int:
    from plexapi.server import PlexServer
    try:
        plex = PlexServer(g_vars['PLEX_URL'], g_vars['PLEX_TOKEN'])
        plex_sessions = plex.sessions()
        return len(plex_sessions)
    except Exception as ex:
        logging.critical(ex)
        print(ex)
        raise ConnectionError()


def get_series_titles(json_input) -> dict:
    title_list = {'key': 'title'}
    for thing in json_input:
        series_title = thing["title"]
        series_id = thing["id"]
        new_item = {series_title: series_id}
        title_list.update(new_item)
    return title_list


def get_series_episode_list(series_id):
    qp = {'seriesId': '{}'.format(series_id)}
    req = sonarr_get("episode", qp)
    return req


def probe_video_file(file_path):
    if not os.path.exists(file_path):
        if parsed_args.verbose:
            logging.debug(f'{file_path} does not exist')
        return 0
    try:
        file_meta = ffmpeg.probe(file_path, analyzeduration='200M', probesize='200M')
    except Exception as ex:
        logging.error(ex)
        print(ex)
        return 1
    else:
        return file_meta


def get_series_file_paths(series_id):
    ep_list = get_series_episode_list(series_id)
    path_list = list()
    for e in ep_list:
        if e['hasFile']:
            ep_file = e['episodeFile']['path']
            path_list.append(ep_file)
    return path_list


def get_master_file_path_list():
    global P_Counter
    global P_Limit
    global SeriesCache
    global RadarrCache
    file_paths = list()

    if not parsed_args.ignore_movies:
        movie_paths = get_radarr_movie_paths()
        if movie_paths is not None and len(movie_paths) > 0:
            file_paths.extend(movie_paths)
    for series in SeriesCache:
        i = series['id']
        series_file_paths = get_series_file_paths(i)
        if series_file_paths is None or len(series_file_paths) < 1:
            pass
        else:
            file_paths.extend(series_file_paths)
    return file_paths


def process_file(file_path):
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

    meta = probe_video_file(file_path)
    if meta == 1 or meta == 0:
        return None
    # if container is not mp4 then we need to convert anyway
    if re.search(".mp4$", file_path) is None:
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
                "{} is candidate for processing (P_Count is {}, P_Limit is {})".format(file_path, P_Counter,
                                                                                       P_Limit))
        (return_code, file_name) = convert_video_file(file_path)
        if return_code == 0:
            return 0, file_name
    else:
        # if not a candidate, return none
        return None


def ffmpeg_argument_assembly(sanitized_file_name: str, json_file_meta, container_type: str):
    arg_list = list()
    arg_list.append("-y")
    arg_list.append("-map 0")
    arg_list.append("-copy_unknown")
    arg_list.append('-analyzeduration 800M')
    arg_list.append('-probesize 800M')

    v_args = ffmpeg_video_conversion_argument(json_file_meta)
    if v_args is not None:
        arg_list.extend(v_args)
    elif v_args is None:
        arg_list.append('-vcodec copy')
    a_args = ffmpeg_audio_conversion_argument(json_file_meta)
    if a_args is not None:
        arg_list.extend(a_args)
    elif a_args is None:
        arg_list.append('-acodec copy')
    s_args = ffmpeg_subtitle_conversion_argument(json_file_meta, container_type)
    if s_args is not None:
        arg_list.extend(s_args)
    t_args = ffmpeg_adaptive_thread_count_argument()
    if t_args is not None:
        arg_list.extend(t_args)
    # if parsed_args.background is not None:
    #     argList.append(f'-threads {parsed_args.background}')
    # force file overwrite
    # argList.append("-map_metadata 0")
    # add input file
    # if parsed_args.verbose == True:
    #     logging.debug(f"v_args is {v_args}; a_args is {a_args}; file ends with .mp4 bools is
    #     {sanitizedFileName.endswith('.mp4')}")
    if v_args is None and a_args is None and re.search(".mp4$|.mkv$", sanitized_file_name) is not None:
        # if all three conditions are met, then we don't need to convert
        return 2
    separator = " "
    if re.search(".mp4$|.mkv$", sanitized_file_name) is not None:
        # assemble ffmpeg command with argument list and output file name
        joined_arg_string = f"ffmpeg -i \'{sanitized_file_name}\' {separator.join(arg_list)} \'{sanitized_file_name + '.converting' + container_type}\' "
    else:
        joined_arg_string = f"ffmpeg -i \'{sanitized_file_name}\' {separator.join(arg_list)} \'{sanitized_file_name + '.converting.mkv'}\' "

    # if parsed_args.verbose == True:
    print(f'{joined_arg_string}')
    logging.debug(joined_arg_string)
    return joined_arg_string


def ffmpeg_adaptive_thread_count_argument() -> set:
    avail_threads = os.cpu_count()
    plex_clients = get_plex_sessions()
    thread_args = set()
    if parsed_args.adaptive:
        if plex_clients == 0:
            if parsed_args.background is None or parsed_args.background == 0:
                thread_args.add(f'-threads {avail_threads - 1}')
                return thread_args
            else:
                thread_args.add(f'-threads {parsed_args.background}')
                return thread_args
        elif 1 >= plex_clients > 0:
            thread_args.add(f'-threads {avail_threads // 1.5}')
            # if parsed_args.verbose:
            #     print(f'running with {(avail_threads // 1.5)} threads')
            return thread_args
        elif 2 >= plex_clients > 1:
            thread_args.add(f'-threads {avail_threads // 2}')
            # if parsed_args.verbose:
            #     print(f'running with {(avail_threads // 2)} threads')
            return thread_args

        elif plex_clients > 2:
            thread_args.add(f'-threads {avail_threads // 3}')
            # if parsed_args.verbose:
            #     print(f'running with {avail_threads // 3} threads')
            return thread_args
    else:
        if parsed_args.background is None or parsed_args.background == 0:
            return None
        else:
            thread_args.add(f'-threads {parsed_args.background}')
            return thread_args


def ffmpeg_video_conversion_argument(json_file_meta):
    # define the rules for video conversion here
    try:
        video_args = set()
        streams = json_file_meta['streams']

        for s in streams:
            try:
                if s['codec_type'] == 'video':
                    # currently only care about it being h264
                    # TODO: add resolution and fps

                    if s['codec_name'] != 'h264':
                        video_args.add('-vcodec h264')
                    fps: float
                    fps_frac = s['r_frame_rate']
                    if len(fps_frac) == 0:
                        fps = fps_frac
                    else:
                        split_frac = fps_frac.split('/')
                        fps = int(split_frac[0]) / int(split_frac[1])
                    if fps >= 32:
                        video_args.add('-framerate 24')
                    try:
                        if s['tags'] is not None:
                            if s['tags']['mimetype'] is not None:
                                if s['tags']['mimetype'] == 'image/jpeg':
                                    video_args.add(f"-map -0:{s['index']}")

                    except Exception as ex:
                        pass
                else:
                    pass
            except Exception as ex:
                logging.error(f"error processing video args: {ex}")
        if len(video_args) == 0:
            return None
        else:
            video_args.add('-vsync 2')
            video_args.add('-r 24')
            video_args.add('-max_muxing_queue_size 9999')
            video_args.add('-preset slow')
            return video_args
    except Exception as ex:
        logging.error(f"error processing video args: {ex}")


def ffmpeg_audio_conversion_argument(json_file_meta):
    # define the rules for audio conversion here
    try:
        audio_args = set()
        streams = json_file_meta['streams']

        for s in streams:
            if s['codec_type'] == 'audio':
                # we want everything to be in 2 channel aac
                if s['codec_name'] != 'aac':
                    audio_args.add("-acodec aac")
                if s['channels'] != 2:
                    audio_args.add("-ac 2")
            else:
                pass
    except Exception as ex:
        logging.error(f"error processing audio args; error: {ex}")

    otherargspresent: bool
    if len(audio_args) == 0:
        otherargspresent = False
    else:
        otherargspresent = True
    try:
        # if there are multiple audio streams, and one has language= english, then set it as the default stream for
        # playback
        audio_stream_list = list(
            filter(lambda x: x['codec_type'] == 'audio' and x['tags']['language'] is not None, streams))
        if len(audio_stream_list) > 1:
            eng_streams = list(filter(lambda x: x['tags']['language'] == 'eng', audio_stream_list))
            if len(eng_streams) > 1:
                # look for "commentary in the list of english streams to weed out commentary tracks"
                for s in eng_streams:
                    track_title = s['tags']['title']
                    if track_title is not None:
                        commentary = re.search("commentary", str(track_title), re.RegexFlag.IGNORECASE)
                        if commentary is not None:
                            eng_streams.remove(s)

            if len(eng_streams) == 1:
                # remove the default designation from all audio streams except our chosen one
                remove_default_list = list(filter(lambda x: x['disposition']['default'] == 1, audio_stream_list))
                try:
                    remove_default_list.remove(eng_streams[0])
                except ValueError:
                    pass
                if len(remove_default_list) >= 1:
                    for r in remove_default_list:
                        audio_args.add(f"-disposition:{r['index']} 0")
                if eng_streams[0]['disposition']['default'] == 0:
                    audio_args.add(f"-disposition:{eng_streams[0]['index']} default")
    except Exception as ex:
        logging.error(ex)

    if len(audio_args) == 0:
        return None

    if otherargspresent is False:
        audio_args.add("-acodec copy")

    return audio_args


def ffmpeg_subtitle_conversion_argument(json_file_meta, container_type: str):
    # define the rules for audio conversion here
    # if re.search(".mkv$", containerType) is None:
    try:
        subt_args = set()
        streams = json_file_meta['streams']
        for s in streams:
            if s['codec_type'] == 'subtitle':
                if s['codec_name'] == 'dvd_subtitle' or s['codec_name'] == 'hdmv_pgs_subtitle':
                    subt_args.add(f'-scodec copy')

                #  subt_args.add(f"-map -0:{s['index']}")

                # remove subtitle stream mappings
                # if s['channels'] != 2:
                #     subt_args.append("-ac 2")

                # for now just copy subtitles

                # if len(subt_args) == 0:
                # tell it not to map subtitles, mp4 doesn't support them as streams anyway
                #  subt_args.append("-scodec copy")
            else:
                pass
        return subt_args
    except Exception as ex:
        print(ex)
        logging.error(f'error: {ex}')


def sani_string(s_input: str):
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
    s_input = s_input.replace("\'", '\'' + "\\'" + "\'")
    return s_input


def convert_video_file(file):
    global P_Counter

    sanitized_string = sani_string(file)
    try:
        conv_args: str
        json_file_meta = probe_video_file(file)
        if json_file_meta == 1 or json_file_meta == 0:
            return 1
        container_type: str
        if re.search(".mp4$", sanitized_string) is not None:
            container_type = ".mp4"
        elif re.search(".mkv$", sanitized_string) is not None:
            container_type = ".mkv"
        else:
            container_type = ".mkv"
        conv_args = ffmpeg_argument_assembly(sanitized_string, json_file_meta, container_type)
        if conv_args == 2:
            # if parsed_args.verbose == True:
            #     logging.debug(f'{file} already meets criteria, skipping')
            return 0

        # if parsed_args.verbose == True:
        #     logging.debug(f'args: \n {conv_args} \n')
        # new_args = conv_args.replace('&', '\&')
        new_args = conv_args
        # if parsed_args.verbose == True:
        #     logging.debug(f'args:: \\n {new_args} \\n')
        conv_process: p = subprocess.Popen(new_args,
                                           stdout=subprocess.PIPE,
                                           shell=True)
        (output, err) = conv_process.communicate()
        print(output)
        print(err)
        logging.error(err)
        p_status = conv_process.wait()
        if conv_process.returncode == 0:
            logging.info("success converting {}".format(file))
            P_Counter = P_Counter + 1

        elif conv_process.returncode == 1:
            print(f"error converting {file}")
            logging.error(f"error converting {file}")
            try:
                os.remove.file(sanitized_string + '.converting' + container_type)
                if parsed_args.verbose:
                    print(f'cleaning up incomplete conversion file')
            except Exception:
                pass
            P_Counter = P_Counter + 1
            raise ChildProcessError
        else:
            print("return code is {}".format(conv_process.returncode))
            P_Counter = P_Counter + 1
            raise EnvironmentError

    except Exception as ex:
        print(ex)
        logging.critical(ex)
        return 1
    else:
        try:
            # path is not literal, so we don't want the 'sanitized' version
            if container_type == '.mkv' or container_type == '.mp4':
                temp_file_name_unsanitized = file + '.converting' + container_type
            else:
                temp_file_name_unsanitized = file + '.converting.mkv'
            if re.search(".mkv$", file):
                new_file_name = file

                shutil.move(temp_file_name_unsanitized, new_file_name)
                if parsed_args.verbose:
                    print(f'moved {temp_file_name_unsanitized} over {new_file_name}')
                    logging.debug(f'moved {temp_file_name_unsanitized} over {new_file_name}')
            elif re.search(".avi$", file):
                new_file_name = file.strip(".avi")
                new_file_name += ".mp4"
                shutil.move(temp_file_name_unsanitized, new_file_name)
                if parsed_args.verbose:
                    print(f'moved {temp_file_name_unsanitized} over {new_file_name}')
                    logging.debug(f'moved {temp_file_name_unsanitized} over {new_file_name}')
            else:
                shutil.move(temp_file_name_unsanitized, file)
                if parsed_args.verbose:
                    print(f'moved {temp_file_name_unsanitized} over {file}')
                    logging.debug(f'moved {temp_file_name_unsanitized} over {file}')
                return 0, temp_file_name_unsanitized
        except Exception as ex:
            logging.critical(f"error during post processing; internal error: {ex}")
            print(f"error during post-processing; error: {ex}")
            return 1
        else:
            if file != new_file_name:
                os.remove(file)  # THIS WILL REMOVE THE NEW ONE IF NEWFILE NAME AND OLDFILE NAME ARE THE SAME!!!!
                if parsed_args.verbose:
                    print(f'deleting original file: {file}')
                    logging.debug(f'deleting original file: {file}')

            logging.debug("completed processing of {}".format(file))
            return 0, new_file_name


def find_episode_file_id_from_file_path(file_path: str):
    for series in SeriesCache:
        s_path = series['path']
        if file_path.startswith(s_path):
            ep_list = get_series_episode_list(series['id'])
            for e in ep_list:
                if e['hasFile']:
                    if e['episodeFile']['path'] == file_path:
                        return e['episodeFile']['id']


def scan_video_files(json_response):
    for series in json_response:
        i = series['id']
        file_paths = get_series_file_paths(i)
        if file_paths is None:
            return
        try:
            for f in file_paths:
                output_string = "{}".format(f)
                meta = probe_video_file(f)
                if meta == 1 or meta == 2:
                    pass
                else:
                    streams = meta['streams']
                    for s in streams:
                        if s['codec_type'] == 'video':
                            output_string += "|video={}".format(s['codec_name'])
                        if s['codec_type'] == 'audio':
                            output_string += "|audio={}".format(s['codec_name'])
                    print(output_string)
        except Exception as ex:
            logging.exception(ex)


def refresh_cache(duration_seconds: int):
    global lastCacheRefreshTime
    cache_lifetime: timedelta
    cache_lifetime = datetime.utcnow() - lastCacheRefreshTime
    if cache_lifetime > timedelta(0, duration_seconds, 0):
        sonarr_get("series")
        radarr_get("movie")
        lastCacheRefreshTime = datetime.utcnow()
        return
    else:
        return


def notify_endpoints():
    # notify sonarr to rescan
    body = {"name": "RefreshSeries"}
    sonarr_json_body = json.dumps(body)
    r = requests.post(g_vars['SONARR_URL'] + "command" + '?apikey=' + g_vars['SONARR_API_KEY'], sonarr_json_body)
    # notify radarr to rescan
    radarr_body = {"name": "RescanMovie"}
    radarr_json_body = json.dumps(radarr_body)
    r = requests.post(g_vars['RADARR_URL'] + "command" + '?apikey=' + g_vars['RADARR_API_KEY'], radarr_json_body)
    # TODO notify plex to refresh library


def worker(event_inst):
    global P_Counter
    global P_Limit
    global lastCacheRefreshTime
    logging.critical("testing from worker")
    lastCacheRefreshTime = datetime.utcnow()
    sonarr_get("series")
    radarr_get("movie")
    while not event_inst.isSet():
        try:
            refresh_cache(3600)
            file_paths = get_master_file_path_list()

            wcount = max(parsed_args.worker, 1)

            with concurrent.futures.thread.ThreadPoolExecutor(max_workers=wcount) as executor:

                for f in file_paths:
                    if not event_inst.isSet():

                        # if parsed_args.verbose == True:
                        #     logging.debug("worker thread checking in")

                        executor.submit(worker_process, f)

                        if P_Limit != 0:
                            if P_Counter >= P_Limit:
                                event_inst.set()
                    else:
                        break
                notify_endpoints()
                event_inst.set()

        except Exception as ex:
            logging.error(ex)


def worker_process(file: str):
    try:

        should_run = is_allowed_to_run_determination()
        while not should_run:
            if parsed_args.verbose:
                print('run criteria not met, waiting')
            time.sleep(150)
            # after the pause, check again to see if run restrictions are met
            should_run = is_allowed_to_run_determination()
            pass

        (p, f) = process_file(file)
        if p is not None:
            if p == '-':
                pass
            elif p == 0:
                # print(" RETURN 0 \n\n")
                return 0, f
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


def is_allowed_to_run_determination():
    if parsed_args.offpeak:
        time_factor = is_allowed_to_run_time()
        if not time_factor:
            print("waiting due to time restrictions")
            return False
        else:
            pass
    if parsed_args.plex:
        # dont run if IsPlexBusy is true
        plex_factor = (get_plex_sessions() > 0)
        if plex_factor:
            print("skipping due to plex client activity")
            return False
        else:
            pass
    # if nothing caused the check to fail, then give the green light to start processing
    return True


def is_allowed_to_run_time():
    if parsed_args.offpeak:
        tz_la = pytz.timezone('America/Los_Angeles')
        now_time = datetime.now(tz_la)
        dow = now_time.isoweekday()
        hr = now_time.hour
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


def main(op_args=None, *args):
    global startTime
    global parsed_args

    if op_args is not None:
        parsed_args = create_arg_parser().parse_args(['--verbose'].extend(args))
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s %(threadName)s %(lineno)d %(message)s"

        )
    else:
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s %(threadName)s %(lineno)d %(message)s",
            filename="../sonarr_trans_log.log"
        )
    # logging.critical("initializing")

    P_Counter = 0
    P_Limit = 0
    startTime = datetime.utcnow()

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

    if op_args is not None and os.path.exists(op_args):
        (r_code, new_name) = worker_process(str(Path(Path(op_args)).absolute()))
        return 0, new_name
    elif op_args is not None:
        return 1
    else:

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
        #     notify_sonarr_of_series_update()
        # else:
        #     main()
        # pass


if __name__ == "__main__":
    arg_parser = create_arg_parser()
    parsed_args = arg_parser.parse_args(sys.argv[1:])
    main()
