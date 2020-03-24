from typing import Dict, Any

defaults: dict = {
    "Any": {
        "name": "Any",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container": "mkv",
        "language": "eng",
        "vcodec": "h264"

    },
    "720p": {
        "name": "720p",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "1080p": {
        "name": "1080p",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "SD": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container": "mkv",
        "language": "eng",
        "vcodec": "h264"
    }
}

g_vars: Dict[Any, str] = dict(SONARR_URL=None,
                              SONARR_API_KEY=None,
                              RADARR_URL=None,
                              RADARR_API_KEY=None,
                              PLEX_URL=None,
                              PLEX_TOKEN=None,
                              TARGET_VCODEC='h264',
                              TARGET_ACODEC='aac',
                              TARGET_CHANNELS=2,
                              TARGET_FPS=24,
                              TARGET_CONTAINER='.mkv',
                              TARGET_LANG='eng'
                              )

#
# class Runner(object):
#     def __init__(self, conversion_preferences: dict = defaults, sonarr: Sonarr = None, radarr: Radarr = None):
#         self.sonarr = sonarr
#         self.radarr = radarr
#         self.path_setting_map = _utils.generate_file_quality_mappings_list_sonarr(self.sonarr, conversion_preferences)
#
#     def process_sonarr_files(self):
#         if self.sonarr is None:
#             raise AssertionError
#         else:
#
#             for file in self.path_setting_map:
#                 file_meta = None
#                 try:
#                     file_meta = probe(filename=file, probesize="800M", analyzeduration="800M")
#                 except Exception as ex:
#                     logging.exception(f"error during probe of {file}")
#                     continue
#
#     def argument_assembly_against_preferences(self, file_name: str, json_file_meta: json) -> (str, str, int):
#         """
#
#         @param file_name:
#         @param json_file_meta:
#         @return string with joined arguments, new file name, status code (0=OK, 1=Exception, 3= Do not need to convert)
#         """
#         san_file_name = _utils.sani_string(str(file_name))
#         mp4 = re.compile(".mp4$|.mkv$")
#         mkv = re.compile(".mkv$")
#         mm = re.compile(".mkv$|.mp4$")
#         if mp4.search(san_file_name) is not None:
#             container_type = ".mp4"
#         elif mkv.search(san_file_name) is not None:
#             container_type = ".mkv"
#         else:
#             container_type = ".mkv"
#
#         arg_list = list()
#         arg_list.append("-y")
#         arg_list.append("-map 0")
#         arg_list.append("-copy_unknown")
#         arg_list.append('-analyzeduration 800M')
#         arg_list.append('-probesize 800M')
#
#         v_args = ffmpeg_video_conversion_argument(json_file_meta)
#         if v_args is not None:
#             arg_list.extend(v_args)
#         elif v_args is None:
#             arg_list.append('-vcodec copy')
#         a_args = _utils.ffmpeg_audio_conversion_argument(json_file_meta)
#         if a_args is not None:
#             arg_list.extend(a_args)
#         elif a_args is None:
#             arg_list.append('-acodec copy')
#         s_args = self.ffmpeg_subtitle_conversion_argument(json_file_meta, container_type)
#         if s_args is not None:
#             arg_list.extend(s_args)
#         t_args = self.ffmpeg_adaptive_thread_count_argument()
#         if t_args is not None:
#             arg_list.extend(t_args)
#         # if self.background is not None:
#         #     argList.append(f'-threads {self.background}')
#         # force file overwrite
#         # argList.append("-map_metadata 0")
#         # add input file
#         # if self.verbose == True:
#         #     logging.debug(f"v_args is {v_args}; a_args is {a_args}; file ends with .mp4 bools is
#         #     {sanitizedFileName.endswith('.mp4')}")
#         if v_args is None and a_args is None and mm.search(san_file_name) is not None:
#             # if all three conditions are met, then we don't need to convert
#             return None, None, 3
#         separator = " "
#         temp_file_name = str()
#         if mm.search(san_file_name) is not None:
#             temp_file_name = san_file_name + '.converting' + container_type
#             # assemble ffmpeg command with argument list and output file name
#             joined_arg_string = f"ffmpeg -i \'{san_file_name}\' {separator.join(arg_list)} \'{temp_file_name}\' "
#         else:
#             temp_file_name = san_file_name + '.converting.mkv'
#             joined_arg_string = f"ffmpeg -i \'{san_file_name}\' {separator.join(arg_list)} \'{temp_file_name}\' "
#
#         # if self.verbose == True:
#         print(f'{joined_arg_string}')
#         logging.debug(joined_arg_string)
#         return joined_arg_string, temp_file_name
#
#     def ffmpeg_video_conversion_argument(self, json_file_meta: json, ):
#         # define the rules for video conversion here
#         try:
#             video_args = set()
#             streams = json_file_meta['streams']
#
#             for s in streams:
#                 try:
#                     if s['codec_type'] == 'video':
#                         # currently only care about it being h264
#                         # TODO: add resolution and fps
#
#                         if s['codec_name'] != 'h264':
#                             video_args.add('-vcodec h264')
#                         fps: float
#                         fps_frac = s['r_frame_rate']
#                         if len(fps_frac) == 0:
#                             fps = fps_frac
#                         else:
#                             split_frac = fps_frac.split('/')
#                             fps = int(split_frac[0]) / int(split_frac[1])
#                         if fps >= 32:
#                             video_args.add('-framerate 24')
#                         try:
#                             if s['tags'] is not None:
#                                 if s['tags']['mimetype'] is not None:
#                                     if s['tags']['mimetype'] == 'image/jpeg':
#                                         video_args.add(f"-map -0:{s['index']}")
#
#                         except Exception as ex:
#                             pass
#                     else:
#                         pass
#                 except Exception as ex:
#                     logging.error(f"error processing video args: {ex}")
#             if len(video_args) == 0:
#                 return None
#             else:
#                 video_args.add('-vsync 2')
#                 video_args.add('-r 24')
#                 video_args.add('-max_muxing_queue_size 9999')
#                 video_args.add('-preset slow')
#                 return video_args
#         except Exception as ex:
#             logging.error(f"error processing video args: {ex}")
