import logging
import os
from collections import deque
from typing import Dict, Deque, List, Tuple

from asgiref.sync import sync_to_async
from hm_wrapper.radarr import Radarr

from . import _utils
from .FilePreferences import FilePreferences, defaults
from ._utils import try_until_async


class QueueEmptyException(IndexError):
    def __init__(self):
        pass


class RadarrHandler(object):
    def __init__(self, radarr: Radarr, conversion_profiles: dict = defaults):

        self.__radarr_cache = None
        self.__radarr_file_queue: Deque[Tuple[str, int]] = deque()

        self.radarr = radarr

        # Generate a file preferences object for each conversion profile
        self._quality_mappings: Dict[int, FilePreferences] = dict()
        for k, v in _utils.generate_file_quality_mappings_list_radarr(self.radarr,
                                                                      conversion_profiles=conversion_profiles).items():
            self._quality_mappings[k] = FilePreferences(v)

        # self.radarr_profile_map = _utils.generate_file_quality_mappings_list_sonarr(radarr=self.radarr,
        #                                                                      conversion_profiles=defaults)

    def _get_radarr_cache(self):
        if self.__radarr_cache is None:
            try:
                self.__radarr_cache = self.radarr.get_movie()
            except Exception as ex:
                logging.exception(ex)
                raise

        for movie in self.__radarr_cache:
            # Skip if movie entry doesn't have a file to process
            if not movie['hasFile']:
                continue

            quality_id = movie['qualityProfileId']
            file_path = os.path.join(movie['path'], movie['movieFile']['relativePath'])
            vee = (file_path, quality_id)
            self.__radarr_file_queue.append(vee)
        return

    @try_until_async(QueueEmptyException)
    async def get_next_radarr_file(self) -> Tuple[List[str], str, str, str]:
        """
        gets the next file off of tRadarrHandler.pyhe queue and runs it through it's corresponding quality
        profile FilePreferences object

        @return list of args, original file name/path, intermediate name/path , output file name/path
        @rtype:
        """
        try:
            file_path, p = self.__radarr_file_queue.popleft()
            return await self._quality_mappings[p].generate_args_from_filepath(file_path)
        except IndexError:
            logging.info(" radarr file queue empty, attempting to refill")
            try:
                sync_to_async(self._get_radarr_cache())
                raise QueueEmptyException
            except QueueEmptyException:
                raise QueueEmptyException
            except IndexError:
                raise IndexError
        except Exception as ex:
            logging.exception(ex)
