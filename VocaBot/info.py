from urllib.parse import unquote

from constants import PV_SERVICES
from contentparser import content_parser, album_tracks, vocadb_url
from i18n import _
from settings import with_voca_lang, translate
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext.dispatcher import run_async
from util import edit_message_text, pv_parser, get_lyric_lang
from vocadb import voca_db


# noinspection PyTypeChecker
def song_keyboard(data, inline=False):
    if not data:
        return
    keyboard = [[]]
    keyboard[-1].append(InlineKeyboardButton(text='📜' + _('Lyrics'),
                                             callback_data='ly|{}'.format(data['id'])))

    # TODO: Add "Artist Info" button to inline

    # If it's from an entry search we get pVs instead of pvServices
    if 'pVs' in data:
        data['pvServices'] = ', '.join([x['service'] for x in data['pVs']])

    if not data['pvServices'] == 'Nothing':
        keyboard.append([])
        for service in PV_SERVICES:
            if service in data['pvServices']:
                callback_data = 'pv|{}|{}'.format(data['id'], service)
                keyboard[-1].append(InlineKeyboardButton(text='🎥' + service,
                                                         callback_data=callback_data))

    keyboard.append([
        InlineKeyboardButton(text=_('Share song'), switch_inline_query='!s#{}'.format(data['id'])),
        InlineKeyboardButton(text=_('View on VocaDB.net'), url=vocadb_url(data, song=True))
    ])

    return InlineKeyboardMarkup(keyboard)


# noinspection PyTypeChecker
def artist_keyboard(data, inline=False):
    if not data:
        return
    keyboard = []
    if not inline:
        keyboard.append([
            InlineKeyboardButton(text='🔝' + _('Popular songs'),
                                 callback_data='arlist|ps|{}'.format(data['id'])),
            InlineKeyboardButton(text='🕒' + _('Latest songs'),
                                 callback_data='arlist|ls|{}'.format(data['id']))
        ])
        keyboard.append([
            InlineKeyboardButton(text='🔝' + _('Popular albums'),
                                 callback_data='arlist|pa|{}'.format(data['id'])),
            InlineKeyboardButton(text='🕒' + _('Latest albums'),
                                 callback_data='arlist|la|{}'.format(data['id']))
        ])

    keyboard.append([
        InlineKeyboardButton(text=_('Share artist'), switch_inline_query='!ar#{}'.format(data['id'])),
        InlineKeyboardButton(text=_('View on VocaDB.net'), url=vocadb_url(data, artist=True))
    ])

    return InlineKeyboardMarkup(keyboard)


# noinspection PyTypeChecker
def album_keyboard(data, inline=False):
    if not data:
        return
    keyboard = [[]]
    keyboard[-1].append(InlineKeyboardButton(text='🎼' + _('Tracks'),
                                             callback_data='allist|{}'.format(data['id'])))

    keyboard.append([
        InlineKeyboardButton(text=_('Share Album'), switch_inline_query='!al#{}'.format(data['id'])),
        InlineKeyboardButton(text=_('View on VocaDB.net'), url=vocadb_url(data, album=True))
    ])

    return InlineKeyboardMarkup(keyboard)


