from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING, Formatter, LogRecord


class ColourFormatter(Formatter):
    NORMAL: int = 10
    BOLD: int = 1
    FADED: int = 2

    GREY: int = 37
    WHITE: int = 38
    GREEN: int = 32
    YELLOW: int = 33
    RED: int = 31

    CSI: str = "\x1b[{};{}m"
    RESET: str = "\x1b[0m"

    def __init__(self, fmt: str, datefmt: str) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)

        self.formats = {
            NOTSET: self.CSI.format(self.FADED, self.GREY) + self._fmt + self.RESET,
            DEBUG: self.CSI.format(self.NORMAL, self.GREY) + self._fmt + self.RESET,
            INFO: self.CSI.format(self.NORMAL, self.GREEN) + self._fmt + self.RESET,
            WARNING: self.CSI.format(self.NORMAL, self.YELLOW) + self._fmt + self.RESET,
            ERROR: self.CSI.format(self.NORMAL, self.RED) + self._fmt + self.RESET,
            CRITICAL: self.CSI.format(self.BOLD, self.RED) + self._fmt + self.RESET,
        }

    def format(self, record: LogRecord) -> str:
        log_fmt = self.formats.get(record.levelno)
        formatter = Formatter(fmt=log_fmt, datefmt=self.datefmt)
        return formatter.format(record)
