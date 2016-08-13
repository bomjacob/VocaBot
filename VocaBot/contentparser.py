import math
from collections import defaultdict

from telegram import Emoji

from constants import Context, VOCADB_BASE_URL
from i18n import _


# I'm not exactly proud of this module's code.. but it does the job.


def names_text(song):
    if len(song['names']) > 1:
        names = _('<b>Additional names:</b>\n')
        for name in song['names']:
            if name['value'] != song['name']:
                names += name['value'] + '\n'
        return names

    return _('No additional names found\n')


def artists_text(entry, inline):
    if len(entry['artists']) > 0:
        artists = _('<b>Artists:</b>\n')
        for artist in entry['artists']:
            roles = []
            for role in artist['effectiveRoles'].split(', '):
                if role == 'Default':
                    roles.append(artist['categories'][:2])
                else:
                    roles.append(role[:2])

            artists += _('[<code>{roles}</code>] '
                         '{artist_name}').format(roles=','.join(roles), artist_name=artist['name'])

            if not inline:
                try:
                    artists += ' /ar_{}'.format(artist['artist']['id'])
                except KeyError:
                    pass

            artists += '\n'

        return artists

    return _('No artists found\n')


def vocadb_url(entry, song=False, artist=False, album=False):
    return '{base_url}{type}/{id}'.format(base_url=VOCADB_BASE_URL,
                                          type='S' if song else 'Ar' if artist else 'Al',
                                          id=entry['id'])


def content_parser(entries, info=False, inline=False, context=None, bot_name='', counts=None):
    text = ''

    if entries and len(entries) > 0:
        if info:
            entries = [entries]
        for i, entry in enumerate(entries):
            # Check if part of a disc listing
            track_number = None
            if 'song' in entry:
                track_number = entry['trackNumber']
                entry = entry['song']

            song, album, artist = False, False, False
            if 'songType' in entry:
                song = True
            if 'artistType' in entry:
                artist = True
            if 'discType' in entry:
                album = True

            if track_number is None or i != 0:
                text += '\n\n'

            try:
                if context == Context.related:
                    if i == 0:
                        text += _('<i>Matching artist</i>')
                    elif i == 1:
                        text += _('<i>Matching likes</i>')
                    elif i == 2:
                        text += _('<i>Matching tags</i>')
                    text += '\n'

                if song:
                    if track_number is None:
                        text += _('{emoji} <b>{name}</b>\n{artist}\n{type}').format(emoji=Emoji.MUSICAL_NOTE,
                                                                                    name=entry['name'],
                                                                                    artist=entry['artistString'],
                                                                                    type=entry['songType'])
                        if 'favoritedTimes' in entry:
                            text += ' ' + _('with {num} favourites').format(num=entry['favoritedTimes'])

                    else:
                        text += _('<code>{track_number})</code> <b>{name}</b>\n{artist}').format(
                            track_number=track_number,
                            name=entry['name'],
                            artist=entry['artistString'])

                if artist:
                    text += _('{emoji} <b>{name}</b>\n{type}').format(emoji=Emoji.MICROPHONE,
                                                                      name=entry['name'],
                                                                      type=entry['artistType'])
                if album:
                    text += _('{emoji} <b>{name}</b>\n{artist}\n{type}').format(emoji=Emoji.OPTICAL_DISC,
                                                                                name=entry['name'],
                                                                                artist=entry['artistString'],
                                                                                type=entry['discType'])

                if info:
                    text += '\n\n'
                    text += names_text(entry)
                    text += '\n'
                    if song:
                        if not inline:
                            text += _('<b>Derived songs:</b>') + ' /dev_{}\n'.format(entry['id'])
                            text += _('<b>Related songs:</b>') + ' /rel_{}\n'.format(entry['id'])
                            if 'originalVersionId' in entry:
                                text += '\n'
                                text += _('<b>Original song:</b>') + ' /info_{}\n'.format(entry['originalVersionId'])
                            text += '\n'
                            text += artists_text(entry, inline)

                        if 'pvServices' in entry:
                            if entry['pvServices'] == 'Nothing':
                                text += _('\nNo promotional videos found')

                    if artist:
                        if not inline:
                            if 'baseVoicebank' in entry:
                                text += _('<b>Base voicebank:</b>') + ' /a_{}\n\n'.format(entry['baseVoicebank']['id'])

                    if album:
                        if 'releaseDate' in entry:
                            if not entry['releaseDate']['isEmpty']:
                                # i18n? .-.
                                text += _('Release date: {date}').format(date=entry['releaseDate']['formatted'])

                    if inline and bot_name:
                        text += _('For more features use non-inline mode: {bot_name}').format(bot_name=bot_name)

                else:
                    if not inline:
                        text += _('\nInfo:')
                        if song:
                            text += ' /info_{}'.format(entry['id'])
                        if artist:
                            text += ' /ar_{}'.format(entry['id'])
                        if album:
                            text += ' /al_{}'.format(entry['id'])

            except OSError:
                pass

        if counts:
            text += _("\n\nFound {found_num} total. "
                      "Viewing page {cur_page}/{max_page}").format(found_num=counts[1],
                                                                   cur_page=math.ceil((counts[0] + 3) / 3),
                                                                   max_page=math.ceil(counts[1] / 3))

    else:
        if context == Context.search:
            text += _("I couldn't find what you were looking for. Did you misspell it?")
        elif context == Context.derived:
            text += _('No derived songs found.')
        elif context == Context.related:
            text += _('No related songs found.')
        else:
            text += _('Not found.')

    return text


def album_tracks(album, inline, bot_name):
    text = _('<b>Tracks')
    if not inline:
        text += _(' on {album_name} by {album_artist}</b>\n').format(album_name=album['name'],
                                                                     album_artist=album['artistString'])
    else:
        text += ':</b>\n'

    discs = defaultdict(list)
    for track in album['tracks']:
        discs[track['discNumber']].append(track)

    for i, (disc_number, tracks) in enumerate(discs.items()):
        if len(discs) > 1:
            if not i == 0:
                text += '\n\n'
            text += _('<i>Disc {disc_number}').format(disc_number=disc_number)
            if 'discs' in album and album['discs']:
                disc = [disc for disc in album['discs'] if disc['discNumber'] == disc_number]
                # Can't find an album to test this on:
                # if 'name' in disc:
                #     text += ' ' + disc['name']
            text += ':</i>\n'
        text += content_parser(tracks, inline=inline)

    if inline and bot_name:
        text += _('\n\nFor more features use non-inline mode: {bot_name}').format(bot_name=bot_name)

    return text
