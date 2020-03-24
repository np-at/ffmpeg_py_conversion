import asyncio
import os
from unittest import TestCase

from ffmp_conv import _utils

TEST_DIR = os.path.dirname(__file__)
SAMPLE_DATA_DIR = os.path.join(TEST_DIR, 'sample_data')

TEST_INPUT_FILE1 = os.path.join(SAMPLE_DATA_DIR, 'in1.mp4')

def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper

class Test(TestCase):
    def test_probe(self):
        data = _utils.probe(TEST_INPUT_FILE1)
        assert set(data.keys()) == {'format', 'streams'}
        assert data['format']['duration'] == '7.036000'

    @async_test
    async def test_probe_async(self):
        data = await _utils.probe_async(TEST_INPUT_FILE1)
        assert set(data.keys()) == {'format', 'streams'}
        assert data['format']['duration'] == '7.036000'
