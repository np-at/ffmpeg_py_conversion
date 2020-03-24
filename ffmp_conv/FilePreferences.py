import logging
import re
from typing import Tuple, List

from . import _utils

defaults = {
    "Any": {
        "name": "Any",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"

    },
    "720p": {
        "name": "720p",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "1080p": {
        "name": "1080p",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "fps_tolerance": 6,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "SD": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },

    "Unknown": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "SDTV": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "WEBDL-480p": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "DVD": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "HDTV-720p": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "HDTV-1080p": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "Raw-HD": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "WEBDL-720p": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "Bluray-720p": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "WEBDL-1080p": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "Bluray-1080p": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "HDTV-2160p": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "WEBDL-2160p": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    },
    "Bluray-2160p": {
        "name": "SD",
        "target-bitrate": None,
        "audio-channels": 2,
        "acodec": "aac",
        "fps": 24,
        "container_type": "mkv",
        "language": "eng",
        "vcodec": "h264"
    }

}


class FilePreferences(object):
    def __init__(self, target_bitrate: int = None,
                 audio_channels: int = None,
                 acodec: str = None,
                 container_type: str = None,
                 language: str = None,
                 vcodec: str = None,
                 audio_language: str = None,
                 fps: int = None,
                 fps_tolerance: int = 6,
                 target_bitrate_tolerance: int = 1,
                 subtitle_language: str = None,
                 preset_preference: str = "slow",
                 **kwargs):
        """

        @type vcodec: str
        @type preset_preference: str
        @param target_bitrate:
        @param audio_channels:
        @param acodec: str
        @param container_type: str
        @param language: str
        @param vcodec: str
        @param fps: int
        @param fps_tolerance: int Deviation form desired fps that is acceptable
        """
        self.preset_preference = preset_preference
        self.target_bitrate_tolerance = target_bitrate_tolerance
        self.subtitle_language = subtitle_language
        self.audio_language = audio_language
        self.vcodec = vcodec
        self.language = language
        if container_type is not None and container_type.__contains__('mkv'):
            self.container_type = "Matroska / WebM"
            self.container_type_suffix = 'mkv'
        else:
            self.container_type = container_type
        self.fps = fps
        self.fps_tolerance = fps_tolerance
        self.acodec = acodec
        self.audio_channels = audio_channels
        self.target_bitrate = target_bitrate

        self.mkv_re: re = re.compile(r"\.mkv$")
        self.mp4_re: re = re.compile(r"\.mp4$")
        self.extension_re = re.compile(r'(?<=\.)([\s\S]{3})$')
        self.output_filename_re = re.compile(r'(\.copy)(?=\.[\s\S]{3}$)')

    async def generate_args_from_filepath(self, file_path: str, sonarr_quality_profile: int = None,
                                    radarr_quality_profile: int = None, **kwargs) -> Tuple[List[str], str, str, str]:
        """
        @return args, input_filename, intermediate_filename, output_filename: Tuple[List[str], str, str, str]
        @rtype: Tuple[List[str], str, str, str]
        @param file_path: str
        @param sonarr_quality_profile: str
        @param radarr_quality_profile: str
        """
        probe_results: dict
        try:
            r = await _utils.probe_async(filename=file_path, analyzeduration='800M', probesize='800M')
            probe_results = r
        except _utils.Error as ex:
            logging.exception(ex.stderr)
            raise
        input_filename: str = file_path

        cmds, intermediate_filename = self.compare(probe_results, input_filename)
        output_filename = self.output_filename_re.sub('', intermediate_filename)
        args = ['ffmpeg', '-i', input_filename]
        args += _utils.convert_kwargs_to_cmd_line_args(kwargs=cmds)
        args += _utils.convert_kwargs_to_cmd_line_args(kwargs=kwargs)
        # args += intermediate_filename
        # args += output_filename
        logging.debug(f"args are {args}; input_filename is {input_filename}; intermediate filename is {intermediate_filename}; output_filename is {output_filename}")
        return (args, input_filename, intermediate_filename, output_filename)

    def compare(self, probe_meta: dict, input_file_path: str) -> Tuple[iter, str]:
        target_args = list()

        st: list = probe_meta['streams']
        streams: list = list(st)
        streams.sort(key=_utils.sortIndex)
        audio_streams = list(filter(lambda x: x['codec_type'] == 'audio', streams))
        video_streams = list(filter(lambda x: x['codec_type'] == 'video', streams))
        subtitle_streams = list(filter(lambda x: x['codec_type'] == 'subtitle', streams))
        if video_streams is not None and len(video_streams) > 0:
            # # check if video codec conversion is required
            # video_codecs: set = set(filter(lambda x: x['codec_name'] != self.vcodec, video_streams))
            # if video_codecs is not None and len(video_codecs) > 1:
            #     target_args.append(('vcodec', 'copy'))
            for stream in video_streams:
                target_args.extend(
                    self.process_video_stream_args(video_stream=stream, video_stream_index=video_streams.index(stream)))

        # set default audio stream
        if audio_streams is not None and len(audio_streams) > 0:
            try:
                if len(audio_streams) > 1:
                    eng_streams = list(filter(lambda x: x['tags']['language'] == 'eng', audio_streams))
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
                        remove_defaults_list = list(filter(lambda x: x['disposition']['default'] == 1, audio_streams))
                        try:
                            remove_defaults_list.remove(eng_streams[0])
                        except ValueError:
                            pass
                        if len(remove_defaults_list) >= 1:
                            for r in remove_defaults_list:
                                target_args.append((f"disposition:{r['index']}", 0))
                        if eng_streams[0]['disposition']['default'] == 0:
                            target_args.append((f"-disposition:{eng_streams[0]['index']}", "default"))
            except Exception as ex:
                logging.error(ex)

            # standard audio stream specific arg processing
            for stream in audio_streams:
                target_args.extend(
                    self.process_audio_stream(stream=stream, stream_type_index=audio_streams.index(stream)))
        else:
            target_args.append(("acodec", "copy"))

        # subtitle arg processing
        for stream in subtitle_streams:
            target_args.extend(
                self.process_subtitle_stream_args(stream=stream, stream_type_index=subtitle_streams.index(stream)))
            pass

        # non- stream specific args section
        format_data = probe_meta['format']
        if self.target_bitrate is not None:

            bits_per_second = format_data['bit_rate']
            megabits_per_second = int(bits_per_second) // 1000000
            if abs(int(megabits_per_second) - self.target_bitrate) >= self.target_bitrate_tolerance:
                target_args.append(('bitrate', self.target_bitrate))

        if self.container_type is not None:
            intermediate_filename = self.extension_re.sub(f'copy.{self.container_type_suffix}', input_file_path)
        else:
            if len(current_extension := self.extension_re.findall(input_file_path)[0]) > 0:
                intermediate_filename = self.extension_re.sub(f'copy.{current_extension}', input_file_path)
            else:
                raise IndexError
        # Add generic args
        target_args.append(('max_muxing_queue_size', 9999))
        target_args.append(('preset', self.preset_preference))
        target_args.append(('vsync', 2))
        return target_args, intermediate_filename

    def process_audio_stream(self, stream, stream_type_index: int) -> list:
        """

        @param stream:
        @param stream_type_index:
        @return:
        """
        stream_audio_args = list()
        if self.audio_channels is not None:
            if stream['channels'] != self.audio_channels:
                stream_audio_args.append((f'ac:{stream_type_index}', self.audio_channels))
        return stream_audio_args

    def process_video_stream_args(self, video_stream, video_stream_index: int) -> list:
        """

        @param video_stream:
        @param video_stream_index:
        @return:
        """
        video_args = list()
        # compare video preferences
        if self.vcodec is not None:
            if video_stream['codec_name'] != self.vcodec:
                video_args.append((f"c:v:{video_stream_index}", self.vcodec))
        else:
            video_args.append((f"c:v:{video_stream_index}", "copy"))
        if self.fps is not None:
            file_fps: float
            fps_frac = video_stream['r_frame_rate']
            if len(fps_frac) == 0:
                file_fps = fps_frac
            else:
                split_frac = fps_frac.split('/')
                file_fps = int(split_frac[0]) / int(split_frac[1])
            if abs(self.fps - file_fps) >= self.fps_tolerance:
                video_args.append(('framerate', 24))

        #  If there is an embedded image just get rid of it for now
        try:
            if mimetype := video_stream['tags']['mimetype'] is not None:
                if mimetype == 'image/jpeg':
                    video_args.append(('map', f'-0:{video_stream["index"]}'))
            pass
        except KeyError:
            pass
        except Exception as ex:
            logging.exception("error")
            pass
        return video_args

    @staticmethod
    def process_subtitle_stream_args(stream, stream_type_index: int) -> list:
        stream_subtitle_args = list()
        #         if self.subtitle_language is not None:
        # if stream['tags']['language'] != self.subtitle_language:
        #         stream_subtitle_args.append(())
        # TODO: this
        return stream_subtitle_args

#         TODO: container type change arguments

#
#       TODO: Subtitle comparison
#       TODO: Stream specific settings mapping (eg 0:2:audio etccc)
