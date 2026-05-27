import os
import sys
import unittest
from queue import Queue
from unittest.mock import MagicMock, PropertyMock, patch


class TestTransitionsList(unittest.TestCase):
    def setUp(self):
        import app
        self.transitions = app.XFADE_TRANSITIONS

    def test_no_duplicates(self):
        self.assertEqual(len(self.transitions), len(set(self.transitions)),
                         "XFADE_TRANSITIONS contains duplicate entries")

    def test_minimum_count(self):
        self.assertGreaterEqual(len(self.transitions), 50)

    def test_fade_included(self):
        self.assertIn("fade", self.transitions)


class TestNvencPresetMap(unittest.TestCase):
    def setUp(self):
        import app
        self.map = app.NVENC_PRESET_MAP

    def test_all_presets_mapped(self):
        x264_presets = [
            "ultrafast", "superfast", "veryfast", "faster",
            "fast", "medium", "slow", "slower", "veryslow"
        ]
        for p in x264_presets:
            self.assertIn(p, self.map, f"Missing NVENC mapping for '{p}'")

    def test_valid_nvenc_preset_values(self):
        valid = {"p1", "p2", "p3", "p4", "p5", "p6", "p7"}
        for v in self.map.values():
            self.assertIn(v, valid, f"Invalid NVENC preset '{v}'")

    def test_default_mapping(self):
        self.assertEqual(self.map.get("medium", "p6"), "p6")


class TestGetFfmpegPath(unittest.TestCase):
    def setUp(self):
        import app
        self.app = app

    def tearDown(self):
        # Clean up any injected attributes
        if hasattr(self.app.sys, 'frozen'):
            del self.app.sys.frozen

    @patch('app.os.path.exists', return_value=True)
    @patch('app.os.path.dirname', return_value='C:\\test')
    @patch('app.os.path.abspath', return_value='C:\\test\\app.py')
    def test_local_bundled_path(self, mock_abspath, mock_dirname, mock_exists):
        result = self.app.get_ffmpeg_path()
        self.assertTrue(result.endswith('ffmpeg\\ffmpeg.exe') or result.endswith('ffmpeg/ffmpeg.exe'))
        self.assertIn('C:\\test', result)

    @patch('app.os.path.exists', return_value=False)
    @patch('app.shutil.which', return_value='C:\\ffmpeg\\bin\\ffmpeg.exe')
    def test_which_path(self, mock_which, mock_exists):
        result = self.app.get_ffmpeg_path()
        self.assertEqual(result, 'C:\\ffmpeg\\bin\\ffmpeg.exe')

    @patch('app.os.path.exists', return_value=False)
    @patch('app.shutil.which', return_value=None)
    def test_fallback(self, mock_which, mock_exists):
        result = self.app.get_ffmpeg_path()
        self.assertEqual(result, 'ffmpeg.exe')

    def test_frozen_path(self):
        self.app.sys.frozen = True
        self.app.sys._MEIPASS = 'C:\\bundle'
        result = self.app.get_ffmpeg_path()
        self.assertEqual(result, 'C:\\bundle\\ffmpeg.exe')
        del self.app.sys.frozen


class TestGetIconPath(unittest.TestCase):
    def setUp(self):
        import app
        self.app = app

    def tearDown(self):
        if hasattr(self.app.sys, 'frozen'):
            del self.app.sys.frozen

    def test_unfrozen(self):
        result = self.app.get_icon_path()
        self.assertEqual(result, 'favicon.ico')

    def test_frozen(self):
        self.app.sys.frozen = True
        self.app.sys._MEIPASS = 'C:\\bundle'
        result = self.app.get_icon_path()
        self.assertEqual(result, 'C:\\bundle\\favicon.ico')
        del self.app.sys.frozen


