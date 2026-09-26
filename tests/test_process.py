import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from backend import process, streamcam

PYTHON = '/usr/bin/python3'


class ProcessTests(unittest.TestCase):
    def test_exact_output_limits_and_nonzero_status(self):
        result = process.run_bounded([PYTHON, '-I', '-c', 'import os; os.write(1,b"a"*100); os.write(2,b"b"*50); raise SystemExit(7)'], stdout_limit=100, stderr_limit=50)
        self.assertEqual((result.returncode, len(result.stdout), len(result.stderr)), (7, 100, 50))

    def test_both_streams_are_bounded(self):
        for fd in (1, 2):
            with self.subTest(fd=fd), patch.object(process, 'read', wraps=os.read) as reads:
                with self.assertRaises(process.OutputLimitError):
                    process.run_bounded([PYTHON, '-I', '-c', f'import os\nwhile True: os.write({fd}, b"x"*4096)'], stdout_limit=100, stderr_limit=100)
                self.assertTrue(all(call.args[1] <= 101 for call in reads.call_args_list))

    def test_closed_pipes_do_not_bypass_deadline(self):
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            process.run_bounded([PYTHON, '-I', '-c', 'import os,time; os.close(1); os.close(2); time.sleep(30)'], timeout=.15)
        self.assertLess(time.monotonic() - started, 2)

    def test_descendant_is_killed_even_after_leader_exit(self):
        for leader_exits in (False, True):
            with self.subTest(leader_exits=leader_exits), tempfile.TemporaryDirectory() as directory:
                marker = Path(directory) / 'child'
                script = f'''import os,signal,time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
child = os.fork()
if child == 0:
    with open({str(marker)!r}, 'w') as f: f.write(str(os.getpid()))
    time.sleep(30)
else:
    if {leader_exits!r}: os._exit(0)
    time.sleep(30)
'''
                with patch.object(process.subprocess, 'Popen', wraps=subprocess.Popen) as spawn:
                    with self.assertRaises(subprocess.TimeoutExpired):
                        process.run_bounded([PYTHON, '-I', '-c', script], timeout=.3)
                    self.assertTrue(spawn.call_args.kwargs['start_new_session'])
                pid = int(marker.read_text())
                stat_path = Path(f'/proc/{pid}/stat')
                # A killed orphan may briefly remain a zombie until PID 1 reaps it.
                for _ in range(100):
                    if not stat_path.exists() or stat_path.read_text().split()[2] == 'Z':
                        break
                    time.sleep(.01)
                else:
                    self.fail('Descendant survived process-group cleanup')

    def test_child_receives_only_allowlisted_environment(self):
        with patch.dict(os.environ, {'PATH': '/tmp/untrusted', 'LD_PRELOAD': '/tmp/untrusted.so', 'PYTHONPATH': '/tmp/untrusted', 'HOME': '/tmp/untrusted'}):
            result = process.run_bounded([PYTHON, '-I', '-c', 'import os,json; print(json.dumps(dict(os.environ)))'])
        environment = json.loads(result.stdout)
        # Python can add LC_CTYPE during startup locale coercion.
        environment.pop('LC_CTYPE', None)
        self.assertEqual(environment, process.ENVIRONMENT)

    def test_trusted_binary_and_untrusted_resolution(self):
        resolved = process.trusted_v4l2()
        self.assertTrue(Path(resolved).is_absolute())
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / 'v4l2-ctl'
            candidate.write_text('untrusted')
            candidate.chmod(0o755)
            with patch.object(process.Path, 'resolve', return_value=candidate):
                with self.assertRaises(FileNotFoundError):
                    process.trusted_v4l2()

    def test_parser_and_json_limits(self):
        for output in ('x'*513,
                       '\n'.join(f'control{i} 0x00980900 (int) : min=0 max=1 value=0' for i in range(129)),
                       'menu 0x00980900 (menu) : min=0 max=65 value=0\n' + '\n'.join(f'  {i}: option' for i in range(65))):
            with self.assertRaises(streamcam.CameraError):
                streamcam.parse_controls(output)
        with self.assertRaises(streamcam.CameraError):
            streamcam.encode_result({'formats': 'x' * streamcam.MAX_JSON})

    def test_v4l2_overflow_is_reported_and_deadline_is_shared(self):
        with patch.object(streamcam, 'run_bounded', side_effect=process.OutputLimitError):
            with self.assertRaises(streamcam.CameraError):
                streamcam.v4l2('/dev/video0', '--info')
        with patch.object(streamcam, 'REQUEST_DEADLINE', time.monotonic() - 1):
            with self.assertRaises(streamcam.CameraError):
                streamcam.v4l2('/dev/video0', '--info')


if __name__ == '__main__':
    unittest.main()
