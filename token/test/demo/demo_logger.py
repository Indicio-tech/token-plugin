import os
import logging
import py._io.terminalwriter as terminalwriter

class DemoLogger():

    def __init__(self, allow_colors=False):
        self._log_name = 'demo_logger'
        self._logger = logging.getLogger(self._log_name)
        if 'OUTPUT_NOT_CAPTURED' in os.environ and int(os.environ['OUTPUT_NOT_CAPTURED']):
            self._tw = terminalwriter.TerminalWriter()
            self._tw.hasmarkup = True

    def log(self, msg, log_level = logging.INFO, color=None):
        if color and hasattr(self, '_tw'):
            msg = self._tw.markup(msg, **{color: 1})
        self._logger.log(log_level, msg)


    def log_green(self, msg):
        self.log(msg, color='green')

    def log_blue(self, msg):
        self.log(msg, color='blue')

