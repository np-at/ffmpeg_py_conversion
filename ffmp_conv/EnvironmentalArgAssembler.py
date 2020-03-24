import logging
import os

import psutil as psutil
from plexapi.server import PlexServer

from ._utils import PSUTIL_PRESENCE


class EnvironmentalArgAssembler(object):
    def __init__(self, plex: PlexServer = None, adaptive: bool = False, background: int = 0,
                 cpu_threshold: int = None, **kwargs):
        self.cpu_threshold = cpu_threshold
        self.PSUTIL_PRESENCE: bool = PSUTIL_PRESENCE

        self.adaptive = adaptive
        self.background = background
        self.other_args = kwargs
        self.plex = plex

    def cpu_usage_threshold(self) -> bool:
        if self.PSUTIL_PRESENCE is False or self.cpu_threshold is None:
            return True
        else:
            if cp := psutil.cpu_percent() > self.cpu_threshold:
                logging.info(
                    f"cpu percentage of {cp}% is above threshold of {self.cpu_threshold}%, deferring execution"
                )
                return False
            else:
                return True

    def ffmpeg_adaptive_thread_count_argument(self) -> list:
        if self.adaptive is None or not self.adaptive:
            return list()
        avail_threads = os.cpu_count()
        thread_args = list()

        if self.plex is None:
            # assume no user based throttling
            logging.warning(f"adaptive thread adjustment requested but no plex object present, continuing without"
                            f" thread adjustment")
            plex_clients = 0
            thread_args.extend([f'-threads', f"{avail_threads}"])
            return thread_args
        else:
            plex_clients = self.plex.sessions()
        if self.adaptive:
            if plex_clients == 0:
                if self.background is None or self.background == 0:
                    thread_args.extend([f'-threads', f'{avail_threads - 1}'])
                    return thread_args
                else:
                    thread_args.extend([f'-threads', f'{self.background}'])
                    return thread_args
            elif 1 >= plex_clients > 0:
                thread_args.extend([f'-threads', f'{avail_threads // 1.5}'])
                # if self.verbose:
                #     print(f'running with {(avail_threads // 1.5)} threads')
                return thread_args
            elif 2 >= plex_clients > 1:
                thread_args.extend([f'-threads', f'{avail_threads // 2}'])
                # if self.verbose:
                #     print(f'running with {(avail_threads // 2)} threads')
                return thread_args

            elif plex_clients > 2:
                thread_args.extend([f'-threads', f'{avail_threads // 3}'])
                # if self.verbose:
                #     print(f'running with {avail_threads // 3} threads')
                return list(thread_args)
        else:
            if self.background is None or self.background == 0:
                return list()
            else:
                thread_args.extend([f'-threads', f'{self.background}'])
                return thread_args
    #
    # def argument_assembly(self, file_name: str, json_file_meta: json) -> (str, str, int):
    #     """
    #
    #     @param file_name:
    #     @param json_file_meta:
    #     @return string with joined arguments, new file name, status code (0=OK, 1=Exception, 3= Do not need to convert)
    #     """
    #     san_file_name = sani_string(str(file_name))
    #     mp4 = re.compile(".mp4$|.mkv$")
    #     mkv = re.compile(".mkv$")
    #     mm = re.compile(".mkv$|.mp4$")
    #     if mp4.search(san_file_name) is not None:
    #         container_type = ".mp4"
    #     elif mkv.search(san_file_name) is not None:
    #         container_type = ".mkv"
    #     else:
    #         container_type = ".mkv"
    #
    #     arg_list = list()
    #
    #     t_args = self.ffmpeg_adaptive_thread_count_argument()
    #     if t_args is not None:
    #         arg_list.extend(t_args)
    # @staticmethod
    # def ffmpeg_video_conversion_argument(json_file_meta: json):
    #     # define the rules for video conversion here
    #     try:
    #         video_args = set()
    #         streams = json_file_meta['streams']
    #
    #         for s in streams:
    #             try:
    #                 if s['codec_type'] == 'video':
    #                     # currently only care about it being h264
    #                     # TODO: add resolution and fps
    #
    #                     if s['codec_name'] != 'h264':
    #                         video_args.add('-vcodec h264')
    #                     fps: float
    #                     fps_frac = s['r_frame_rate']
    #                     if len(fps_frac) == 0:
    #                         fps = fps_frac
    #                     else:
    #                         split_frac = fps_frac.split('/')
    #                         fps = int(split_frac[0]) / int(split_frac[1])
    #                     if fps >= 32:
    #                         video_args.add('-framerate 24')
    #                     try:
    #                         if s['tags'] is not None:
    #                             if s['tags']['mimetype'] is not None:
    #                                 if s['tags']['mimetype'] == 'image/jpeg':
    #                                     video_args.add(f"-map -0:{s['index']}")
    #
    #                     except Exception as ex:
    #                         pass
    #                 else:
    #                     pass
    #             except Exception as ex:
    #                 logging.error(f"error processing video args: {ex}")
    #         if len(video_args) == 0:
    #             return None
    #         else:
    #             video_args.add('-vsync 2')
    #             video_args.add('-r 24')
    #             video_args.add('-max_muxing_queue_size 9999')
    #             video_args.add('-preset slow')
    #             return video_args
    #     except Exception as ex:
    #         logging.error(f"error processing video args: {ex}")
    #
    # @staticmethod
    # def ffmpeg_audio_conversion_argument(json_file_meta):
    #     # define the rules for audio conversion here
    #     audio_args = set()
    #
    #     try:
    #         streams = json_file_meta['streams']
    #
    #         for s in streams:
    #             if s['codec_type'] == 'audio':
    #                 # we want everything to be in 2 channel aac
    #                 if s['codec_name'] != 'aac':
    #                     audio_args.add("-acodec aac")
    #                 if s['channels'] != 2:
    #                     audio_args.add("-ac 2")
    #             else:
    #                 pass
    #     except Exception as ex:
    #         logging.error(f"error processing audio args; error: {ex}")
    #
    #     other_args_present: bool
    #     if len(audio_args) == 0:
    #         other_args_present = False
    #     else:
    #         other_args_present = True
    #     try:
    #         # if there are multiple audio streams, and one has language= english, then set it as the default stream for
    #         # playback
    #         audio_stream_list = list(
    #             filter(lambda x: x['codec_type'] == 'audio' and x['tags']['language'] is not None, streams))
    #         if len(audio_stream_list) > 1:
    #             eng_streams = list(filter(lambda x: x['tags']['language'] == 'eng', audio_stream_list))
    #             if len(eng_streams) > 1:
    #                 # look for "commentary in the list of english streams to weed out commentary tracks"
    #                 for s in eng_streams:
    #                     track_title = s['tags']['title']
    #                     if track_title is not None:
    #                         commentary = re.search("commentary", str(track_title), re.RegexFlag.IGNORECASE)
    #                         if commentary is not None:
    #                             eng_streams.remove(s)
    #
    #             if len(eng_streams) == 1:
    #                 # remove the default designation from all audio streams except our chosen one
    #                 remove_default_list = list(filter(lambda x: x['disposition']['default'] == 1, audio_stream_list))
    #                 try:
    #                     remove_default_list.remove(eng_streams[0])
    #                 except ValueError:
    #                     pass
    #                 if len(remove_default_list) >= 1:
    #                     for r in remove_default_list:
    #                         audio_args.add(f"-disposition:{r['index']} 0")
    #                 if eng_streams[0]['disposition']['default'] == 0:
    #                     audio_args.add(f"-disposition:{eng_streams[0]['index']} default")
    #     except Exception as ex:
    #         logging.error(ex)
    #
    #     if len(audio_args) == 0:
    #         return None
    #
    #     if other_args_present is False:
    #         audio_args.add("-acodec copy")
    #
    #     return audio_args
    #
    # @staticmethod
    # def ffmpeg_subtitle_conversion_argument(json_file_meta, container_type: str):
    #     # define the rules for audio conversion here
    #     # if re.search(".mkv$", containerType) is None:
    #     try:
    #         subtitle_args = set()
    #         streams = json_file_meta['streams']
    #         for s in streams:
    #             if s['codec_type'] == 'subtitle':
    #                 if s['codec_name'] == 'dvd_subtitle' or s['codec_name'] == 'hdmv_pgs_subtitle':
    #                     subtitle_args.add(f'-scodec copy')
    #
    #                 #  subtitle_args.add(f"-map -0:{s['index']}")
    #
    #                 # remove subtitle stream mappings
    #                 # if s['channels'] != 2:
    #                 #     subtitle_args.append("-ac 2")
    #
    #                 # for now just copy subtitles
    #
    #                 # if len(subtitle_args) == 0:
    #                 # tell it not to map subtitles, mp4 doesn't support them as streams anyway
    #                 #  subtitle_args.append("-scodec copy")
    #             else:
    #                 pass
    #         return subtitle_args
    #     except Exception as ex:
    #         print(ex)
    #         logging.error(f'error: {ex}')
