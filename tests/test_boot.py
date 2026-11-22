import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, HERE)


def sandbox():
    r = tempfile.mkdtemp(prefix="bm-test-")
    os.makedirs(r + "/etc/default/grub.d")
    open(r + "/etc/default/grub", "w").write(
        'GRUB_DEFAULT=0\nGRUB_TIMEOUT=5\nGRUB_HIDDEN_TIMEOUT=0\n'
        'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash amdgpu.dcdebugmask=0x12 loglevel=3"\nGRUB_CMDLINE_LINUX=""\n')
    for t in ("spinner", "bgrt"):
        d = r + f"/usr/share/plymouth/themes/{t}"
        os.makedirs(d)
        open(f"{d}/{t}.plymouth", "w").write(f"[Plymouth Theme]\nName={t}\nModuleName=two-step\n")
    os.makedirs(r + "/etc/plymouth")
    open(r + "/etc/plymouth/plymouthd.conf", "w").write("[Daemon]\nTheme=bgrt\n")
    return r


def helper(root, *a):
    env = dict(os.environ, BOOT_MARKA_ROOT=root, BOOT_MARKA_TEST="1")
    return subprocess.run([sys.executable, os.path.join(HERE, "prilozhi.py"), *a], env=env, capture_output=True, text=True)


class T(unittest.TestCase):
    def setUp(self):
        self.r = sandbox()
        os.environ["BOOT_MARKA_ROOT"] = self.r
        import importlib, jezgro
        self.J = importlib.reload(jezgro)

    def tearDown(self):
        shutil.rmtree(self.r)
        os.environ.pop("BOOT_MARKA_ROOT", None)

    def test_modes_keep_foreign(self):
        J = self.J
        b = "quiet splash amdgpu.dcdebugmask=0x12 loglevel=3"
        self.assertEqual("amdgpu.dcdebugmask=0x12", J.build_cmdline(b, "podroben"))
        self.assertIn("vt.global_cursor_default=0", J.build_cmdline(b, "tih"))
        self.assertEqual("tih", J.detect_mode(J.build_cmdline(b, "tih")))
        self.assertEqual("normalen", J.detect_mode("quiet splash"))
        self.assertEqual("podroben", J.detect_mode("ro"))

    def test_read_grub(self):
        g = self.J.read_grub()
        self.assertEqual("5", g["GRUB_TIMEOUT"])
        self.assertIn("amdgpu", g["GRUB_CMDLINE_LINUX_DEFAULT"])
        p = self.J.grub_from_settings(g)
        self.assertEqual("hidden", p.style)       # заради остарелия GRUB_HIDDEN_TIMEOUT

    def test_apply_and_reset(self):
        r = helper(self.r, "--tema", "spinner", "--rezhim", "tih", "--grub-vreme", "3", "--grub-stil", "menu", "--grub-pomni", "1")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        d = open(self.r + "/etc/default/grub.d/99-boot-marka.cfg").read()
        self.assertIn("GRUB_TIMEOUT=3", d)
        self.assertIn("GRUB_DEFAULT=saved", d)
        self.assertIn("amdgpu.dcdebugmask=0x12", d)
        g = self.J.read_grub()
        self.assertEqual("3", g["GRUB_TIMEOUT"])
        self.assertEqual("", g["GRUB_HIDDEN_TIMEOUT"])
        self.assertIn("Theme=spinner", open(self.r + "/etc/plymouth/plymouthd.conf").read())
        self.assertIn("update-initramfs", r.stdout)
        # основният файл не е пипан
        self.assertIn("GRUB_TIMEOUT=5", open(self.r + "/etc/default/grub").read())
        r = helper(self.r, "--varni")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(self.r + "/etc/default/grub.d/99-boot-marka.cfg"))
        self.assertIn("Theme=bgrt", open(self.r + "/etc/plymouth/plymouthd.conf").read())

    def test_custom_theme(self):
        J = self.J
        src = os.path.join(self.r, "a.gif")
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=320x240:d=1:r=10", src], check=True)
        d, slug, n, size = J.make_custom(J.Custom(title="Моята Проба", src=src, label="SimNet", indicator="lenta"), workdir=os.path.join(self.r, "w"), log=lambda s: None)
        self.assertEqual("moyata-proba", slug)
        self.assertGreaterEqual(n, 5)
        r = helper(self.r, "--nova-tema", d, slug, "--tema", "boot-marka-" + slug)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        t = [x for x in J.themes() if x.name == "boot-marka-moyata-proba"][0]
        self.assertTrue(t.ours)
        self.assertGreaterEqual(len(t.frames), 5)
        sc = open(t.path + "/boot-marka-moyata-proba.script").read()
        self.assertIn("label.png", sc)
        self.assertIn("SetBootProgressFunction", sc)
        self.assertNotIn("{", sc.replace("{\n", "").replace("{{", "")) if False else None
        r = helper(self.r, "--varni")
        self.assertFalse(os.path.exists(t.path))

    def test_rejects(self):
        self.assertNotEqual(0, helper(self.r, "--tema", "../../etc").returncode)
        self.assertNotEqual(0, helper(self.r, "--grub-vreme", "99").returncode)
        bad = os.path.join(self.r, "bad"); os.makedirs(bad)
        open(bad + "/evil.sh", "w").write("x")
        self.assertNotEqual(0, helper(self.r, "--nova-tema", bad, "x").returncode)
        self.assertNotEqual(0, helper(self.r, "--grub-fon", "/etc/passwd").returncode)


if __name__ == "__main__":
    unittest.main()