class TestCreateVideoWorkerValidation(unittest.TestCase):
    def setUp(self):
        import app
        self.app = app
        self.q = Queue()

        # Mock tkinter vars as simple MagicMock objects
        self.app.source_dir_var = MagicMock()
        self.app.dest_dir_var = MagicMock()
        self.app.duration_var = MagicMock()
        self.app.fade_duration_var = MagicMock()
        self.app.randomize_transitions_var = MagicMock()
        self.app.selected_transition_var = MagicMock()
        self.app.preset_var = MagicMock()
        self.app.crf_var = MagicMock()
        self.app.width_var = MagicMock()
        self.app.height_var = MagicMock()
        self.app.output_name_var = MagicMock()
        self.app.sort_order_var = MagicMock()
        self.app.use_hw_accel_var = MagicMock()

        # Default valid return values
        self.app.source_dir_var.get.return_value = 'C:\\input'
        self.app.dest_dir_var.get.return_value = 'C:\\output'
        self.app.duration_var.get.return_value = 3.0
        self.app.fade_duration_var.get.return_value = 0.5
        self.app.randomize_transitions_var.get.return_value = False
        self.app.selected_transition_var.get.return_value = 'fade'
        self.app.preset_var.get.return_value = 'medium'
        self.app.crf_var.get.return_value = 23
        self.app.width_var.get.return_value = 1920
        self.app.height_var.get.return_value = 1080
        self.app.output_name_var.get.return_value = 'output.mp4'
        self.app.sort_order_var.get.return_value = 'by name'
        self.app.use_hw_accel_var.get.return_value = False

        # Patch get_ffmpeg_path and os.listdir to avoid real FS access
        self.ffmpeg_patch = patch.object(self.app, 'get_ffmpeg_path', return_value='C:\\ffmpeg.exe')
        self.exists_patch = patch.object(self.app.os.path, 'exists', return_value=True)
        self.listdir_patch = patch.object(self.app.os, 'listdir', return_value=['img1.png', 'img2.png'])
        self.ffmpeg_patch.start()
        self.exists_patch.start()
        self.listdir_patch.start()

    def tearDown(self):
        self.ffmpeg_patch.stop()
        self.exists_patch.stop()
        self.listdir_patch.stop()

    def _get_message(self):
        try:
            return self.q.get_nowait()
        except Exception:
            return None

    def test_missing_source_dir(self):
        self.app.source_dir_var.get.return_value = ''
        self.app.create_video_worker(self.q)
        msg = self._get_message()
        self.assertIsNotNone(msg)
        self.assertEqual(msg[0], 'error')
        self.assertIn('source', msg[1].lower())

    def test_missing_dest_dir(self):
        self.app.dest_dir_var.get.return_value = ''
        self.app.create_video_worker(self.q)
        msg = self._get_message()
        self.assertIsNotNone(msg)
        self.assertEqual(msg[0], 'error')
        self.assertIn('destination', msg[1].lower())

    def test_negative_duration(self):
        self.app.duration_var.get.return_value = 0
        self.app.create_video_worker(self.q)
        msg = self._get_message()
        self.assertIsNotNone(msg)
        self.assertEqual(msg[0], 'error')
        self.assertIn('duration', msg[1].lower())

    def test_negative_fade(self):
        self.app.fade_duration_var.get.return_value = -1
        self.app.create_video_worker(self.q)
        msg = self._get_message()
        self.assertIsNotNone(msg)
        self.assertEqual(msg[0], 'error')
        self.assertIn('transition', msg[1].lower())

    def test_fade_equals_duration(self):
        self.app.fade_duration_var.get.return_value = 3.0
        self.app.duration_var.get.return_value = 3.0
        self.app.create_video_worker(self.q)
        msg = self._get_message()
        self.assertIsNotNone(msg)
        self.assertEqual(msg[0], 'error')
        self.assertIn('transition', msg[1].lower())

    def test_crf_out_of_range_low(self):
        self.app.crf_var.get.return_value = -1
        self.app.create_video_worker(self.q)
        msg = self._get_message()
        self.assertIsNotNone(msg)
        self.assertEqual(msg[0], 'error')
        self.assertIn('crf', msg[1].lower())

    def test_crf_out_of_range_high(self):
        self.app.crf_var.get.return_value = 52
        self.app.create_video_worker(self.q)
        msg = self._get_message()
        self.assertIsNotNone(msg)
        self.assertEqual(msg[0], 'error')
        self.assertIn('crf', msg[1].lower())

    def test_invalid_resolution(self):
        self.app.width_var.get.return_value = 0
        self.app.create_video_worker(self.q)
        msg = self._get_message()
        self.assertIsNotNone(msg)
        self.assertEqual(msg[0], 'error')
        self.assertIn('resolution', msg[1].lower())

    def test_empty_output_filename(self):
        self.app.output_name_var.get.return_value = ''
        self.app.create_video_worker(self.q)
        msg = self._get_message()
        self.assertIsNotNone(msg)
        self.assertEqual(msg[0], 'error')
        self.assertIn('filename', msg[1].lower())

    def test_no_images_found(self):
        listdir_patch = patch.object(self.app.os, 'listdir', return_value=[])
        listdir_patch.start()
        self.app.create_video_worker(self.q)
        msg = self._get_message()
        self.assertIsNotNone(msg)
        self.assertEqual(msg[0], 'error')
        self.assertIn('image', msg[1].lower())
        listdir_patch.stop()


class TestCancelEvent(unittest.TestCase):
    def setUp(self):
        import app
        self.app = app
        self.app.cancel_event.clear()

    def test_cancel_event_clear_by_default(self):
        self.assertFalse(self.app.cancel_event.is_set())

    def test_cancel_event_set(self):
        self.app.cancel_event.set()
        self.assertTrue(self.app.cancel_event.is_set())

    def test_cancel_event_clear_after_set(self):
        self.app.cancel_event.set()
        self.app.cancel_event.clear()
        self.assertFalse(self.app.cancel_event.is_set())


class TestSortOrder(unittest.TestCase):
    def test_by_name_sort(self):
        files = ['img10.png', 'img2.png', 'img1.png']
        files.sort(key=lambda x: os.path.basename(x).lower())
        self.assertEqual(files, ['img1.png', 'img10.png', 'img2.png'])


class TestOutputFilenameExtension(unittest.TestCase):
    def test_extension_added_when_missing(self):
        name = 'myvideo'
        if not name.endswith('.mp4'):
            name += '.mp4'
        self.assertEqual(name, 'myvideo.mp4')

    def test_extension_not_duplicated(self):
        name = 'myvideo.mp4'
        if not name.endswith('.mp4'):
            name += '.mp4'
        self.assertEqual(name, 'myvideo.mp4')


if __name__ == '__main__':
    unittest.main()
