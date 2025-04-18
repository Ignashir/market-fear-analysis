from enum import StrEnum
import argparse

class Length(StrEnum):
    ONE_MONTH = "m1"
    SIX_MONTH = "m6"
    YTD = "ytd"
    YEAR = "y1"
    FIVE_YEAR = "y5"
    MAX = "y10"


def parse_enum(enum_class):
    def _convert(value):
        try:
            return enum_class[value]
        except KeyError:
            raise argparse.ArgumentTypeError(f"Invalid choice, must be one of: {', '.join([e.name for e in enum_class])}")
    return _convert