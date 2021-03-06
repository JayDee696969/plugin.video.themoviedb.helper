from resources.lib.requestapi import RequestAPI


class FanartTV(RequestAPI):
    def __init__(self, api_key=None, client_key=None, language=None, cache_long=None, cache_short=None):
        super(FanartTV, self).__init__(
            cache_short=cache_short, cache_long=cache_long,
            req_api_name='FanartTV', req_api_url='http://webservice.fanart.tv/v3', req_wait_time=0,
            req_api_key='?api_key=fcca59bee130b70db37ee43e63f8d6c1')
        self.req_api_key = '?api_key={0}'.format(api_key) if api_key else self.req_api_key
        self.req_api_key = '{0}&client_key={1}'.format(self.req_api_key, client_key) if client_key else self.req_api_key
        self.language = language[:2] if language else 'en'
        self.response, self.ftvtype, self.ftvid = None, None, None

    def get_artwork_request(self, ftvid, ftvtype, *args, **kwargs):
        """
        ftvtype can be 'movies' 'tv'
        ftvid is tmdb_id|imdb_id for movies and tvdb_id for tv
        """
        if not ftvtype or not ftvid:
            return
        if self.ftvtype != ftvtype or self.ftvid != ftvid:
            self.response = self.get_request_lc(ftvtype, ftvid, *args, **kwargs)
            self.ftvtype = ftvtype
            self.ftvid = ftvid
        return self.response

    def get_artwork_list(self, ftvid, ftvtype, artwork, *args, **kwargs):
        if not artwork:
            return []
        if self.response:
            if self.ftvtype != ftvtype or self.ftvid != ftvid:
                if not self.get_artwork_request(ftvtype, ftvid, *args, **kwargs):
                    return []
        elif not ftvtype or not ftvid or not self.get_artwork_request(ftvtype, ftvid, *args, **kwargs):
            return []
        return self.response.get(artwork, [])

    def get_artwork_best(self, ftvid, ftvtype, artwork, *args, **kwargs):
        best_like = -1
        best_item = None
        for i in self.get_artwork_list(ftvtype, ftvid, artwork):
            if i.get('lang', '') == self.language:
                return i.get('url', '')
            elif i.get('likes', 0) > best_like:
                best_item = i.get('url', '')
                best_like = i.get('likes', 0)
        return best_item

    def get_artwork_best_lc(self, ftvid, ftvtype, artwork, *args, **kwargs):
        cache_name = '{0}.fanarttv.best'.format(self.cache_name)
        cache_only = kwargs.pop('cache_only', False)
        cache_refresh = kwargs.pop('cache_refresh', False)
        return self.use_cache(
            self.get_artwork_best, ftvid, ftvtype, artwork, cache_days=self.cache_long,
            cache_only=cache_only, cache_refresh=cache_refresh, cache_name=cache_name)

    def get_movie_clearart(self, ftvid, *args, **kwargs):
        artwork = self.get_artwork_best_lc(ftvid, 'movies', 'hdmovieclearart', *args, **kwargs)
        return artwork or self.get_artwork_best_lc(ftvid, 'movies', 'movieclearart', *args, **kwargs)

    def get_movie_clearlogo(self, ftvid, *args, **kwargs):
        artwork = self.get_artwork_best_lc(ftvid, 'movies', 'hdmovielogo', *args, **kwargs)
        return artwork or self.get_artwork_best_lc(ftvid, 'movies', 'movielogo', *args, **kwargs)

    def get_movie_poster(self, ftvid, *args, **kwargs):
        return self.get_artwork_best_lc(ftvid, 'movies', 'movieposter', *args, **kwargs)

    def get_movie_fanart(self, ftvid, *args, **kwargs):
        return self.get_artwork_best_lc(ftvid, 'movies', 'moviebackground', *args, **kwargs)

    def get_movie_landscape(self, ftvid, *args, **kwargs):
        return self.get_artwork_best_lc(ftvid, 'movies', 'moviethumb', *args, **kwargs)

    def get_movie_banner(self, ftvid, *args, **kwargs):
        return self.get_artwork_best_lc(ftvid, 'movies', 'moviebanner', *args, **kwargs)

    def get_tvshow_clearart(self, ftvid, *args, **kwargs):
        artwork = self.get_artwork_best_lc(ftvid, 'tv', 'hdclearart', *args, **kwargs)
        return artwork or self.get_artwork_best_lc(ftvid, 'tv', 'clearart', *args, **kwargs)

    def get_tvshow_clearlogo(self, ftvid, *args, **kwargs):
        artwork = self.get_artwork_best_lc(ftvid, 'tv', 'hdtvlogo', *args, **kwargs)
        return artwork or self.get_artwork_best_lc(ftvid, 'tv', 'clearlogo', *args, **kwargs)

    def get_tvshow_banner(self, ftvid, *args, **kwargs):
        return self.get_artwork_best_lc(ftvid, 'tv', 'tvbanner', *args, **kwargs)

    def get_tvshow_landscape(self, ftvid, *args, **kwargs):
        return self.get_artwork_best_lc(ftvid, 'tv', 'tvthumb', *args, **kwargs)

    def get_tvshow_fanart(self, ftvid, *args, **kwargs):
        return self.get_artwork_best_lc(ftvid, 'tv', 'showbackground', *args, **kwargs)

    def get_tvshow_characterart(self, ftvid, *args, **kwargs):
        return self.get_artwork_best_lc(ftvid, 'tv', 'characterart', *args, **kwargs)

    def get_tvshow_allart(self, ftvid, *args, **kwargs):
        clearart = self.get_tvshow_clearart(ftvid, *args, **kwargs)
        clearlogo = self.get_tvshow_clearlogo(ftvid, *args, **kwargs)
        banner = self.get_tvshow_banner(ftvid, *args, **kwargs)
        landscape = self.get_tvshow_landscape(ftvid, *args, **kwargs)
        fanart = self.get_tvshow_fanart(ftvid, *args, **kwargs)
        characterart = self.get_tvshow_characterart(ftvid, *args, **kwargs)
        return {
            'clearart': clearart, 'clearlogo': clearlogo, 'banner': banner,
            'landscape': landscape, 'fanart': fanart, 'characterart': characterart}

    def get_tvshow_allart_lc(self, ftvid, *args, **kwargs):
        cache_name = '{0}.fanarttv.tvall'.format(self.cache_name)
        cache_only = kwargs.pop('cache_only', False)
        cache_refresh = kwargs.pop('cache_refresh', False)
        return self.use_cache(
            self.get_tvshow_allart, ftvid, cache_days=self.cache_long,
            cache_only=cache_only, cache_refresh=cache_refresh, cache_name=cache_name)

    def get_movie_allart(self, ftvid, *args, **kwargs):
        clearart = self.get_movie_clearart(ftvid, *args, **kwargs)
        clearlogo = self.get_movie_clearlogo(ftvid, *args, **kwargs)
        banner = self.get_movie_banner(ftvid, *args, **kwargs)
        landscape = self.get_movie_landscape(ftvid, *args, **kwargs)
        fanart = self.get_movie_fanart(ftvid, *args, **kwargs)
        return {
            'clearart': clearart, 'clearlogo': clearlogo, 'banner': banner,
            'landscape': landscape, 'fanart': fanart}

    def get_movie_allart_lc(self, ftvid, *args, **kwargs):
        cache_name = '{0}.fanarttv.movieall'.format(self.cache_name)
        cache_only = kwargs.pop('cache_only', False)
        cache_refresh = kwargs.pop('cache_refresh', False)
        return self.use_cache(
            self.get_movie_allart, ftvid, cache_days=self.cache_long,
            cache_only=cache_only, cache_refresh=cache_refresh, cache_name=cache_name)
