import asyncio
import logging
import os
import shutil
import sys
from asyncio import sleep
from typing import Dict, Any, List

from ffmp_conv.EnvironmentalArgAssembler import EnvironmentalArgAssembler
from ffmp_conv._utils import Error, _spawn, _spawn_async
from .RadarrHandler import RadarrHandler, QueueEmptyException
from .SonarrHandler import SonarrHandler

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


async def _run_file_async(cmds: List[str], init_file: str, intermediate_file: str, output_file: str):
    try:
        opfile = str(intermediate_file)
        # cmds += '-threads'
        # cmds += '12'
        cmds.append(opfile)
        # logging.debug(f" cmds are {cmds}")
        if cmds is None:
            raise TypeError
    except Exception as ex:
        logging.exception(ex)
        raise
    try:
        await _spawn_async(*cmds)
    except Error as er:
        logging.info(f"{init_file} failed to convert")
        logging.info(f"removing working conversion file {intermediate_file}")
        os.remove(intermediate_file)
        logging.error(er)
    except ChildProcessError as ex:
        logging.info(f"{init_file} failed to convert")
        logging.info(f"removing working conversion file {intermediate_file}")
        os.remove(intermediate_file)
        logging.exception(ex)
    except KeyboardInterrupt as ex:
        logging.exception(ex)
        logging.info(f"attempting graceful exit")
        logging.info(f"removing working conversion file {intermediate_file}")
        os.remove(intermediate_file)
        sys.exit(0)
    except Exception as ex:
        logging.exception(ex)
        logging.info(f"removing working conversion file {intermediate_file}")
        os.remove(intermediate_file)
    else:
        logging.info(f"{cmds[1]} converted")
        logging.debug(f"replacing original file with completed conversion: {output_file}")
        os.remove(init_file)
        shutil.move(intermediate_file, output_file)


def _run_file(cmds: List[str], init_file: str, intermediate_file: str, output_file: str):
    try:
        opfile = str(intermediate_file)
        cmds.append(opfile)
        logging.debug(f" cmds are {cmds}")
        if cmds is None:
            raise TypeError
    except Exception as ex:
        logging.exception(ex)
        raise
    try:
        _spawn(cmds=cmds)
    except Error as er:
        logging.info(f"{init_file} failed to convert")
        logging.info(f"removing working conversion file {intermediate_file}")
        os.remove(intermediate_file)
        logging.error(er)
    except ChildProcessError as ex:
        logging.info(f"{init_file} failed to convert")
        logging.info(f"removing working conversion file {intermediate_file}")
        os.remove(intermediate_file)
        logging.exception(ex)
    except KeyboardInterrupt as ex:
        logging.exception(ex)
        logging.info(f"attempting graceful exit")
        logging.info(f"removing working conversion file {intermediate_file}")
        os.remove(intermediate_file)
        sys.exit(0)
    except Exception as ex:
        logging.exception(ex)
        logging.info(f"removing working conversion file {intermediate_file}")
        os.remove(intermediate_file)
    else:
        logging.info(f"{cmds[1]} converted")
        logging.debug(f"replacing original file with completed conversion: {output_file}")
        os.remove(init_file)
        shutil.move(intermediate_file, output_file)


