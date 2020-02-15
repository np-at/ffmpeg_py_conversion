import logging
import os
import re
import shlex
import shutil
import subprocess
from typing import Dict, Any

from ffmpeg._probe import probe

from ._utils import ArgAssembler

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


class Converter(object):

    def __init__(self,
                 SONARR_URL=None,
                 SONARR_API_KEY=None,
                 RADARR_URL=None,
                 RADARR_API_KEY=None,
                 PLEX_URL=None,
                 PLEX_TOKEN=None,
                 VERBOSE=None,
                 **kwargs):
        """

        @param kwargs:
        """
        self.PLEX_URL = PLEX_URL
        self.RADARR_URL = RADARR_URL
        self.SONARR_API_KEY = SONARR_API_KEY
        self.RADARR_API_KEY = RADARR_API_KEY
        self.SONARR_URL = SONARR_URL
        self.PLEX_TOKEN = PLEX_TOKEN
        self.g_vars = g_vars
        self.verbose = VERBOSE
        self.arg = ArgAssembler(plex_url=self.PLEX_URL, plex_token=self.PLEX_TOKEN)
        for Key in g_vars:
            for k, v in kwargs:
                if str(Key).lower() == str(k).lower():
                    self.g_vars[Key] = v

    def try_process_file(self, file_str) -> (int, str):
        """

        @param file_str:
        @return: return code, new file name (full path)
        return code 0 = success
        return code 1 = general error
        return code 2 = valid file, processing was not neccessary as it met criteria
        return code 3 = not a valid video file or otherwise unable to probe
        """
        from pathlib import Path
        file = Path(file_str)
        if not Path.exists(file):
            raise FileNotFoundError()
        else:
            file_meta = str()
            try:
                file_meta = probe(file, analyzeduration='800M', probesize='800M')
                has_video_stream = False
                for stream in file_meta['streams']:
                    if stream['codec_type'] == 'video':
                        has_video_stream = True
                if has_video_stream is not True:
                    return 3, None
            except Exception as ex:
                return 3, None
            try:
                com_args, temp_file_name, status_code = self.arg.argument_assembly(json_file_meta=file_meta,
                                                                                   file_name=file)
                if status_code == 3 or status_code == 1:
                    return 0, file
                else:
                    try:
                        conversion_process = subprocess.Popen(shlex.split(com_args),
                                                              shell=False)
                        status = conversion_process.wait()
                        if conversion_process.returncode != 0:

                            try:
                                os.remove(temp_file_name)
                            except IsADirectoryError:
                                logging.error(f"unable to remove {temp_file_name} as it is a directory")
                                pass
                            else:
                                logging.info(f"removed file {temp_file_name}")

                            return conversion_process.returncode, conversion_process.stderr
                        else:
                            rcode, new_file = self._post_process(file=str(file),
                                                                 container_type=g_vars['TARGET_CONTAINER'])
                            if rcode == 0:
                                return 0, new_file
                            else:
                                raise SystemError()
                    except:
                        pass

            except Exception as ex:
                logging.exception(ex)
                return 1, ex

    def _post_process(self, container_type, file) -> (int, str):
        """

        @param container_type:
        @param file:
        @return: (return code, the new file name/path)
        """
        try:
            # path is not literal, so we don't want the 'sanitized' version
            if container_type == '.mkv' or container_type == '.mp4':
                temp_file_name_unsanitized = file + '.converting' + container_type
            else:
                temp_file_name_unsanitized: str = file + '.converting.mkv'
            if re.search(".mkv$", file):
                new_file_name = file

                shutil.move(temp_file_name_unsanitized, new_file_name)
                if self.verbose:
                    print(f'moved {temp_file_name_unsanitized} over {new_file_name}')
                    logging.debug(f'moved {temp_file_name_unsanitized} over {new_file_name}')
            elif re.search(".avi$", file):
                new_file_name = file.strip(".avi")
                new_file_name += ".mp4"
                shutil.move(temp_file_name_unsanitized, new_file_name)
                if self.verbose:
                    print(f'moved {temp_file_name_unsanitized} over {new_file_name}')
                    logging.debug(f'moved {temp_file_name_unsanitized} over {new_file_name}')
            else:
                shutil.move(temp_file_name_unsanitized, file)
                if self.verbose:
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
                if self.verbose:
                    print(f'deleting original file: {file}')
                    logging.debug(f'deleting original file: {file}')

            logging.debug("completed processing of {}".format(file))
            return 0, new_file_name
