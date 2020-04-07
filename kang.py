# -*- coding: future_fstrings -*-

#   Friendly Telegram (telegram userbot)
#   Copyright (C) 2018-2020 The Authors

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.

#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

from .. import loader, utils  # pylint: disable=relative-beyond-top-level
import logging
import io
from os import remove as DelFile
import urllib.request
from PIL import Image
from asyncio import sleep
import math

PACK_FULL = "Whoa! That's probably enough stickers for one pack, give it a break. \
A pack can't have more than 120 stickers at the moment."
PACK_FULL_RUS = "К сожалению, в одном наборе может быть не более 120 стикеров."

logger = logging.getLogger(__name__)


def register(cb):
    cb(KangMod())


@loader.tds
class KangMod(loader.Module):
    """Be cool, be kanger"""
    strings = {
        "name": "GovnoKanger",
        "silent_mode_cfg_doc": "If turned off, your userbot will edit kang message on ever step(recent actions flood) (on/off)",
        "pack_name_cfg_doc": "Название пакета спермы.\n%username% - твоя кликуха на зоне\n%packNumber% - сколько раз тебя там петушили.",
        "preparing_msg": "<code>Дрочу...</code>",
        "unsupported_err": "<b>И чё за говно ты мне дал</b>",
        "reply_err": "<b>Реплай мне дай дура тупая...</b>",
        "gettingType_msg": "<code>Щя чекну что за высер ты мне дал...</code>",
        "image_kanging_msg": "<code>Жру твое говно...</code>",
        "animated_kanging_msg": "<code>Пью твою мочу...</code>",
        "pack_notExist": "Пакет гавна не найден...",
        "switching_msg": "<code>Сру в пакет номер {} потому что в предыдущий насрал дядя витя...</code>",
        "added_to_different_msg": "УРА!!! Я ПОСРАЛ В ПАКЕТ" +
            "Я насрал в новый пакет. Положил его <a href=\"{}\">сюда</a> \n " +  # noqa: E131
            "<b>Ваша мать съест какашку через 5 секунд.</b>",
        "added_msg": "УРА!!! Я ПОСРАЛ В ПАКЕТ. Говно положил вот <a href=\"{}\">сюда</a> \n" +
            "<b>Ваша мать съест какашку через 5 секунд.</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig("silent_mode", "off", lambda: self.strings["silent_mode_cfg_doc"],
                                        "pack_name", '%username%\'s pack %packNumber%', lambda: self.strings["pack_name_cfg_doc"])  # noqa: E128

    def config_complete(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client

    async def kangcmd(self, message):
        """Kangs a sticker or image to your own pack!
        Usage: .kang (reply) (optional: emoji)
        If pack doesn\'t exist it will be created automatically.
        """
        user = await self.client.get_me()
        if not user.username:
            user.username = user.first_name
        reply = await message.get_reply_message()
        photo = None
        emojibypass = False
        is_anim = False
        emoji = ""
        silent_mode = self.config['silent_mode']
        if silent_mode != "on":
            await utils.answer(message, self.strings['preparing_msg'])
        if reply and reply.media:
            try:
                if reply.photo:
                    photo = io.BytesIO()
                    photo = await self.client.download_media(reply.photo, photo)
                elif reply.file:
                    if reply.file.mime_type == "application/x-tgsticker":
                        await self.client.download_file(reply.media.document, 'AnimatedSticker.tgs')
                        try:
                            emoji = reply.media.document.attributes[0].alt
                        except AttributeError:
                            emoji = reply.media.document.attributes[1].alt
                        emojibypass = True
                        is_anim = True
                        photo = 1
                    else:
                        photo = io.BytesIO()
                        await self.client.download_file(reply.media.document, photo)

                    # For kanging other sticker
                        if reply.sticker:
                            emoji = reply.file.emoji
                            emojibypass = True
                else:
                    await utils.answer(message, self.strings['unsupported_err'])
                    return
            except AttributeError:
                photo = io.BytesIO()
                photo = await self.client.download_media(reply.photo, photo)
                try:
                    emoji = reply.media.document.attributes[1].alt
                    emojibypass = True
                except AttributeError:
                    emojibypass = False
        else:
            await utils.answer(message, self.strings['reply_err'])
            return

        if silent_mode != "on":
            await utils.answer(message, self.strings['gettingType_msg'])

        if photo:
            splat = message.text.split()
            if not emojibypass or not emoji:
                emoji = "🤔"
            pack = 1
            if len(splat) == 3:
                pack = splat[2]  # User sent both
                emoji = splat[1]
            elif len(splat) == 2:
                if splat[1].isnumeric():
                    pack = int(splat[1])
                else:
                    emoji = splat[1]

            packname = f"a{user.id}_by_{user.username}_{pack}"
            packnick = self.config['pack_name'].replace('%username%',
                                                        f'@{user.username}').replace("%packNumber%",
                                                                                    str(pack))  # noqa: E128
            cmd = '/newpack'
            file = io.BytesIO()

            if not is_anim:
                image = await resize_photo(photo)
                file.name = "sticker.png"
                image.save(file, "PNG")
                await utils.answer(message, self.strings['image_kanging_msg'])
            else:
                packname += "_anim"
                packnick += " animated"
                cmd = '/newanimated'
                await utils.answer(message, self.strings['animated_kanging_msg'])

            response = urllib.request.urlopen(
                urllib.request.Request(f'http://t.me/addstickers/{packname}'))
            htmlstr = response.read().decode("utf8").split('\n')

            if "  A <strong>Telegram</strong> user has created the <strong>Sticker&nbsp;Set</strong>." not in htmlstr:
                async with self.client.conversation('Stickers') as conv:
                    await conv.send_message('/addsticker')
                    await conv.get_response()
                    await self.client.send_read_acknowledge(conv.chat_id)
                    await conv.send_message(packname)
                    x = await conv.get_response()
                    mtext = x.text
                    while mtext == PACK_FULL or mtext == PACK_FULL_RUS:
                        pack += 1
                        packname = f"a{user.id}_by_{user.username}_{pack}"
                        packnick = self.config['pack_name'].replace('%username%',
                                                                    f'@{user.username}').replace("%packNumber%",  # noqa: E128
                                                                                                str(pack))
                        if silent_mode != "on":
                            await utils.answer(message, self.strings['switching_msg'].format(str(pack)))
                        await conv.send_message(packname)
                        x = await conv.get_response()
                        mtext = x.text
                        if x.text == "Invalid pack selected." or x.text == "Не выбран набор стикеров.":
                            await conv.send_message(cmd)
                            await conv.get_response()
                            await self.client.send_read_acknowledge(conv.chat_id)
                            await conv.send_message(packnick)
                            await conv.get_response()
                            await self.client.send_read_acknowledge(conv.chat_id)
                            if is_anim:
                                await conv.send_file('AnimatedSticker.tgs', force_document=True)
                                DelFile('AnimatedSticker.tgs')
                            else:
                                file.seek(0)
                                await conv.send_file(file, force_document=True)
                            await conv.get_response()
                            await conv.send_message(emoji)
                            await self.client.send_read_acknowledge(conv.chat_id)
                            await conv.get_response()
                            await conv.send_message("/publish")
                            if is_anim:
                                await conv.get_response()
                                await conv.send_message(f"<{packnick}>")
                            await conv.get_response()
                            await self.client.send_read_acknowledge(conv.chat_id)
                            await conv.send_message("/skip")
                            await self.client.send_read_acknowledge(conv.chat_id)
                            await conv.get_response()
                            await conv.send_message(packname)
                            await self.client.send_read_acknowledge(conv.chat_id)
                            await conv.get_response()
                            await self.client.send_read_acknowledge(conv.chat_id)
                            await utils.answer(message,
                                        self.strings['added_to_different_msg'].format(  # noqa: E127
                                            f"t.me/addstickers/{packname}"
                                        ))
                            await sleep(5)
                            await message.delete()
                            return
                    if is_anim:
                        await conv.send_file('AnimatedSticker.tgs',
                                            force_document=True)  # noqa: E128
                        DelFile('AnimatedSticker.tgs')
                    else:
                        file.seek(0)
                        await conv.send_file(file, force_document=True)
                    await conv.get_response()
                    await conv.send_message(emoji)
                    await self.client.send_read_acknowledge(conv.chat_id)
                    await conv.get_response()
                    await conv.send_message('/done')
                    await conv.get_response()
                    await self.client.send_read_acknowledge(conv.chat_id)
            else:
                if silent_mode != "on":
                    await utils.answer(message, self.strings['pack_notExist'])
                async with self.client.conversation('Stickers') as conv:
                    await conv.send_message(cmd)
                    await conv.get_response()
                    await self.client.send_read_acknowledge(conv.chat_id)
                    await conv.send_message(packnick)
                    await conv.get_response()
                    await self.client.send_read_acknowledge(conv.chat_id)
                    if is_anim:
                        await conv.send_file('AnimatedSticker.tgs',
                                            force_document=True)  # noqa: E128
                        DelFile('AnimatedSticker.tgs')
                    else:
                        file.seek(0)
                        await conv.send_file(file, force_document=True)
                    await conv.get_response()
                    await conv.send_message(emoji)
                    await self.client.send_read_acknowledge(conv.chat_id)
                    await conv.get_response()
                    await conv.send_message("/publish")
                    if is_anim:
                        await conv.get_response()
                        await conv.send_message(f"<{packnick}>")
                    await conv.get_response()
                    await self.client.send_read_acknowledge(conv.chat_id)
                    await conv.send_message("/skip")
                    await self.client.send_read_acknowledge(conv.chat_id)
                    await conv.get_response()
                    await conv.send_message(packname)
                    await self.client.send_read_acknowledge(conv.chat_id)
                    await conv.get_response()
                    await self.client.send_read_acknowledge(conv.chat_id)
            await utils.answer(message,
                                self.strings['added_msg'].format(  # noqa: E127
                                    f"t.me/addstickers/{packname}"
                                ))
            await sleep(5)
            await message.delete()


async def resize_photo(photo):
    """ Resize the given photo to 512x512 """
    image = Image.open(photo)
    maxsize = (512, 512)
    if (image.width and image.height) < 512:
        size1 = image.width
        size2 = image.height
        if image.width > image.height:
            scale = 512 / size1
            size1new = 512
            size2new = size2 * scale
        else:
            scale = 512 / size2
            size1new = size1 * scale
            size2new = 512
        size1new = math.floor(size1new)
        size2new = math.floor(size2new)
        sizenew = (size1new, size2new)
        image = image.resize(sizenew)
    else:
        image.thumbnail(maxsize)

    return image
