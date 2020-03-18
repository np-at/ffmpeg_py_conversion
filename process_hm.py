import logging

import ffmp_conv
from ffmp_conv.converter import Converter
import os
import hm_wrapper

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


class FilePreferences(object):
    def __init__(self, target_bitrate: int, audio_channels: int, acodec: str, , container_type: str,
                 language: str, vcodec: str, audio_language: str, fps: int, fps_tolerance: int = 6, subtitle_language: str = None):
        """

        @param target_bitrate:
        @param audio_channels:
        @param acodec:
        @param container_type:
        @param language:
        @param vcodec:
        @param fps:
        @param fps_tolerance: Deviation form desired fps that is acceptable
        """
        self.subtitle_language = subtitle_language
        self.audio_language = audio_language
        self.vcodec = vcodec
        self.language = language
        self.container_type = container_type
        self.fps = fps
        self.fps_tolerance = fps_tolerance
        self.acodec = acodec
        self.audio_channels = audio_channels
        self.target_bitrate = target_bitrate

    def compare(self, probe_meta: dict) -> dict:
        target_args = dict()
        for stream in probe_meta['streams']:
            # compare video preferences
            if stream['codec_type'] == 'video':
                if self.vcodec is not None:
                    if v := stream['codec_name'] != self.vcodec:
                        target_args["vcodec"] = self.vcodec
                if self.fps is not None:
                    file_fps: float
                    fps_frac = stream['r_frame_rate']
                    if len(fps_frac) == 0:
                        file_fps = fps_frac
                    else:
                        split_frac = fps_frac.split('/')
                        file_fps = int(split_frac[0]) / int(split_frac[1])
                    if abs(self.fps - file_fps) >= self.fps_tolerance:
                        target_args['framerate'] = 24
            if stream['codec_type'] == 'audio':
                if self.audio_channels is not None:
                    if stream['channels'] != self.audio_channels:
                        target_args['ac'] = self.audio_channels
                    pass
                if self.acodec is not None:
                    if stream['acodec'] != self.acodec:
                        target_args['acodec'] = self.acodec
                    pass
                if self.audio_language is not None:
                    try:
                        if stream['tags']['language'] != self.audio_language:
                            target_args[]
                    except Exception as ex:
                        logging.exception(ex)
                        pass

                elif self.language is not None:
                    try:
                        if stream['tags']['language'] != self.language:
                            target_args[]
                    except Exception as ex:
                        logging.exception(ex)
                        pass
#       TODO: Bitrate comparison
#       TODO: Container comparison
#       TODO: Subtitle comparison
#       TODO: Stream specific settings mapping (eg 0:2:audio etccc)



def setup():
    s = hm_wrapper.sonarr.Sonarr()


if __name__ == '__main__':
    ffmp_conv.main()
