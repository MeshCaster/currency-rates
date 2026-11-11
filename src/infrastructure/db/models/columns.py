from enum import StrEnum

from sqlalchemy import Enum


def enum_column[E: StrEnum](enum: type[E], length: int = 16) -> Enum:
    return Enum(enum, native_enum=False, length=length, validate_strings=True,
                values_callable=lambda e: [m.value for m in e])
