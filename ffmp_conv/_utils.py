import json
import logging
import re
import os
from plexapi.server import PlexServer


class ArgAssembler:
    def __init__(self, verbose: bool = False, adaptive: bool = True, background: int = 0, plex_url: str = None,
                 plex_token: str = None):
        self.verbose = verbose
        self.adaptive = adaptive
        self.background = background
        if plex_token is not None and plex_url is not None:
            try:
                self.plex = PlexServer(plex_url, plex_token)
            except:
                self.plex = None
        else:
            self.plex = None

    def argument_assembly(self, file_name: str, json_file_meta: json) -> str:
        """

        @param file_name:
        @param json_file_meta:
        @param container_type:
        @return:
        """
        san_file_name = self.sani_string(str(file_name))
        mp4 = re.compile(".mp4$|.mkv$")
        mkv = re.compile(".mkv$")
        mm = re.compile(".mkv$|.mp4$")
        if mp4.search(san_file_name) is not None:
            container_type = ".mp4"
        elif mkv.search(san_file_name) is not None:
            container_type = ".mkv"
        else:
            container_type = ".mkv"

        arg_list = list()
        arg_list.append("-y")
        arg_list.append("-map 0")
        arg_list.append("-copy_unknown")
        arg_list.append('-analyzeduration 800M')
        arg_list.append('-probesize 800M')

        v_args = self.ffmpeg_video_conversion_argument(json_file_meta)
        if v_args is not None:
            arg_list.extend(v_args)
        elif v_args is None:
            arg_list.append('-vcodec copy')
        a_args = self.ffmpeg_audio_conversion_argument(json_file_meta)
        if a_args is not None:
            arg_list.extend(a_args)
        elif a_args is None:
            arg_list.append('-acodec copy')
        s_args = self.ffmpeg_subtitle_conversion_argument(json_file_meta, container_type)
        if s_args is not None:
            arg_list.extend(s_args)
        t_args = self.ffmpeg_adaptive_thread_count_argument()
        if t_args is not None:
            arg_list.extend(t_args)
        # if self.background is not None:
        #     argList.append(f'-threads {self.background}')
        # force file overwrite
        # argList.append("-map_metadata 0")
        # add input file
        # if self.verbose == True:
        #     logging.debug(f"v_args is {v_args}; a_args is {a_args}; file ends with .mp4 bools is
        #     {sanitizedFileName.endswith('.mp4')}")
        if v_args is None and a_args is None and mm.search(san_file_name) is not None:
            # if all three conditions are met, then we don't need to convert
            return 2, None
        separator = " "
        temp_file_name = str()
        if mm.search(san_file_name) is not None:
            temp_file_name = san_file_name + '.converting' + container_type
            # assemble ffmpeg command with argument list and output file name
            joined_arg_string = f"ffmpeg -i \'{san_file_name}\' {separator.join(arg_list)} \'{temp_file_name}\' "
        else:
            temp_file_name = san_file_name + '.converting.mkv'
            joined_arg_string = f"ffmpeg -i \'{san_file_name}\' {separator.join(arg_list)} \'{temp_file_name}\' "

        # if self.verbose == True:
        print(f'{joined_arg_string}')
        logging.debug(joined_arg_string)
        return joined_arg_string, temp_file_name

    def ffmpeg_adaptive_thread_count_argument(self) -> set:
        avail_threads = os.cpu_count()
        plex_clients = int()

        if self.plex is None:
            plex_clients = 0
        else:
            plex_clients = self.plex.sessions()
        thread_args = set()
        if self.adaptive:
            if plex_clients == 0:
                if self.background is None or self.background == 0:
                    thread_args.add(f'-threads {avail_threads - 1}')
                    return thread_args
                else:
                    thread_args.add(f'-threads {self.background}')
                    return thread_args
            elif 1 >= plex_clients > 0:
                thread_args.add(f'-threads {avail_threads // 1.5}')
                # if self.verbose:
                #     print(f'running with {(avail_threads // 1.5)} threads')
                return thread_args
            elif 2 >= plex_clients > 1:
                thread_args.add(f'-threads {avail_threads // 2}')
                # if self.verbose:
                #     print(f'running with {(avail_threads // 2)} threads')
                return thread_args

            elif plex_clients > 2:
                thread_args.add(f'-threads {avail_threads // 3}')
                # if self.verbose:
                #     print(f'running with {avail_threads // 3} threads')
                return thread_args
        else:
            if self.background is None or self.background == 0:
                return None
            else:
                thread_args.add(f'-threads {self.background}')
                return thread_args

    @staticmethod
    def ffmpeg_video_conversion_argument(json_file_meta: json):
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

    @staticmethod
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

    @staticmethod
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

    def sani_string(self, s_input: str):
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
        r = ('\'' + "\\'" + "\'")
        s_input = str(s_input).replace("\'", r)

        return s_input
