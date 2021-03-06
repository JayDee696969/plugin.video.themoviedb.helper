import sys
import xbmc
import xbmcgui
import xbmcvfs
import datetime
import resources.lib.utils as utils
from json import loads
from string import Formatter
from collections import defaultdict
from resources.lib.plugin import Plugin
from resources.lib.kodilibrary import KodiLibrary
from resources.lib.traktapi import TraktAPI
from resources.lib.listitem import ListItem


def string_format_map(fmt, d):
    try:
        str.format_map
    except AttributeError:
        parts = Formatter().parse(fmt)
        return fmt.format(**{part[1]: d[part[1]] for part in parts})
    else:
        return fmt.format(**d)


class Player(Plugin):
    def __init__(self):
        super(Player, self).__init__()
        self.traktapi = TraktAPI()
        self.search_movie, self.search_episode, self.play_movie, self.play_episode = [], [], [], []
        self.item = defaultdict(lambda: '+')
        self.itemlist = []
        self.actions = []
        self.players = {}

    def setup_players(self, tmdbtype=None, details=False, clearsetting=False):
        self.build_players(tmdbtype)
        if details:
            self.build_details()
        self.build_selectbox(clearsetting)

    def get_itemindex(self, force_dialog=False):
        default_player_movies = self.addon.getSetting('default_player_movies')
        default_player_episodes = self.addon.getSetting('default_player_episodes')
        if force_dialog or (self.itemtype == 'movie' and not default_player_movies) or (self.itemtype == 'episode' and not default_player_episodes):
            utils.kodi_log('Player -- Asked user to select player', 2)
            return xbmcgui.Dialog().select(self.addon.getLocalizedString(32042), self.itemlist)
        itemindex = -1
        with utils.busy_dialog():
            for index in range(0, len(self.itemlist)):
                label = self.itemlist[index].getLabel()
                if (label == default_player_movies and self.itemtype == 'movie') or (label == default_player_episodes and self.itemtype == 'episode'):
                    utils.kodi_log('Player -- Attempting to play with default player:\n{0}'.format(label), 2)
                    return index
        return itemindex

    def play_external(self, force_dialog=False):
        utils.kodi_log('Player -- Attempting to play external', 2)
        itemindex = self.get_itemindex(force_dialog=force_dialog)

        if not itemindex > -1:
            utils.kodi_log('Player -- User cancelled or default player not found', 2)
            return False

        player = self.actions[itemindex]
        if not player or not player[1]:
            utils.kodi_log('Player -- Selected player incorrectly configured', 2)
            return False

        resolve_url = False
        if isinstance(player[1], list):
            actionlist = player[1]
            player = (False, actionlist[0])
            utils.kodi_log('Player -- Action list for selected player:\n{0}'.format(actionlist), 2)
            with utils.busy_dialog():
                for d in actionlist[1:]:
                    if player[0]:
                        break  # Playable item found so let's break loop and play it
                    folder = KodiLibrary().get_directory(string_format_map(player[1], self.item))
                    x = 0
                    for f in folder:
                        x += 1
                        for k, v in d.items():
                            if k == 'position':
                                if utils.try_parse_int(string_format_map(v, self.item)) != x:
                                    break  # Not the item position we want so let's move on to next item
                            elif not f.get(k) or string_format_map(v, self.item) not in u'{}'.format(f.get(k, '')):
                                break  # Item's key value doesn't match value we are looking for so move onto next item
                        else:
                            resolve_url = True if f.get('filetype') == 'file' else False
                            player = (resolve_url, f.get('file'))
                            break  # Item matches all our criteria so let's move onto our next action
                    else:
                        utils.kodi_log('Player -- Failed to {0}'.format(self.itemlist[itemindex].getLabel()), 2)
                        xbmcgui.Dialog().ok(self.itemlist[itemindex].getLabel(), self.addon.getLocalizedString(32040), self.addon.getLocalizedString(32041))
                        return self.play_external(force_dialog=True)

        if player and player[1]:
            utils.kodi_log('Player -- Attempting to play item', 2)
            xbmc.executebuiltin('Dialog.Close(12003)')
            action = string_format_map(player[1], self.item)
            if player[0]:
                utils.kodi_log('Player -- Playing found item:\n{0}'.format(action), 2)
                xbmc.Player().play(action, ListItem(library='video', **self.details).set_listitem())
                return action
            action = u'Container.Update({0})'.format(action) if xbmc.getCondVisibility("Window.IsMedia") else u'ActivateWindow(videos,{0},return)'.format(action)
            utils.kodi_log('Player -- Search action:\n{0}'.format(action), 2)
            xbmc.executebuiltin(action) if sys.version_info.major == 3 else xbmc.executebuiltin(action.encode('utf-8'))
            return action

    def play(self, itemtype, tmdb_id, season=None, episode=None):
        self.itemtype, self.tmdb_id, self.season, self.episode = itemtype, tmdb_id, season, episode
        self.tmdbtype = 'tv' if self.itemtype in ['episode', 'tv'] else 'movie'
        self.details = self.tmdb.get_detailed_item(self.tmdbtype, tmdb_id, season=season, episode=episode)
        self.item['imdb_id'] = self.details.get('infolabels', {}).get('imdbnumber')
        self.item['originaltitle'] = self.details.get('infolabels', {}).get('originaltitle')
        self.item['title'] = self.details.get('infolabels', {}).get('tvshowtitle') or self.details.get('infolabels', {}).get('title')
        self.item['year'] = self.details.get('infolabels', {}).get('year')
        is_local = False
        if self.details and self.itemtype == 'movie':
            utils.kodi_log('Player -- Searching KodiDb for local movie', 2)
            is_local = self.playmovie()
        if self.details and self.itemtype == 'episode':
            utils.kodi_log('Player -- Searching KodiDb for local episode', 2)
            is_local = self.playepisode()
        if is_local:
            utils.kodi_log('Player -- Playing local item:\n{0}'.format(is_local), 2)
            return is_local

        with utils.busy_dialog():
            self.setup_players(details=True)

        if not self.itemlist:
            utils.kodi_log('Player -- No players to display!', 2)
            return False

        return self.play_external()

    def build_details(self):
        self.item['id'] = self.tmdb_id
        self.item['tmdb'] = self.tmdb_id
        self.item['imdb'] = self.details.get('infolabels', {}).get('imdbnumber')
        self.item['name'] = u'{0} ({1})'.format(self.item.get('title'), self.item.get('year'))
        self.item['firstaired'] = self.details.get('infolabels', {}).get('premiered')
        self.item['premiered'] = self.details.get('infolabels', {}).get('premiered')
        self.item['released'] = self.details.get('infolabels', {}).get('premiered')
        self.item['showname'] = self.item.get('title')
        self.item['clearname'] = self.item.get('title')
        self.item['tvshowtitle'] = self.item.get('title')
        self.item['title'] = self.item.get('title')
        self.item['thumbnail'] = self.details.get('thumb')
        self.item['poster'] = self.details.get('poster')
        self.item['fanart'] = self.details.get('fanart')
        self.item['now'] = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')

        if self.traktapi:
            slug_type = utils.type_convert(self.tmdbtype, 'trakt')
            trakt_details = self.traktapi.get_details(slug_type, self.traktapi.get_traktslug(slug_type, 'tmdb', self.tmdb_id))
            self.item['trakt'] = trakt_details.get('ids', {}).get('trakt')
            self.item['imdb'] = trakt_details.get('ids', {}).get('imdb')
            self.item['tvdb'] = trakt_details.get('ids', {}).get('tvdb')
            self.item['slug'] = trakt_details.get('ids', {}).get('slug')

        if self.itemtype == 'episode':  # Do some special episode stuff
            self.item['id'] = self.item.get('tvdb')
            self.item['title'] = self.details.get('infolabels', {}).get('title')  # Set Episode Title
            self.item['name'] = u'{0} S{1:02d}E{2:02d}'.format(self.item.get('showname'), int(self.season), int(self.episode))
            self.item['season'] = self.season
            self.item['episode'] = self.episode

        if self.traktapi and self.itemtype == 'episode':
            trakt_details = self.traktapi.get_details(slug_type, self.item.get('slug'), season=self.season, episode=self.episode)
            self.item['epid'] = trakt_details.get('ids', {}).get('tvdb')
            self.item['epimdb'] = trakt_details.get('ids', {}).get('imdb')
            self.item['eptmdb'] = trakt_details.get('ids', {}).get('tmdb')
            self.item['eptrakt'] = trakt_details.get('ids', {}).get('trakt')

        for k, v in self.item.copy().items():
            v = u'{0}'.format(v)
            self.item[k] = v.replace(',', '')
            self.item[k + '_+'] = v.replace(' ', '+')
            self.item[k + '_-'] = v.replace(' ', '-')
            self.item[k + '_escaped'] = v.replace(' ', '%2520')
            self.item[k + '_escaped+'] = v.replace(' ', '%252B')

    def build_players(self, tmdbtype=None):
        basedirs = ['special://profile/addon_data/plugin.video.themoviedb.helper/players/']
        if self.addon.getSettingBool('bundled_players'):
            basedirs.append('special://home/addons/plugin.video.themoviedb.helper/resources/players/')
        for basedir in basedirs:
            files = [x for x in xbmcvfs.listdir(basedir)[1] if x.endswith('.json')]
            for file in files:
                vfs_file = xbmcvfs.File(basedir + file)
                try:
                    content = vfs_file.read()
                    meta = loads(content) or {}
                finally:
                    vfs_file.close()
                if not meta.get('plugin') or not xbmc.getCondVisibility(u'System.HasAddon({0})'.format(meta.get('plugin'))):
                    utils.kodi_log('Player -- {0}\nPlugin {1} not found! Skipping...'.format(file, meta.get('plugin', 'undefined')), 2)
                    continue  # Don't have plugin so skip

                utils.kodi_log('Player -- Adding players...\n{0}'.format(file), 2)
                tmdbtype = tmdbtype or self.tmdbtype
                priority = utils.try_parse_int(meta.get('priority')) or 1000
                if tmdbtype == 'movie' and meta.get('search_movie'):
                    self.search_movie.append((vfs_file, priority))
                if tmdbtype == 'movie' and meta.get('play_movie'):
                    self.play_movie.append((vfs_file, priority))
                if tmdbtype == 'tv' and meta.get('search_episode'):
                    self.search_episode.append((vfs_file, priority))
                if tmdbtype == 'tv' and meta.get('play_episode'):
                    self.play_episode.append((vfs_file, priority))
                self.players[vfs_file] = meta
        utils.kodi_log('Player -- {0} players built'.format(len(self.players)), 2)

    def build_selectbox(self, clearsetting=False):
        self.itemlist, self.actions = [], []
        if clearsetting:
            self.itemlist.append(xbmcgui.ListItem(xbmc.getLocalizedString(13403)))  # Clear Default
        for i in sorted(self.play_movie, key=lambda x: x[1]):
            self.itemlist.append(xbmcgui.ListItem(u'{0} {1}'.format(self.addon.getLocalizedString(32061), self.players.get(i[0], {}).get('name', ''))))
            self.actions.append((True, self.players.get(i[0], {}).get('play_movie', '')))
        for i in sorted(self.search_movie, key=lambda x: x[1]):
            self.itemlist.append(xbmcgui.ListItem(u'{0} {1}' .format(xbmc.getLocalizedString(137), self.players.get(i[0], {}).get('name', ''))))
            self.actions.append((False, self.players.get(i[0], {}).get('search_movie', '')))
        for i in sorted(self.play_episode, key=lambda x: x[1]):
            self.itemlist.append(xbmcgui.ListItem(u'{0} {1}'.format(self.addon.getLocalizedString(32061), self.players.get(i[0], {}).get('name', ''))))
            self.actions.append((True, self.players.get(i[0], {}).get('play_episode', '')))
        for i in sorted(self.search_episode, key=lambda x: x[1]):
            self.itemlist.append(xbmcgui.ListItem(u'{0} {1}'.format(xbmc.getLocalizedString(137), self.players.get(i[0], {}).get('name', ''))))
            self.actions.append((False, self.players.get(i[0], {}).get('search_episode', '')))
        utils.kodi_log('Player -- Select box built with {0} actions'.format(len(self.actions)), 2)

    def playfile(self, file):
        if file:
            xbmc.executebuiltin(u'PlayMedia({0})'.format(file))
            return file

    def playmovie(self):
        fuzzy_match = self.addon.getSettingBool('fuzzymatch_movie')
        return self.playfile(KodiLibrary(dbtype='movie').get_info('file', fuzzy_match=fuzzy_match, **self.item))

    def playepisode(self):
        fuzzy_match = self.addon.getSettingBool('fuzzymatch_tv')
        dbid = KodiLibrary(dbtype='tvshow').get_info('dbid', fuzzy_match=fuzzy_match, **self.item)
        return self.playfile(KodiLibrary(dbtype='episode', tvshowid=dbid).get_info('file', season=self.season, episode=self.episode))
