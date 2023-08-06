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

import asyncio, multiprocessing, aiofiles

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.utils import get_peer_id
from swibots import BotApp, RegisterCommand, BotContext, CommandEvent, Message, MediaUploadRequest
from aioredis import Redis
from logging import INFO, basicConfig, getLogger
from var import Var
from FastTelethon import download_file
from traceback import format_exc
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from datetime import datetime as dt
from mimetypes import guess_extension

basicConfig(
    format="%(asctime)s || %(name)s [%(levelname)s] : %(message)s",
    level=INFO,
    datefmt="%m/%d/%Y, %H:%M:%S",
)
LOGS = getLogger(__name__)
TelethonLogger = getLogger("Telethon")
TelethonLogger.setLevel(INFO)


try:
    LOGS.info("Trying Connect With Telegram")
    tg_bot = TelegramClient(StringSession(Var.SESSION), Var.API_ID, Var.API_HASH).start()
    LOGS.info("Successfully Connected with Telegram")
    LOGS.info("Trying Connect With Switch")
    sw_bot = BotApp(Var.SWITCH_BOT_TOKEN, "Stream Messages From Telegram Into Switch")
    LOGS.info("Successfully Connected with Switch")
except Exception as e:
    LOGS.critical(str(e))
    exit()

try:
    dB = Redis(
        username=Var.REDISUSER,
        host=Var.REDIS_URL.split(":")[0],
        port=int(Var.REDIS_URL.split(":")[1]),
        password=Var.REDISPASSWORD,
        decode_responses=True,
    )
    CACHE = {}
except Exception as es:
    LOGS.critical(str(es))
    exit()

# Registering Switch Commands

sw_bot.register_command([
    RegisterCommand("start", "To Get Help", True),
    RegisterCommand("watch", "To Stream Messages On Current Switch Channel", True),
    RegisterCommand("list", "To Get List Of Telegram Channels Which Are Currently Streaming In Switch Channel", True),
    RegisterCommand("unwatch", "To Stop Streaming Of Messages From Given Telegram Channel Into This Switch Channel", True),
]) 

# func and variable

def run_async(function):
    @wraps(function)
    async def wrapper(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            ThreadPoolExecutor(max_workers=multiprocessing.cpu_count() * 5),
            partial(function, *args, **kwargs),
        )

    return wrapper

HELP = """
Hey {}

/watch <telegram channel link> - *To Stream Messages On Current Switch Channel*

/list - *To Get List Of Telegram Channels Which Are Currently Streaming In Switch Channel*

/unwatch <telegram channel link> - *To Stop Streaming Of Messages From Given Telegram Channel Into This Switch Channel*
"""


# telegram channel joining stuffs

def link_parser_tg(link):
    hash = False
    if "@" in link:
        chat = link.strip().split()[0]
    elif "/joinchat/" in link:
        chat = link.split("/")[-1].replace("+", "")
        hash = True
    elif "+" in link:
        chat = link.split("/")[-1].replace("+", "")
        hash = True
    elif "-100" in link or link.isdigit():
        chat = int(link)
    else:
        chat = link.strip().split()[0]
    return chat, hash

async def join_channel(channel_id_text, client):
    chat, hash = link_parser_tg(channel_id_text)
    try:
        if hash:
            ch = await client(ImportChatInviteRequest(chat))
            return get_peer_id(ch.chats[0])
        else:
            ch = await client(JoinChannelRequest(chat))
            return get_peer_id(ch.chats[0])
    except BaseException:
        LOGS.error(format_exc())
        return False
    
async def leave_channel(channel_id_text, client):
    chat, hash = link_parser_tg(channel_id_text)
    try:
        if hash:
            ch = await client(CheckChatInviteRequest(chat))
            if ch.left:
                return True
            chat = ch.id
        ch = await client(LeaveChannelRequest(chat))
        return get_peer_id(ch.chats[0])
    except BaseException:
        LOGS.error(format_exc())
        return False
    
async def converter(event: events.NewMessage.Event):
    media, name, file, doc = None, None, None, False
    if event.media:
        try:
            name = event.file.name
        except:
            name = None
        if event.photo:
            if not name:
                name = "photo_" + dt.now().isoformat("_", "seconds") + ".png"
            dl = await event.client.download_media(event.media)
            media = MediaUploadRequest(path=dl, description=event.text.replace("**", "*"))
            return event.text.replace("**", "*"), media, doc
        if event.document or event.video or event.audio:
            if not name:
                name = "document_" + dt.now().isoformat("_", "seconds") + guess_extension(event.media.document.mime_type)
            file = event.media.document
            dl = await file_download(name, event, file)
            media = MediaUploadRequest(path=dl, description=event.text.replace("**", "*")) 
            doc = True
            return event.text.replace("**", "* "), media, doc
    return event.text.replace("**", "* "), media, doc

async def file_download(filename, event, file):
    async with aiofiles.open(filename, "wb") as f:
        ok = await download_file(
            client=event.client,
            location=file,
            out=f,
        )
    return filename

# database stuffs

async def sync_db_into_local():
    # await dB.flushall()
    data = eval((await dB.get("DATAS")) or "{}")
    CACHE.update(data)

