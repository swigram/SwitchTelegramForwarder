#    This file is part of the Switch Telegram Forwarder distribution.
#    Copyright (c) 2023 swigram
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3.
#
#    This program is distributed in the hope that it will be useful, but
#    WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#    General Public License for more details.
#
# License can be found in <
# https://github.com/swigram/SwitchTelegramForwarder/blob/main/LICENSE > .

from decouple import config

class Var:
    API_ID = config("API_ID", default=6, cast=int)
    API_HASH = config("API_ID")
    SESSION = config("SESSION")
    SWITCH_BOT_TOKEN = config("SWITCH_BOT_TOKEN")
    REDISPASSWORD = config("REDISPASSWORD")
    REDIS_URL = config("REDIS_URL")
    REDISUSER = config("REDISUSER", default="default")