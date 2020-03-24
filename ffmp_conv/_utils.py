import asyncio
import functools
import json
import logging
import signal
import subprocess
from typing import Dict

from asgiref.sync import sync_to_async
from hm_wrapper.radarr import Radarr

try:
    import psutil as psutil

    PSUTIL_PRESENCE: bool = True
except:
    logging.warning("unable to import psutil: Please install it if you would like to scale threads to cpu usage")
    pass
from hm_wrapper.sonarr import Sonarr


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
    r = ('\'' + "\\'" + "\'")
    s_input = str(s_input).replace("\'", r)

    return s_input


def get_media_from_sonarr(sonarr: Sonarr, conversion_profiles: dict, strict_profile_checking: bool = False):
    return generate_conversion_lookup_sonarr(conversion_profiles, sonarr)
    #


def dictMap(f, xs):
    return dict((f(i), i) for i in xs)


#
# def generate_file_quality_mappings_list_sonarr(sonarr: Sonarr, conversion_profiles: dict,
#                                                strict_profile_checking: bool = False) -> dict:
#     """
#     Generates a list of dict objects key=video file path on system, value = the desired quality settings
#     corresponding to the profile defined by the user
#     @param sonarr:
#     @param conversion_profiles:
#     @param strict_profile_checking:
#     @return:
#     """
#
#     conversion_lookup = generate_conversion_lookup_sonarr(conversion_profiles, sonarr)
#     series = sonarr.get_series()
#     path_quality_mappings = dict()
#     for s in series:
#         quality_profile_settings = conversion_lookup[s['qualityProfileId']]
#         series_files = dict((p, quality_profile_settings) for p in list(
#             map(lambda x: x['path'], sonarr.get_episode_files_by_series_id(s['id']))))
#         path_quality_mappings.update(series_files)
#
#     return path_quality_mappings
#     # if strict_profile_checking:
#     conversion_profiles.keys().__contains__(s['qualityProfileId'])
# conversion_settings = conversion_profiles


def generate_file_quality_mappings_list_radarr(radarr: Radarr, conversion_profiles: Dict[str, dict]):
    k = dict()
    q = radarr.get_quality_profiles()
    final_dict = dict()
    try:
        for g in q:
            for y in g['items']:
                k[y['quality']['name']] = y['quality']['id']
    except Exception as ex:
        logging.exception(ex)
        raise

    for name, qid in k.items():
        for cname, profile_data in conversion_profiles.items():
            if str(name).lower().__eq__(cname.lower()):
                final_dict[qid] = profile_data

    return final_dict


def generate_conversion_lookup_sonarr(conversion_profiles: Dict[str, dict], sonarr: Sonarr):
    k = dict()
    q = sonarr.get_quality_profiles()
    final_dict = dict()
    try:
        for g in q:
            for y in g['items']:
                k[y['quality']['name']] = y['quality']['id']
    except Exception as ex:
        logging.exception(ex)
        raise

    for name, qid in k.items():
        for cname, profile_data in conversion_profiles.items():
            if str(name).lower().__eq__(cname.lower()):
                final_dict[qid] = profile_data

    return final_dict
    #
    # quality_profiles = sonarr.get_quality_profiles()
    # id_names = dict(map(lambda x: (x['name'], x['id']), quality_profiles))
    # profile_mapping = dict()
    # for i in id_names.keys():
    #     for p in conversion_profiles.keys():
    #         if str(i).lower() == str(p).lower():
    #             e = id_names[i]
    #             profile_mapping[e] = conversion_profiles[p]
    #             pass
    #         else:
    #             pass
    # return profile_mapping


def probe(filename, cmd='ffprobe', **kwargs):
    """Run ffprobe on the specified file and return a JSON representation of the output.

    Raises:
        :class:`ffmpeg.Error`: if ffprobe returns a non-zero exit code,
            an :class:`Error` is returned with a generic error message.
            The stderr output can be retrieved by accessing the
            ``stderr`` property of the exception.
    """
    args = [cmd, '-show_format', '-show_streams', '-of', 'json']
    args += convert_kwargs_to_cmd_line_args(kwargs)
    args += [filename]
    logging.debug(f"running ffprobe with args: {' '.join(args)}")
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    out, err = p.communicate()
    if p.returncode != 0:
        logging.exception(err)
        raise Error('ffprobe', out, err)
    return json.loads(out.decode('utf-8'))