async def add_to_stream(tg_channel_id, sw_community_id, sw_channel_id):
    data = eval((await dB.get("DATAS")) or "{}")
    key = f"{sw_community_id}|{sw_channel_id}"
    _data = data.get(key) or []
    if tg_channel_id not in _data:
        _data.append(tg_channel_id)
        data.update({key: _data})
        CACHE[key] = _data
        await dB.set("DATAS", str(data))

async def remove_from_stream(tg_channel_id, sw_community_id, sw_channel_id):
    data = eval((await dB.get("DATAS")) or "{}")
    key = f"{sw_community_id}|{sw_channel_id}"
    _data = data.get(key) or []
    if tg_channel_id in _data:
        _data.remove(tg_channel_id)
        data.update({key: _data})
        CACHE[key] = _data
        await dB.set("DATAS", str(data))

@run_async
def get_from_stream(sw_community_id, sw_channel_id):
    key = f"{sw_community_id}|{sw_channel_id}"
    return CACHE.get(key) or []

@run_async
def get_target_swi_channel(tg_channel_id):
    lst = []
    for key in list(CACHE.keys()):
        if tg_channel_id in CACHE[key]:
            lst.append(key)
    return lst

# Sending in Switch Stuff

async def send_message_in_switch(key, dl: str="", media=None, doc=None):
    message = Message(sw_bot)
    communtiy_id, channel_id = key.split("|")
    message.community_id = communtiy_id
    message.channel_id = channel_id
    message.message = dl.replace("**", "* ")
    message.is_document = doc
    return print(await message.send(media))

# Getting New Messages From Telegram and Streaming In Switch

@tg_bot.on(events.NewMessage(incoming=True))
async def msgedit(e: events.NewMessage.Event):
    ch = await e.get_chat()
    chat_id = get_peer_id(ch)
    target_list = await get_target_swi_channel(chat_id)
    if target_list:
        dl, media, doc = await converter(e)
        msg = await send_message_in_switch(target_list[0], dl, media, doc)
        target_list.pop(0)
        for key in target_list:
            await sw_bot.forward_message(msg, key.split("|")[1])
        # proc = [send_message_in_switch(key, dl, media, doc) for key in target_list]
        # await asyncio.gather(*proc)

# Commands Of Switch

@sw_bot.on_command("start")
async def _start(ctx: BotContext[CommandEvent]):
    await ctx.reply_message_text(ctx.event.message, HELP.format(ctx.event.message.user.name))


@sw_bot.on_command("watch")
async def _watch(ctx: BotContext[CommandEvent]):
    # if not ctx.event.message.user.admin:
    #     return await ctx.event.message.reply_text("I Only Work In For Community Admins!")
    link = ctx.event.params
    if not tg_bot.is_connected():
        await tg_bot.connect()
    if not (ctx.event.message.channel_id or ctx.event.message.community_id or ctx.event.message.group_id):
        return await ctx.event.message.reply_text("*I Only Work In Switch Community's Channel and Groups!*")
    chat_id = await join_channel(link, tg_bot)
    if not chat_id:
        return await ctx.event.message.reply_text("`Invalid Link Or Something Went Wrong!!!`")
    await add_to_stream(chat_id, ctx.event.message.community_id, ctx.event.message.channel_id or ctx.event.message.group_id)
    await ctx.event.message.reply_text("*Succesfully Added The Following Telegram Channel Into Watch List.*")

@sw_bot.on_command("unwatch")
async def _unwatch(ctx: BotContext[CommandEvent]):
    # if not ctx.event.message.user.admin:
    #     return await ctx.event.message.reply_text("I Only Work In For Community Admins!")
    link = ctx.event.params
    if not tg_bot.is_connected():
        await tg_bot.connect()
    if not (ctx.event.message.channel_id or ctx.event.message.community_id or ctx.event.message.group_id):
        return await ctx.event.message.reply_text("*I Only Work In Switch Community's Channel and Group!*")
    chat_id = await leave_channel(link, tg_bot)
    if not chat_id:
        return await ctx.event.message.reply_text("`Invalid Link Or Something Went Wrong!!!`")
    await remove_from_stream(chat_id, ctx.event.message.community_id, ctx.event.message.channel_id or ctx.event.message.group_id)
    await ctx.event.message.reply_text("*Succesfully Removed The Following Telegram Channel Into Watch List If Its Exist.*")

@sw_bot.on_command("list")
async def _list(ctx: BotContext[CommandEvent]):
    # if not ctx.event.message.user.admin:
    #     return await ctx.event.message.reply_text("I Only Work In For Community Admins!")
    if not tg_bot.is_connected():
        await tg_bot.connect()
    if not (ctx.event.message.channel_id or ctx.event.message.community_id):
        return await ctx.event.message.reply_text("*I Only Work In Switch Community's Channel!*")
    data = await get_from_stream(ctx.event.message.community_id, ctx.event.message.channel_id)
    txt = "*List Of Telegram Channels Currently Streaming Into This Chat*\n\n"
    for chat_id in (data):
        try:
            u = await tg_bot.get_entity(chat_id)
        except BaseException:
            u = None
        if u:
            txt += f"`{u.title}` ({chat_id})\n"
        else:
            txt += f"`Unknown` ({chat_id})\n"
    await ctx.event.message.reply_text(txt)

tg_bot.loop.run_until_complete(sync_db_into_local())
sw_bot.run()
