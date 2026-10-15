import io
import unittest
from unittest.mock import patch

from dmoj import sysinfo


class MonitoringSysinfoTests(unittest.TestCase):
    def test_missing_proc_metrics_are_omitted(self):
        with patch('builtins.open', side_effect=OSError), patch.object(sysinfo.shutil, 'disk_usage', side_effect=OSError):
            name, metrics = sysinfo.monitoring_metrics()
        self.assertEqual(name, 'monitor-metrics')
        self.assertEqual(metrics, {'cpu_count': sysinfo._cpu_count})

    def test_linux_metrics_and_cpu_delta(self):
        files = {
            '/proc/stat': 'cpu 100 0 100 800 0 0 0 0 0 0\n',
            '/proc/meminfo': 'MemTotal: 1024 kB\nMemAvailable: 512 kB\n',
            '/proc/net/dev': ' lo: 100 0 0 0 0 0 0 0 200 0\n eth0: 300 0 0 0 0 0 0 0 400 0\n',
        }
        with patch('builtins.open', side_effect=lambda path: io.StringIO(files[path])), \
                patch.object(sysinfo, '_previous_cpu', None), \
                patch.object(sysinfo.shutil, 'disk_usage', return_value=type('Disk', (), {'total': 1000, 'free': 500})()):
            _, first = sysinfo.monitoring_metrics()
            self.assertNotIn('cpu_percent', first)
            files['/proc/stat'] = 'cpu 150 0 100 850 0 0 0 0\n'
            _, second = sysinfo.monitoring_metrics()
        self.assertEqual(second['cpu_percent'], 50)
        self.assertEqual(second['memory_available_bytes'], 512 * 1024)
        self.assertEqual(second['network_received_bytes'], 300)
        self.assertEqual(second['network_sent_bytes'], 400)


if __name__ == '__main__':
    unittest.main()
