import os
from unittest import TestCase

from ffmp_conv import FilePreferences
from ffmp_conv.Tests.test__utils import async_test

TEST_DIR = os.path.dirname(__file__)
SAMPLE_DATA_DIR = os.path.join(TEST_DIR, 'sample_data')

TEST_INPUT_FILE1 = os.path.join(SAMPLE_DATA_DIR, 'in1.mp4')


class TestFilePreferences(TestCase):
    @async_test
    async def test_generate_args_from_filepath(self):
        f = FilePreferences.FilePreferences()
        data = await f.generate_args_from_filepath(TEST_INPUT_FILE1)
        self.assertIsNotNone(data)
