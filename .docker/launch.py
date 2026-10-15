"""Keep the judge's inherited runtime/problem caches on Python 3.14+."""
import multiprocessing
import runpy
import sys

if __name__ == '__main__':
    # This judge expects fork semantics; Python 3.14 defaults to forkserver.
    multiprocessing.set_start_method('fork')
    arguments = sys.argv[1:]
    if arguments[0] == '/env/bin/python3':
        sys.argv = [arguments[2], *arguments[3:]]
        runpy.run_module(arguments[2], run_name='__main__', alter_sys=True)
    else:
        sys.argv = arguments
        runpy.run_path(arguments[0], run_name='__main__')