class Converter(object):
    def __init__(self,
                 sonarr_url=None,
                 sonarr_api=None,
                 radarr_url=None,
                 radarr_api=None,
                 plex_url=None,
                 plex_token=None,
                 adaptive: bool = False,
                 wait_fxn=lambda: True,
                 process_radarr_files=False,
                 process_sonarr_files=False,
                 **kwargs):
        """

        @param kwargs:
        """

        self.process_sonarr_files = process_sonarr_files
        self.process_radarr_files = process_radarr_files
        self.wait_fxn = wait_fxn
        self.plex = None
        self.env_arg_handler = None
        if plex_token is not None and plex_url is not None:
            try:
                from plexapi.server import PlexServer
                self.plex = PlexServer(baseurl=plex_url, token=plex_token)
                self.env_arg_handler = EnvironmentalArgAssembler(plex=self.plex, adaptive=adaptive)

            except Exception as ex:
                logging.exception(ex)

        self.radarr = None
        self.radarr_handler = None
        if radarr_url is not None and radarr_api is not None:
            try:
                from hm_wrapper.radarr import Radarr
                self.radarr = Radarr(radarr_url, radarr_api)
                self.radarr_handler = RadarrHandler(radarr=self.radarr)
            except Exception as ex:
                logging.exception(ex)

        self.sonarr = None
        self.sonarr_handler = None
        if sonarr_url is not None and sonarr_api is not None:
            try:
                from hm_wrapper.sonarr import Sonarr
                self.sonarr = Sonarr(host_url=sonarr_url, api_key=sonarr_api)
                self.sonarr_handler = SonarrHandler(sonarr=self.sonarr)
            except Exception as ex:
                logging.exception(ex)

        self.sonarr_profile_map = None
        self.g_vars = g_vars

    async def run_sonarr_file(self):
        """
        Gets next sonarr file off the queue (refreshes queue if needed) and attempts to convert it according to FilePreferences
        Raises NameError if Sonarr object was unable to be instantiated,
        Raises Error if conversion unsuccessful
        """
        if self.sonarr_handler is None:
            err = NameError(self.sonarr_handler)
            logging.exception(err)
            raise err

        try:
            tpl = await asyncio.create_task(self.sonarr_handler.get_next_sonarr_file())
        except Exception as ex:
            logging.exception(ex)
            raise
        (a, init_file, intermediate_file, output_file) = tpl
        try:
            await _run_file_async(cmds=a, init_file=init_file, intermediate_file=intermediate_file,
                                  output_file=output_file)
        except Error as ex:
            logging.exception(ex)
            raise
        except Exception as ex:
            logging.exception(ex)
            raise

    async def run_radarr_file(self):
        """
       Gets next radarr file off the queue (refreshes queue if needed) and attempts to convert it according to FilePreferences
       Raises NameError if Radarr object was unable to be instantiated,
       Raises Error if conversion unsuccessful
       """
        if self.radarr_handler is None:
            err = NameError(self.radarr_handler)
            logging.exception(err)
            raise err
        a, init_file, intermediate_file, output_file = await self.radarr_handler.get_next_radarr_file()
        try:
            await _run_file_async(cmds=a, init_file=init_file, intermediate_file=intermediate_file,
                                  output_file=output_file)
        except Error as ex:
            logging.exception(ex)
            raise

    async def Process(self):
        radarr_empty = False
        sonarr_empty = False
        while True:
            if self.wait_fxn():
                if self.process_radarr_files and not radarr_empty:
                    try:
                        await self.run_radarr_file()
                    except QueueEmptyException as ex:
                        logging.info(f"Radarr Queue Empty")
                        radarr_empty = True
                    except Exception as ex:
                        logging.exception(ex)
                        raise
            else:
                await sleep(delay=3)
            if self.wait_fxn():
                if self.process_sonarr_files and not sonarr_empty:
                    try:
                        await self.run_sonarr_file()
                    except QueueEmptyException as ex:
                        logging.info(f"Sonarr Queue Empty")
                        sonarr_empty = True
                    except Exception as ex:
                        logging.exception(ex)
                        raise
            if radarr_empty and sonarr_empty:
                logging.info(f"both queues exhausted, quitting")
                break
            else:
                await sleep(delay=3)
            await sleep(delay=5)
    # @staticmethod
    #     # async def _spawn(cmds):
    #     #     logging.debug('Spawning ffmpeg with command: ' + ' '.join(cmds))
    #     #     proc = await asyncio.create_subprocess_exec(
    #     #         cmds,
    #     #         stdout=asyncio.subprocess.PIPE,
    #     #         stderr=asyncio.subprocess.PIPE,
    #     #         shell=False
    #     #     )
    #     #     stdout, stderr = await proc.communicate()
    #     #     if stdout:
    #     #         print(f'[stdout]\n{stdout.decode()}')
    #     #     if stderr:
    #     #         print(f'[stderr]\n{stderr.decode()}')

    # def try_process_file(self, file_str) -> (int, str):
    #     """
    #
    #     @param file_str:
    #     @return: return code, new file name (full path)
    #     return code 0 = success
    #     return code 1 = general error
    #     return code 2 = valid file, processing was not neccessary as it met criteria
    #     return code 3 = not a valid video file or otherwise unable to probe
    #     """
    #     from pathlib import Path
    #     file = Path(file_str)
    #     if not Path.exists(file):
    #         raise FileNotFoundError()
    #     else:
    #         file_meta = str()
    #         try:
    #             file_meta = probe(file, analyzeduration='800M', probesize='800M')
    #             has_video_stream = False
    #             for stream in file_meta['streams']:
    #                 if stream['codec_type'] == 'video':
    #                     has_video_stream = True
    #             if has_video_stream is not True:
    #                 return 3, None
    #         except Exception as ex:
    #             return 3, None
    #         try:
    #             com_args, temp_file_name, status_code = self.arg.argument_assembly(json_file_meta=file_meta,
    #                                                                                file_name=file)
    #             if status_code == 3 or status_code == 1:
    #                 return 0, file
    #             else:
    #                 try:
    #                     conversion_process = os.subprocess.Popen(shlex.split(com_args),
    #                                                              shell=False)
    #                     status = conversion_process.wait()
    #                     if conversion_process.returncode != 0:
    #
    #                         try:
    #                             os.remove(temp_file_name)
    #                         except IsADirectoryError:
    #                             logging.error(f"unable to remove {temp_file_name} as it is a directory")
    #                             pass
    #                         else:
    #                             logging.info(f"removed file {temp_file_name}")
    #
    #                         return conversion_process.returncode, conversion_process.stderr
    #                     else:
    #                         rcode, new_file = self._post_process(file=str(file),
    #                                                              container_type=g_vars['TARGET_CONTAINER'])
    #                         if rcode == 0:
    #                             return 0, new_file
    #                         else:
    #                             raise SystemError()
    #                 except:
    #                     pass
    #
    #         except Exception as ex:
    #             logging.exception(ex)
    #             return 1, ex
    #
    # def _post_process(self, container_type, file) -> (int, str):
    #     """
    #
    #     @param container_type:
    #     @param file:
    #     @return: (return code, the new file name/path)
    #     """
    #     try:
    #         # path is not literal, so we don't want the 'sanitized' version
    #         if container_type == '.mkv' or container_type == '.mp4':
    #             temp_file_name_unsanitized = file + '.converting' + container_type
    #         else:
    #             temp_file_name_unsanitized: str = file + '.converting.mkv'
    #         if re.search(".mkv$", file):
    #             new_file_name = file
    #
    #             shutil.move(temp_file_name_unsanitized, new_file_name)
    #             if self.verbose:
    #                 print(f'moved {temp_file_name_unsanitized} over {new_file_name}')
    #                 logging.debug(f'moved {temp_file_name_unsanitized} over {new_file_name}')
    #         elif re.search(".avi$", file):
    #             new_file_name = file.strip(".avi")
    #             new_file_name += ".mp4"
    #             shutil.move(temp_file_name_unsanitized, new_file_name)
    #             if self.verbose:
    #                 print(f'moved {temp_file_name_unsanitized} over {new_file_name}')
    #                 logging.debug(f'moved {temp_file_name_unsanitized} over {new_file_name}')
    #         else:
    #             shutil.move(temp_file_name_unsanitized, file)
    #             if self.verbose:
    #                 print(f'moved {temp_file_name_unsanitized} over {file}')
    #                 logging.debug(f'moved {temp_file_name_unsanitized} over {file}')
    #             return 0, temp_file_name_unsanitized
    #     except Exception as ex:
    #         logging.critical(f"error during post processing; internal error: {ex}")
    #         print(f"error during post-processing; error: {ex}")
    #         return 1
    #     else:
    #         if file != new_file_name:
    #             os.remove(file)  # THIS WILL REMOVE THE NEW ONE IF NEWFILE NAME AND OLDFILE NAME ARE THE SAME!!!!
    #             if self.verbose:
    #                 print(f'deleting original file: {file}')
    #                 logging.debug(f'deleting original file: {file}')
    #
    #         logging.debug("completed processing of {}".format(file))
    #         return 0, new_file_name
