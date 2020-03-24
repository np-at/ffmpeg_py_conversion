import asyncio
import logging
import os
import sys
from argparse import ArgumentParser, Namespace

from .converter import Converter


def try_load_config_file(parser: ArgumentParser = None, namespace: Namespace = None, selector: str = None) -> Namespace:
    """

    @param namespace:
    @type namespace:
    @param parser: main ArgumentParser object passed in to attempt to decode .env file
    @type parser: ArgumentParser
    @param selector: used if your have multiple configs in your file and want to select one, leave blank otherwise
    @type selector: str
    @return: parser object
    @rtype:
    """
    env_file = os.path.join(os.path.curdir, '.env')
    if parser is None and namespace is None:
        raise NameError
    if namespace is None:
        namespace, _ = parser.parse_known_args()

    if os.path.exists(env_file):
        data: dict

        try:
            import json
            from json import JSONDecodeError

            try:

                with open(env_file) as f:
                    data = json.load(f)

            except JSONDecodeError as ex:
                logging.critical(f'unable to decode {env_file}', ex)
                raise
            except Exception as exx:
                logging.critical(f'error reading {env_file}', exx)

        except ImportError:
            try:
                import yaml

                with open(env_file) as f:
                    data = yaml.load(f)
            except Exception as ex:
                logging.exception(ex)
                raise
        except Exception:
            logging.error(f"failed to parse config file")
            return namespace

        data_object: dict
        if selector is not None:
            data_object = data[selector]
        else:
            data_object = data

        for a in namespace.__dict__:
            if data_object.__contains__(a):
                namespace.__setattr__(a, data_object[a])
        return namespace
    else:
        return namespace


def create_arg_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument('--sonarr_url',
                        '-s',
                        help="url for sonarr")
    parser.add_argument('--sonarr_api', '-sa',

                        help="api key for sonarr")
    parser.add_argument('--radarr_url', '-r',

                        help="url for radarr")
    parser.add_argument('--radarr_api', '-ra',

                        help="api for radarr")
    parser.add_argument('--plex_url', '-p',

                        help="url for plex")
    parser.add_argument('--plex_token', '-pa',

                        help="api key/token for plex")
    parser.add_argument('--verbose', '-v',

                        help="verbosity",
                        action='count')
    return parser


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(threadName)s %(lineno)d %(message)s",
        # filename="ffmp_log.log"
    )

    p = create_arg_parser()
    n = try_load_config_file(parser=p)
    parsed_args, _ = p.parse_known_args(sys.argv[1:], n)
    d = parsed_args.__dict__
    try:
        c = Converter(**d)
        asyncio.run(c.run_sonarr_file())
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        logging.exception(ex)


if __name__ == '__main__':
    main()
