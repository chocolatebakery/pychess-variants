import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "render-build.sh"
STUB_COMMANDS = """
pip3() {
    printf '%s\\n' "pip3 $*" >> "$BUILD_CALLS"
    if [ "$*" = "$FAIL_PIP_ARGS" ]; then return 42; fi
}
yarn() {
    printf '%s\\n' "yarn $*" >> "$BUILD_CALLS"
}
export -f pip3 yarn
bash "$1"
"""


@unittest.skipUnless(os.name != "nt" and shutil.which("bash"), "Requires native Bash")
class RenderBuildTest(unittest.TestCase):
    def run_build(self, fail_pip_args=""):
        with tempfile.TemporaryDirectory() as directory:
            calls_file = Path(directory) / "calls.log"
            calls_file.touch()
            env = dict(os.environ, BUILD_CALLS=str(calls_file), FAIL_PIP_ARGS=fail_pip_args)
            result = subprocess.run(
                ["bash", "-c", STUB_COMMANDS, "render-build-test", str(BUILD_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            return result, calls_file.read_text().splitlines()

    def test_local_fsx_is_installed_before_main_app_and_frontend(self):
        result, calls = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls,
            [
                "pip3 install ./vendor/pyffish-fsx",
                "pip3 install .",
                "yarn install",
                "yarn dev",
                "yarn md",
            ],
        )

    def test_failed_fsx_install_stops_the_build(self):
        result, calls = self.run_build("install ./vendor/pyffish-fsx")
        self.assertEqual(result.returncode, 42)
        self.assertEqual(calls, ["pip3 install ./vendor/pyffish-fsx"])

    def test_failed_app_install_stops_the_frontend_build(self):
        result, calls = self.run_build("install .")
        self.assertEqual(result.returncode, 42)
        self.assertEqual(calls, ["pip3 install ./vendor/pyffish-fsx", "pip3 install ."])
