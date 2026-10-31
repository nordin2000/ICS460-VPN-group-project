"""Unit tests for the pure helpers in scripts/vpnlib.py.

These need no VPN, no network and no root:  python -m unittest discover tests
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import vpnlib as lib  # noqa: E402

SAMPLE_CONF = (ROOT / "examples" / "sample-hub-wg0.conf").read_text()
KEY1 = "RkFLRS1zaXRlLXdnLTEta2V5LXRlc3RzLW9ubHkuLi4="
KEY2 = "RkFLRS1zaXRlLXdnLTIta2V5LXRlc3RzLW9ubHkuLi4="
NEW_KEY = "TkVXLXNpdGUta2V5LWZvci10ZXN0cy1vbmx5Li4uLi4="


class NextFreeIP(unittest.TestCase):
    def test_skips_hub_active_and_unreleased(self):
        reg = lib.load_registry(ROOT / "examples" / "sample-registry.json")
        # .1 hub, .2/.3 active, .4 revoked but not released -> .5
        self.assertEqual(lib.next_free_ip("10.100.0.0/24", "10.100.0.1", reg), "10.100.0.5")

    def test_released_address_is_reused(self):
        reg = {"peers": [{"name": "a", "tunnel_ip": "10.100.0.2",
                          "status": "revoked", "released": True}]}
        self.assertEqual(lib.next_free_ip("10.100.0.0/24", "10.100.0.1", reg), "10.100.0.2")

    def test_full_subnet_raises(self):
        reg = {"peers": [{"name": "a", "tunnel_ip": "10.100.0.2", "status": "active"}]}
        with self.assertRaises(RuntimeError):
            lib.next_free_ip("10.100.0.0/30", "10.100.0.1", reg)  # only .1 and .2 usable


class HubConfigEditing(unittest.TestCase):
    def test_peers_in_conf(self):
        self.assertEqual(lib.peers_in_conf(SAMPLE_CONF), [KEY1, KEY2])

    def test_add_appends_block(self):
        out = lib.add_peer_block(SAMPLE_CONF, "site-wg-3", NEW_KEY, "10.100.0.5")
        self.assertEqual(lib.peers_in_conf(out), [KEY1, KEY2, NEW_KEY])
        self.assertIn("AllowedIPs = 10.100.0.5/32", out)
        self.assertIn("# site-wg-3", out)

    def test_add_refuses_duplicate_key(self):
        with self.assertRaises(ValueError):
            lib.add_peer_block(SAMPLE_CONF, "dupe", KEY1, "10.100.0.9")

    def test_remove_only_the_target(self):
        out, removed = lib.remove_peer_block(SAMPLE_CONF, KEY1)
        self.assertTrue(removed)
        self.assertEqual(lib.peers_in_conf(out), [KEY2])
        self.assertIn("[Interface]", out)
        self.assertNotIn("site-wg-1", out)

    def test_remove_missing_key_changes_nothing(self):
        out, removed = lib.remove_peer_block(SAMPLE_CONF, NEW_KEY)
        self.assertFalse(removed)
        self.assertEqual(lib.peers_in_conf(out), [KEY1, KEY2])

    def test_add_then_remove_round_trip(self):
        added = lib.add_peer_block(SAMPLE_CONF, "site-wg-3", NEW_KEY, "10.100.0.5")
        out, removed = lib.remove_peer_block(added, NEW_KEY)
        self.assertTrue(removed)
        self.assertEqual(lib.peers_in_conf(out), [KEY1, KEY2])

    def test_site_conf_never_contains_a_real_private_key(self):
        conf = lib.render_site_conf("10.100.0.5", "HUBKEY=", "wg-hub", "51820", "172.30.0.10")
        self.assertIn("PrivateKey = <inserted on the site>", conf)
        self.assertIn("Endpoint = wg-hub:51820", conf)
        self.assertIn("AllowedIPs = 172.30.0.10/32", conf)
        self.assertNotIn("PersistentKeepalive", conf)


class NetBirdBodies(unittest.TestCase):
    def test_setup_key_is_one_off_one_day_one_use(self):
        body = lib.setup_key_body("site-nb-1", "grp123", False, "2026-10-05")
        self.assertEqual(body["type"], "one-off")
        self.assertEqual(body["expires_in"], 86400)
        self.assertEqual(body["usage_limit"], 1)
        self.assertEqual(body["auto_groups"], ["grp123"])

    def test_group_update_keeps_other_members(self):
        group = {"name": "prov-sites", "peers": [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]}
        self.assertEqual(lib.group_update_without(group, "p2"),
                         {"name": "prov-sites", "peers": ["p1", "p3"]})

    def test_block_keeps_role_and_groups(self):
        user = {"role": "user", "auto_groups": ["g1", "g2"], "is_blocked": False}
        self.assertEqual(lib.user_update_body(user, True),
                         {"role": "user", "auto_groups": ["g1", "g2"], "is_blocked": True})

    def test_pick_exactly_one(self):
        self.assertEqual(lib.pick_exactly_one([{"id": 1}], "peer"), {"id": 1})
        with self.assertRaises(LookupError):
            lib.pick_exactly_one([], "peer")
        with self.assertRaises(LookupError):
            lib.pick_exactly_one([{"id": 1}, {"id": 2}], "peer")


class ConfigAndInputs(unittest.TestCase):
    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".env", delete=False)
        f.write(text)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_secret_in_file_is_refused(self):
        path = self._write("NETBIRD_API_TOKEN=abc\n")
        with self.assertRaises(ValueError):
            lib.load_config(path)

    def test_env_overrides_file(self):
        path = self._write("WG_PORT=51820\n")
        os.environ["WG_PORT"] = "51821"
        self.addCleanup(os.environ.pop, "WG_PORT")
        self.assertEqual(lib.load_config(path)["WG_PORT"], "51821")

    def test_example_config_loads(self):
        cfg = lib.load_config(ROOT / "config.example")
        self.assertEqual(cfg["WG_SUBNET"], "10.100.0.0/24")

    def test_validate_name(self):
        self.assertEqual(lib.validate_name("site-wg-1"), "site-wg-1")
        for bad in ["Site1", "-site", "site_1", "a" * 40, ""]:
            with self.assertRaises(ValueError):
                lib.validate_name(bad)

    def test_parse_site_exec(self):
        self.assertEqual(lib.parse_site_exec("local"), ("local", None))
        self.assertEqual(lib.parse_site_exec("docker:site-1"), ("docker", "site-1"))
        self.assertEqual(lib.parse_site_exec("ssh:10.0.0.5"), ("ssh", "10.0.0.5"))
        with self.assertRaises(ValueError):
            lib.parse_site_exec("docker:")


if __name__ == "__main__":
    unittest.main()
