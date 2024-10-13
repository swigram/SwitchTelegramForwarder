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

import asyncio, multiprocessing, aiofiles, os

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.errors import UserNotParticipantError
from telethon.utils import get_peer_id
from swibots import BotApp, BotCommand, BotContext, CommandEvent, Message, InlineKeyboardButton,InlineMarkup
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
    if Var.SESSION:
        tg_bot = TelegramClient(StringSession(Var.SESSION), Var.API_ID, Var.API_HASH).start()
    else:
        tg_bot = TelegramClient("session", Var.API_ID, Var.API_HASH).start(
            bot_token=Var.TG_BOT_TOKEN
        )
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

sw_bot.set_bot_commands([
    BotCommand("start", "To Get Help", True),
    BotCommand("watch", "To Stream Messages On Current Switch Channel", True),
    BotCommand("list", "To Get List Of Telegram Channels Which Are Currently Streaming In Switch Channel", True),
    BotCommand("unwatch", "To Stop Streaming Of Messages From Given Telegram Channel Into This Switch Channel", True),
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

def replace(dl):
    return dl.replace("**", " * ").replace("__", " __ ")


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

async def join_channel(channel_id_text, client: TelegramClient):
    chat, hash = link_parser_tg(channel_id_text)
    try:
        if hash:
            ch = await client(ImportChatInviteRequest(chat))
            return get_peer_id(ch.chats[0])
        else:
            if await client.is_bot():
                chat = await client.get_entity(chat)
                return get_peer_id(chat)
            else:
                ch = await client(JoinChannelRequest(chat))
                return get_peer_id(ch.chats[0])
    except BaseException:
        LOGS.error(format_exc())
        return False
    
async def leave_channel(channel_id_text, client: TelegramClient):
    chat, hash = link_parser_tg(channel_id_text)
    try:
        if hash:
            try:
                user = await client.get_permissions(chat, "me")
            except UserNotParticipantError:
                pass
            if user.has_left:
                return True
            chat = ch.id
        ch = await client(LeaveChannelRequest(chat))
        return get_peer_id(ch.chats[0])
    except BaseException:
        LOGS.error(format_exc())
        return False

def get_markup(event: events.NewMessage.Event):
    buttons = []
    if event.buttons:
        for button in event.buttons:
            row = []
            for btn in button:
                if getattr(btn, "url", None):
                    row.append(InlineKeyboardButton(btn.text, url=btn.url))
                else:
                    row.append(InlineKeyboardButton(btn.text, callback_data=btn.data))
            if row:
                buttons.append(row)
    if buttons:
        return InlineMarkup(buttons)


async def converter(event: events.NewMessage.Event):
    media, name, file, doc = None, None, None, False
    if event.media:
        try:
            name = event.file.name
        except:
            name = None
        if event.photo:
            text = replace(event.text)
            text = replace(event.text)
            if not name:
                name = "photo_" + dt.now().isoformat("_", "seconds") + ".png"
            dl = await event.client.download_media(event.media)
            return text, dl, doc, dl, get_markup(event)
        if event.document or event.video or event.audio or event.sticker:
            if not name:
                name = "document_" + dt.now().isoformat("_", "seconds") + guess_extension(event.media.document.mime_type)
            thumb = None
            if event.file.media.thumbs:
                thumb = await event.download_media(thumb=-1)
            file = event.media.document
            text = replace(event.text)
            text = replace(event.text)
            dl = await file_download(name, event, file)
            doc = True
            return text, name, doc, dl, get_markup(event)

    return replace(event.text), media, doc, None, None

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

async def remove_from_stream(tg_channel_id, msg, sw_community_id, sw_channel_id):
    data = eval((await dB.get("DATAS")) or "{}")
    key = f"{sw_community_id}|{sw_channel_id}"
    _data = data.get(key) or []
    if tg_channel_id in _data:
        _data.remove(tg_channel_id)
        data.update({key: _data})
        CACHE[key] = _data
        await dB.set("DATAS", str(data))
        await msg.reply_text("*Succesfully Removed The Following Telegram Channel Into Watch List If Its Exist.*")

    else:
        await msg.reply_text("`Invalid Link Or Something Went Wrong!!!`")


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

async def send_message_in_switch(key, dl: str="", media=None, doc=None, markup=None):
    communtiy_id, channel_id = key.split("|")
    print(communtiy_id, channel_id, dl, media, doc)
    return await sw_bot.send_message(
        community_id=communtiy_id,
        channel_id=channel_id,
        message=replace(dl),
        document=media,
        media_type=7 if doc else None,
        inline_markup=markup
    )

# Getting New Messages From Telegram and Streaming In Switch

@tg_bot.on(events.NewMessage(incoming=True))
async def msgedit(e: events.NewMessage.Event):
    ch = await e.get_chat()
    chat_id = get_peer_id(ch)
    print(chat_id)
    target_list = await get_target_swi_channel(chat_id)
    print(target_list)
    if target_list:
        dl, media, doc, path, markup = await converter(e)
        msg = await send_message_in_switch(target_list[0], dl, media, doc, markup)
        for paths in [path, media]:
            try:
                if paths:
                    os.remove(path)
            except:
                pass
        target_list.pop(0)
        for key in target_list:
            try:
                await msg.forward_to(key.split("|")[1])
            except BaseException:
                print(format_exc())

# Commands Of Switch

@sw_bot.on_command("start")
async def _start(ctx: BotContext[CommandEvent]):
    await ctx.event.message.reply_text(HELP.format(ctx.event.message.user.name))


@sw_bot.on_command("watch")
async def _watch(ctx: BotContext[CommandEvent]):
    # if not ctx.event.message.user.admin:
    #     return await ctx.event.message.reply_text("I Only Work In For Community Admins!")
    link = ctx.event.params
    if not tg_bot.is_connected():
        await tg_bot.connect()
    if not (ctx.event.message.channel_id and ctx.event.message.community_id):
        return await ctx.event.message.reply_text("*I Only Work In Switch Community's Channel!*")
    chat_id = await join_channel(link, tg_bot)
    if not chat_id:
        return await ctx.event.message.reply_text("`Invalid Link Or Something Went Wrong!!!`")
    await add_to_stream(chat_id, ctx.event.message.community_id, ctx.event.message.channel_id)
    await ctx.event.message.reply_text("*Succesfully Added The Following Telegram Channel Into Watch List.*")

@sw_bot.on_command("unwatch")
async def _unwatch(ctx: BotContext[CommandEvent]):
    # if not ctx.event.message.user.admin:
    #     return await ctx.event.message.reply_text("I Only Work In For Community Admins!")
    link = ctx.event.params
    if not tg_bot.is_connected():
        await tg_bot.connect()
    if not (ctx.event.message.channel_id and ctx.event.message.community_id):
        return await ctx.event.message.reply_text("*I Only Work In Switch Community's Channel!*")
    chat_id = await leave_channel(link, tg_bot)
    await remove_from_stream(chat_id, ctx.event.message, ctx.event.message.community_id, ctx.event.message.channel_id)
    
@sw_bot.on_command("list")
async def _list(ctx: BotContext[CommandEvent]):
    # if not ctx.event.message.user.admin:
    #     return await ctx.event.message.reply_text("I Only Work In For Community Admins!")
    if not tg_bot.is_connected():
        await tg_bot.connect()
    if not (ctx.event.message.channel_id and ctx.event.message.community_id):
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

