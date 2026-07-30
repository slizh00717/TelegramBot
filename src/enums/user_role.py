from enum import Enum


class UserRole(str, Enum):
    BARBER = "barber"
    CLIENT = "client"
