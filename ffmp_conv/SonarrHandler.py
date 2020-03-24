import logging
from collections import deque
from typing import Dict, Deque, List, Tuple

from asgiref.sync import sync_to_async
from hm_wrapper.sonarr import Sonarr

from . import _utils
from .FilePreferences import FilePreferences, defaults
from ._utils import try_until_async


class QueueEmptyException(IndexError):
    def __init__(self):
        pass


class SonarrHandler(object):
    def __init__(self, sonarr: Sonarr, conversion_profiles: dict = None):

        if conversion_profiles is None:
            conversion_profiles = defaults
        self.__sonarr_series_cache = None
        self._sonarr_series_queue: Deque[Tuple[int, int]] = deque()
        self.__sonarr_file_queue: Deque[Tuple[str, int]] = deque()

        self.sonarr = sonarr

        # Generate a file preferences object for each conversion profile
        self._quality_mappings: Dict[int, FilePreferences] = dict()
        c_lookup = _utils.generate_conversion_lookup_sonarr(sonarr=self.sonarr,
                                                            conversion_profiles=conversion_profiles)
        for k, v in c_lookup.items():
            self._quality_mappings[k] = FilePreferences(**v)
        logging.debug(self._quality_mappings)
        # self.sonarr_profile_map = _utils.generate_conversion_lookup_sonarr(sonarr=self.sonarr,
        #                                                                    conversion_profiles=defaults)

    def _sonarr_series_cache(self):
        if self.__sonarr_series_cache is None:
            try:
                self.__sonarr_series_cache = self.sonarr.get_series()
            except Exception as ex:
                logging.exception(ex)
                raise

        for series in self.__sonarr_series_cache:
            quality_id = series['qualityProfileId']
            series_id = series['id']
            vee = (series_id, quality_id)
            self._sonarr_series_queue.append(vee)

    @try_until_async(QueueEmptyException)
    async def get_next_sonarr_group(self):

        if self.sonarr is None:
            raise
        if self.__sonarr_series_cache is None:
            self._sonarr_series_cache()
        elif self._sonarr_series_queue is None:
            sync_to_async(self._sonarr_series_cache)()

        try:
            s, q = self._sonarr_series_queue.popleft()
            files: list = self.sonarr.get_episode_files_by_series_id(s)
            if files is not None and len(files) > 0:
                try:
                    for f in files:
                        self.__sonarr_file_queue.append((str(f['path']), int(f['quality']['quality']['id'])))
                except:
                    pass
                return
            else:
                raise QueueEmptyException
        except QueueEmptyException:
            raise QueueEmptyException
        except IndexError:
            raise IndexError
        except Exception as ex:
            logging.exception(ex)
            raise

    @try_until_async(QueueEmptyException)
    async def get_next_sonarr_file(self) -> Tuple[List[str], str, str, str]:
        """
        gets the next file off of tSonarrHandler.pyhe queue and runs it through it's corresponding quality
        profile FilePreferences object

        @return list of args, original file name/path, intermediate name/path , output file name/path
        @rtype:
        """
        try:
            file_path, p = self.__sonarr_file_queue.popleft()
            if file_path is None:
                print("null error at filepath")
            a = await self._quality_mappings[p].generate_args_from_filepath(file_path)
            if a is None:
                logging.exception(f'returned null filepath args {a}')
                raise TypeError
            return a
        except IndexError:
            logging.info(" sonarr file queue empty, attempting to refill")
            try:
                await self.get_next_sonarr_group()
                raise QueueEmptyException
            except QueueEmptyException:
                raise QueueEmptyException
            except IndexError:
                raise IndexError
