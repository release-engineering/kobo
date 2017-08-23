# -*- coding: utf-8 -*-


import errno
import os
import logging
import logging.handlers
import warnings


__all__ = (
    "BRIEF_LOG_FORMAT",
    "VERBOSE_LOG_FORMAT",
    "add_stream_handler",
    "add_stderr_logger",
    "add_file_logger",
    "add_rotating_file_logger",
    "LoggingBase",
)


BRIEF_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s"
VERBOSE_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] {%(process)5d} %(name)s:%(lineno)4d %(message)s"


###########
# Following hack enables 'VERBOSE' log level in the python logging module and Logger class.
# This means you need to import kobo.log before you can use 'VERBOSE' logging.


logging.VERBOSE = 15
logging.addLevelName(15, "VERBOSE")


def verbose(self, msg, *args, **kwargs):
    """
    Log 'msg % args' with severity 'VERBOSE'.

    To pass exception information, use the keyword argument exc_info with
    a true value, e.g.

    logger.info("Houston, we have a %s", "interesting problem", exc_info=1)
    """
    if self.manager.disable >= logging.VERBOSE:
        return
    if logging.VERBOSE >= self.getEffectiveLevel():
        self._log(*(logging.VERBOSE, msg, args), **kwargs)
logging.Logger.verbose = verbose


def verbose(msg, *args, **kwargs):
    """
    Log a message with severity 'VERBOSE' on the root logger.
    """
    if len(logging.root.handlers) == 0:
        logging.basicConfig()
    logging.root.verbose(*((msg, ) + args), **kwargs)
logging.verbose = verbose
del verbose


# end of hack
###########


def add_stderr_logger(logger, log_level=None, format=None):
    """Add a stderr logger to the logger.

    Deprecated, use ``add_stream_handler`` instead.
    """
    add_stream_handler(logger, log_level=log_level, format=format)


def add_stream_handler(logger, log_level=None, format=None, stream=None):
    """Add a handler that prints values to the given stream. Defaults to
    sys.stderr.
    """
    log_level = log_level or logging.DEBUG
    format = format or BRIEF_LOG_FORMAT

    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        logging.Formatter(format, datefmt="%Y-%m-%d %H:%M:%S"))
    handler.setLevel(log_level)
    logger.addHandler(handler)


class KoboLogWarning(UserWarning):
    """Just like a UserWarning, but with a custom name for better filtering."""
    pass


def _warn(msg, *args):
    """Report a warning pointing to a line that called whatever function called
    _warn.
    """
    warnings.warn(msg % args, KoboLogWarning, stacklevel=3)


def add_file_logger(logger, logfile, log_level=None, format=None, mode="a"):
    """Add a file logger to the logger.

    When there is a problem with the log file, a warning is logged. It can be
    turned into an exception by running:

    > warnings.simplefilter('error', kobo.log.KoboLogWarning)
    """
    log_level = log_level or logging.DEBUG
    format = format or BRIEF_LOG_FORMAT

    # Create parent directory if needed.
    try:
        os.makedirs(os.path.dirname(logfile))
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            _warn('Could not create %s: %s', os.path.dirname(logfile), exc)
            return

    # touch the logfile
    if not os.path.exists(logfile):
        try:
            fo = open(logfile, "w")
            fo.close()
        except IOError as exc:
            _warn('Could not touch %s: %s', logfile, exc)
            return

    # is the logfile really a file?
    if not os.path.isfile(logfile):
        _warn('Can not log into %s: not a file', logfile)
        return

    # check if the logfile is writable
    if not os.access(logfile, os.W_OK):
        _warn('Can not log into %s: not writable', logfile)
        return

    handler = logging.FileHandler(logfile, mode=mode)
    handler.setFormatter(logging.Formatter(format, datefmt="%Y-%m-%d %H:%M:%S"))
    handler.setLevel(log_level)
    logger.addHandler(handler)


def add_rotating_file_logger(logger, logfile, log_level=None, format=None, mode="a"):
    """Add a rotating file logger to the logger."""
    log_level = log_level or logging.DEBUG
    format = format or BRIEF_LOG_FORMAT

    # touch the logfile
    if not os.path.exists(logfile):
        try:
            fo = open(logfile, "w")
            fo.close()
        except (ValueError, IOError):
            return

    # is the logfile really a file?
    if not os.path.isfile(logfile):
        return

    # check if the logfile is writable
    if not os.access(logfile, os.W_OK):
        return

    handler = logging.handlers.RotatingFileHandler(logfile, maxBytes=10*(1024**2), backupCount=5, mode=mode)
    handler.setFormatter(logging.Formatter(format, datefmt="%Y-%m-%d %H:%M:%S"))
    handler.setLevel(log_level)
    logger.addHandler(handler)


class LoggingBase(object):
    """Inherit from this class to obtain log_* logging methods."""

    def __init__(self, logger=None):
        self._logger = logger

    def __log(self, level, msg, *args, **kwargs):
        if self._logger is None:
            return
        self._logger.log(level, msg, *args, **kwargs)

    def log_debug(self, msg, *args, **kwargs):
        self.__log(logging.DEBUG, msg, *args, **kwargs)

    def log_verbose(self, msg, *args, **kwargs):
        self.__log(logging.VERBOSE, msg, *args, **kwargs)

    def log_info(self, msg, *args, **kwargs):
        self.__log(logging.INFO, msg, *args, **kwargs)

    def log_warning(self, msg, *args, **kwargs):
        self.__log(logging.WARNING, msg, *args, **kwargs)

    def log_error(self, msg, *args, **kwargs):
        self.__log(logging.ERROR, msg, *args, **kwargs)

    def log_critical(self, msg, *args, **kwargs):
        self.__log(logging.CRITICAL, msg, *args, **kwargs)
