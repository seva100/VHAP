# 
# Toyota Motor Europe NV/SA and its affiliated companies retain all intellectual 
# property and proprietary rights in and to this software and related documentation. 
# Any commercial use, reproduction, disclosure or distribution of this software and 
# related documentation without an express license agreement from Toyota Motor Europe NV/SA 
# is strictly prohibited.
#


import logging
import sys
from datetime import datetime
import atexit
from pathlib import Path
import contextlib
import joblib


def _colored(msg, color):
    colors = {'red': '\033[91m', 'green': '\033[92m', 'yellow': '\033[93m', 'normal': '\033[0m'}
    return colors[color] + msg + colors["normal"]


class ColorFormatter(logging.Formatter):
    """
    Class to make command line log entries more appealing
    Inspired by https://github.com/facebookresearch/detectron2
    """

    def formatMessage(self, record):
        """
        Print warnings yellow and errors red
        :param record:
        :return:
        """
        log = super().formatMessage(record)
        if record.levelno == logging.WARNING:
            prefix = _colored("WARNING", "yellow")
        elif record.levelno == logging.ERROR or record.levelno == logging.CRITICAL:
            prefix = _colored("ERROR", "red")
        else:
            return log
        return prefix + " " + log


def get_logger(name, level=logging.DEBUG, root=False, log_dir=None):
    """
    Replaces the standard library logging.getLogger call in order to make some configuration
    for all loggers.
    :param name: pass the __name__ variable
    :param level: the desired log level
    :param root: call only once in the program
    :param log_dir: if root is set to True, this defines the directory where a log file is going
                    to be created that contains all logging output
    :return: the logger object
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if root:
        # create handler for console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        formatter = ColorFormatter(_colored("[%(asctime)s %(name)s]: ", "green") + "%(message)s",
                                   datefmt="%m/%d %H:%M:%S")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.propagate = False # otherwise root logger prints things again

        if log_dir is not None:
            # add handler to log to a file
            log_dir = Path(log_dir)
            if not log_dir.exists():
                logger.info(f"Logging directory {log_dir} does not exist and will be created")
                log_dir.mkdir(parents=True)
            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            log_file = log_dir / f"{timestamp}.log"

            # open stream and make sure it will be closed
            stream = log_file.open(mode="w")
            atexit.register(stream.close)

            formatter = logging.Formatter("[%(asctime)s] %(name)s %(levelname)s: %(message)s",
                                          datefmt="%m/%d %H:%M:%S")
            file_handler = logging.StreamHandler(stream)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


@contextlib.contextmanager
def tqdm_joblib(tqdm_object):
    """Context manager to patch joblib to report into tqdm progress bar given as argument"""
    class TqdmBatchCompletionCallback(joblib.parallel.BatchCompletionCallBack):
        def __call__(self, *args, **kwargs):
            tqdm_object.update(n=self.batch_size)
            return super().__call__(*args, **kwargs)

    old_batch_callback = joblib.parallel.BatchCompletionCallBack
    joblib.parallel.BatchCompletionCallBack = TqdmBatchCompletionCallback
    try:
        yield tqdm_object
    finally:
        joblib.parallel.BatchCompletionCallBack = old_batch_callback
        tqdm_object.close()
