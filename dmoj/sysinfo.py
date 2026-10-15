import os
import shutil
import time
from multiprocessing import cpu_count as _get_cpu_count

_cpu_count = _get_cpu_count()


if hasattr(os, 'getloadavg'):

    def load_fair():
        try:
            load = os.getloadavg()[0] / _cpu_count
        except OSError:  # as of May 2016, Windows' Linux subsystem throws OSError on getloadavg
            load = -1
        return 'load', load

else:
    # There exist some Unix platforms (like Android) which don't
    # have `getloadavg` implemented, but aren't Windows
    # so we manually read the `/proc/loadavg` file.
    def load_fair():
        try:
            with open('/proc/loadavg', 'r') as f:
                load = float(f.read().split()[0]) / _cpu_count
        except FileNotFoundError:
            load = -1
        return 'load', load


def cpu_count():
    return 'cpu-count', _cpu_count


report_callbacks = [load_fair, cpu_count]


_previous_cpu = None


def monitoring_metrics():
    """Best effort Linux host counters, sampled by the existing 10-second ping.

    CPU is a delta since the previous ping. Other platforms omit unavailable
    counters; load average is deliberately not presented as CPU utilization.
    Network totals are cumulative host bytes, not a fabricated bandwidth rate.
    """
    global _previous_cpu
    metrics = {'cpu_count': _cpu_count}
    try:
        with open('/proc/stat') as stream:
            # Exclude guest counters, which are already included in user/nice.
            values = [int(value) for value in stream.readline().split()[1:9]]
        current = (sum(values), sum(values[3:5]), time.monotonic())
        previous, _previous_cpu = _previous_cpu, current
        if previous and current[0] > previous[0]:
            metrics['cpu_percent'] = max(0, min(100, 100 * (
                1 - (current[1] - previous[1]) / (current[0] - previous[0]))))
    except (OSError, ValueError, IndexError):
        pass
    try:
        with open('/proc/meminfo') as stream:
            memory = dict(line.split(':', 1) for line in stream if ':' in line)
        for source, target in [('MemTotal', 'memory_total_bytes'), ('MemAvailable', 'memory_available_bytes')]:
            if source in memory:
                metrics[target] = int(memory[source].split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    try:
        disk = shutil.disk_usage('/')
        metrics.update(disk_total_bytes=disk.total, disk_free_bytes=disk.free)
    except OSError:
        pass
    try:
        received = sent = 0
        with open('/proc/net/dev') as stream:
            for line in stream:
                if ':' not in line:
                    continue
                interface, counters = line.split(':', 1)
                if interface.strip() == 'lo':
                    continue
                values = counters.split()
                received += int(values[0])
                sent += int(values[8])
        metrics.update(network_received_bytes=received, network_sent_bytes=sent)
    except (OSError, ValueError, IndexError):
        pass
    return 'monitor-metrics', metrics


report_callbacks.append(monitoring_metrics)