@run_async
@translate
@with_voca_lang
def song(bot, update, groups, lang):
    data = voca_db.song(groups[0], 'MainPicture, Names, Lyrics, Artists, PVs', lang=lang)
    update.message.reply_text(content_parser(data, info=True), reply_markup=song_keyboard(data),
                              parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@run_async
@translate
@with_voca_lang
def artist(bot, update, groups, lang):
    data = voca_db.artist(groups[0], 'MainPicture, Names', lang=lang)
    update.message.reply_text(content_parser(data, info=True), reply_markup=artist_keyboard(data),
                              parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@run_async
@translate
@with_voca_lang
def album(bot, update, groups, lang):
    data = voca_db.album(groups[0], 'MainPicture, Names, Discs, Tracks', lang=lang)
    update.message.reply_text(content_parser(data, info=True), reply_markup=album_keyboard(data),
                              parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@run_async
@translate
@with_voca_lang
def lyrics(bot, update, groups, lang):
    data = voca_db.song(groups[0], lang=lang, fields='MainPicture, Names, Lyrics, Artists, PVs')

    reply_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_lyric_lang(lyric['translationType'], lyric['cultureCode']),
                              callback_data='ly|{}|{}'.format(data['id'],
                                                              lyric['id'])) for lyric in data['lyrics']]])

    inline = bool(update.callback_query.inline_message_id)

    if data['lyrics']:
        if groups[1] == '':
            text = _('What language would you like the lyrics for <b>{name} by {artist}</b> in?').format(
                name=data['name'],
                artist=data['artistString'])
            edit_message_text(bot, update, send_if_possible=True,
                              text=text,
                              reply_markup=reply_keyboard,
                              parse_mode=ParseMode.HTML)
            update.callback_query.answer()
        else:
            for lyric in data['lyrics']:
                if lyric['id'] == int(groups[1]):
                    text = ''
                    if inline:
                        text = content_parser(data, info=True, inline=True, bot_name=bot.username)
                    text += '\n\n' + '📜'
                    text += _('<b>{lang} lyrics for {song} by {artist}</b>\n'
                              '{lyrics}').format(song=data['name'],
                                                 artist=data['artistString'],
                                                 lang=get_lyric_lang(lyric['translationType'], lyric['cultureCode'],
                                                                     long=True),
                                                 lyrics=lyric['value'])
                    edit_message_text(bot, update,
                                      text=text,
                                      reply_markup=song_keyboard(data, inline=True) if inline else reply_keyboard,
                                      parse_mode=ParseMode.HTML)
                    update.callback_query.answer()
    else:
        update.callback_query.answer(_('No lyrics found.'))


@run_async
@translate
@with_voca_lang
def pv(bot, update, groups, lang):
    data = voca_db.song(groups[0], lang=lang, fields='MainPicture, Names, Lyrics, Artists, PVs')

    inline = bool(update.callback_query.inline_message_id)

    # TODO: Deal with several of the same service. Ex: 17523 has two YT
    for pv_info in data['pVs']:
        if pv_info['service'] == groups[1]:
            text = ''
            if inline:
                text = content_parser(data, info=True, inline=True, bot_name=bot.username)
            text += '\n\n' + '🎥'
            text += _('<b>{service} PV for {song} by {artist}</b>\n'
                      'PV Title:\n{name}\n{url}').format(song=data['name'],
                                                         artist=data['artistString'],
                                                         service=pv_info['service'],
                                                         name=pv_info['name'],
                                                         url=pv_info['url'])
            edit_message_text(bot, update, send_if_possible=True,
                              text=text,
                              reply_markup=song_keyboard(data, inline=True) if inline else None,
                              parse_mode=ParseMode.HTML)

            update.callback_query.answer()
            return


@run_async
@translate
@with_voca_lang
def album_list(bot, update, groups, lang):
    data = voca_db.album(groups[0], 'MainPicture, Names, Discs, Tracks', lang=lang)

    inline = bool(update.callback_query.inline_message_id)

    text = ''
    if inline:
        text = content_parser(data, info=True, inline=True, bot_name=bot.username)
    text += '\n\n'
    text += album_tracks(data, inline=inline)

    edit_message_text(bot, update, send_if_possible=True,
                      text=text,
                      reply_markup=album_keyboard(data, inline=True) if inline else None,
                      parse_mode=ParseMode.HTML)
    update.callback_query.answer()


@run_async
@translate
@with_voca_lang
def song_by_pv(bot, update, lang):
    for entity in update.message.entities:
        if entity.type == 'url':
            pv = pv_parser(update.message.text)
            if pv:
                data = voca_db.song_by_pv(pv[0], pv[1], 'MainPicture, Names, Lyrics, Artists, PVs', lang=lang)
                update.message.reply_text(content_parser(data, info=True), reply_markup=song_keyboard(data),
                                          parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def forwarded(bot, update, update_queue):
    url = 'https://telegram.me/{}?start=cmd'.format(bot.username)
    for i, entity in enumerate(update.message.entities[:]):
        if entity.type == 'text_link':
            if entity.url.startswith(url):
                update.message.text = unquote(entity.url)[len(url) + 1:]
                del update.message.entities[i]
                update_queue.put(update)
