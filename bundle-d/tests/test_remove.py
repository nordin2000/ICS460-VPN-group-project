"""Run from bundle-d: python3 -m unittest discover -s tests"""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'remove', Path(__file__).resolve().parents[2] / 'bundle-c/lab/remove.py'
)
remove = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remove)

CONFIG = '''[Interface]
PrivateKey = test-only
Address = 10.100.0.1/24

[Peer]
PublicKey = north-key
AllowedIPs = 10.100.0.2/32

[Peer]
PublicKey = east-key
AllowedIPs = 10.100.0.3/32

[Peer]
PublicKey = west-key
AllowedIPs = 10.100.0.4/32
'''


class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / 'wg0.conf'
        self.config.write_text(CONFIG)
        config_patch = patch.object(remove, 'CONFIG', self.config)
        config_patch.start()
        self.addCleanup(config_patch.stop)

    def test_removal_preserves_other_peers_and_interface(self):
        with patch.object(remove.subprocess, 'check_output', side_effect=[
            'north-key east-key west-key', 'north-key west-key'
        ]), patch.object(remove.subprocess, 'run') as run:
            remove.remove_from_hub('east-key')
        run.assert_called_once_with(
            ['wg', 'set', 'wg0', 'peer', 'east-key', 'remove'], check=True
        )
        self.assertEqual(self.config.read_text(), CONFIG.replace(
            '[Peer]\nPublicKey = east-key\nAllowedIPs = 10.100.0.3/32\n\n', ''
        ))
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        backup = self.config.with_suffix('.conf.before-remove')
        self.assertEqual(backup.read_text(), CONFIG)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_repeat_removal_does_nothing(self):
        text, _ = remove.remove_peer_block(CONFIG, 'east-key')
        self.config.write_text(text)
        with patch.object(remove.subprocess, 'check_output', return_value='north-key west-key'), \
                patch.object(remove.subprocess, 'run') as run:
            remove.remove_from_hub('east-key')
        run.assert_not_called()
        self.assertEqual(self.config.read_text(), text)

    def test_failed_live_removal_does_not_overwrite_saved_config(self):
        with patch.object(remove.subprocess, 'check_output', return_value='east-key'), \
                patch.object(remove.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'wg')):
            with self.assertRaises(subprocess.CalledProcessError):
                remove.remove_from_hub('east-key')
        self.assertEqual(self.config.read_text(), CONFIG)

    def test_verification_catches_peer_still_live(self):
        with patch.object(remove.subprocess, 'check_output', return_value='east-key'), \
                patch.object(remove.subprocess, 'run'):
            with self.assertRaisesRegex(RuntimeError, 'verification failed'):
                remove.remove_from_hub('east-key')

    def test_missing_peer_keeps_config(self):
        text, changed = remove.remove_peer_block(CONFIG, 'missing-key')
        self.assertFalse(changed)
        self.assertEqual(text, CONFIG)


if __name__ == '__main__':
    unittest.main()