async def probe_async(filename, cmd='ffprobe', **kwargs):
    """Run ffprobe on the specified file and return a JSON representation of the output.

    Raises:
        :class:`ffmpeg.Error`: if ffprobe returns a non-zero exit code,
            an :class:`Error` is returned with a generic error message.
            The stderr output can be retrieved by accessing the
            ``stderr`` property of the exception.
    """
    args = [cmd, '-show_format', '-show_streams', '-of', 'json']
    args += convert_kwargs_to_cmd_line_args(kwargs)
    args += [filename]
    args = list(args)
    logging.debug(f"running ffprobe with args: {' '.join(args)}")
    try:

        out: bytes = await _spawn_async(*args, return_output=True)
    except Exception as ex:
        logging.exception(ex)
        raise

    try:
        decodd_out = out.decode('utf-8')
        out_ob = await sync_to_async(json.loads)(decodd_out)

        return out_ob
    except Exception as ex:
        logging.exception(ex)


def escape_chars(text, chars):
    """Helper function to escape uncomfortable characters."""
    text = str(text)
    chars = list(set(chars))
    if '\\' in chars:
        chars.remove('\\')
        chars.insert(0, '\\')
    for ch in chars:
        text = text.replace(ch, '\\' + ch)
    return text


def convert_kwargs_to_cmd_line_args(kwargs) -> list:
    """Helper function to build command line arguments out of dict or list[tuple]."""
    args = []
    try:
        if isinstance(kwargs, dict):
            for k in sorted(kwargs.keys()):
                v = kwargs[k]
                args.append(f'-{k}')
                if v is not None:
                    args.append('{}'.format(v))
        elif isinstance(kwargs, list):
            for k, v in kwargs:
                args.append('-{}'.format(k))
                if v is not None:
                    args.append('{}'.format(v))
    except Exception as ex:
        logging.exception(ex)
    return args


class Error(Exception):
    def __init__(self, cmd, stdout, stderr):
        super(Error, self).__init__(
            '{} error (see stderr output for detail)'.format(cmd)
        )
        self.stdout = stdout
        self.stderr = stderr


def sortIndex(val) -> int:
    return int(val['index'])


def try_until_async(expected_exception):
    """
       Decorator, keep on trying functioning as long as it only raises Exception expr
       @param expected_exception:
       @return:
       @rtype:
       """

    def wrapper(f):
        @functools.wraps(f)
        async def __helper(*args, **kwargs):
            cont = True
            while cont:
                try:
                    e = await f(*args, **kwargs)
                    return e

                except expected_exception:
                    logging.debug(f"exception {expected_exception} raised, ignoring")
                    pass
                # Propagate up any other exception types
                except Exception as ex:
                    logging.exception(ex)
                    raise

        return __helper

    return wrapper


def try_until(expected_exception):
    """
    Decorator, keep on trying functioning as long as it only raises Exception expr
    @param expected_exception:
    @return:
    @rtype:
    """

    def try_decorator(f):
        def __helper(*args, **kwargs):
            cont = True
            while cont:
                try:
                    r = f(*args, **kwargs)
                    return r
                except expected_exception:
                    logging.debug(f"exception {expected_exception} raised, ignoring")
                    pass
                # Propagate up any other exception types
                except Exception as ex:
                    logging.exception(ex)
                    raise

        return __helper

    return try_decorator


async def _spawn_async(*args, return_output=False):
    # logging.debug(f'Spawning process with command: {args}')

    # make sure the arglist doesn't assume shell (remove first arg if same as prog)
    # if cmds[0] == prog:
    #     cmds.remove(prog)
    try:
        proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE)
    except Exception as ex:

        logging.exception(ex)
        raise
    try:
        # this buffers output in memory, may be a problem in the future
        out: bytes
        out, err = await proc.communicate()
        # logging.info(out.decode())
        # await asyncio.gather(read_stdout(proc.stdout),
        #                      read_stderr(proc.stderr))
        # data = await proc.stdout.readline()
        # line = data.decode('ascii').rstrip()
        await proc.wait()
    except KeyboardInterrupt:
        await proc.send_signal(signal=signal.SIGTERM)
    except Exception as ex:
        logging.exception(ex)
        raise
    else:
        if proc.returncode != 0:
            ex = ChildProcessError(proc)
            logging.error(ex)
            logging.exception(ex, out, err)
            raise ex
        else:
            if return_output:
                return out
            else:
                return


async def read_stderr(stderr):
    print('read_stderr')
    while True:
        buf = await stderr.read()
        if not buf:
            break

        print(f'stderr: {buf}')


async def read_stdout(stdout):
    print('read_stdout')
    while True:
        buf = await stdout.read(10)
        if not buf:
            break

        print(f'stdout: {buf}')


def _spawn(cmds):
    logging.debug(f'Spawning process with command: {cmds}')
    proc = subprocess.Popen(
        cmds,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
    )
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        logging.error(stderr)
        raise Error('ffprobe', stdout, stderr)
    if stdout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr:
        print(f'[stderr]\n{stderr.decode()}')
        raise ChildProcessError()
