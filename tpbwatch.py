# watch a TPB user for new uploads

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.urlfetch import fetch
from google.appengine.ext import db
from google.appengine.api import memcache

from BeautifulSoup import BeautifulSoup
import cgi
import re

tpb = 'http://thepiratebay.org'

class ItemTPB(db.Model):
    tpb_user = db.StringProperty()
    tpb_search = db.StringProperty()
    url = db.StringProperty()
    date = db.DateTimeProperty(auto_now_add=True)

def make_soup(self, user):
    url = tpb + '/user/' + user
    try:
        fetch_ob = fetch(url)
        html = fetch_ob.content
    except:
        pass

    code = fetch_ob.status_code
    if code != 200:
        html = 'Failed to fetch url: %d' % code

    cleaner = re.compile(r"SCR\'\+\'IPT", re.IGNORECASE)
    html = cleaner.sub('SCRIPT', html, 0)

    soup = BeautifulSoup(html)
    return soup


search_form = '<html><body><form method="get">user:<input type="text" name="user">search:<input type="text" name="search"><input type="submit"></form></body></html>'
def search(self, user, search):
    soup = make_soup(self, user)
    result = [] 
    try:
        table = soup.find('table', {'id': 'searchResult'})
        items = table.findAll('a', {'class': 'detLink'})
        m = re.compile(search, re.IGNORECASE);
        for link in items:
            res = m.search(link['title'])
            if res is not None:
                result += [(link['title'], tpb + link['href'])]
    except:
        pass

    return result

rss_template = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <title>__TPB_SEARCH__</title>
        <description>Results of search for \'__TPB_SEARCH__\' under user __TPB_USER__</description>
        <link>http://tpbwatch.appspot.com</link>
        <language>en-us</language>
        __RSS_ITEMS__
      </channel>
    </rss>"""
def generate_rss(tpb_user, tpb_search, items):
    rss_items = ''
    for item in items:
        rss_items += '<item><title>%s</title><link>%s</link><description>%s</description></item>' % (item[0], item[1], item[1])
    rss = re.sub('__RSS_ITEMS__', rss_items, rss_template, 0)
    rss = re.sub('__TPB_USER__', tpb_user, rss, 0)
    rss = re.sub('__TPB_SEARCH__', tpb_search, rss, 0)

    return rss


class MainPage(webapp.RequestHandler):
    def get(self):
        tpb_user = cgi.escape(self.request.get('user'))
        tpb_search = cgi.escape(self.request.get('search'))
        cache_key = 'tpb_user=%s,tpb_search=%s' % (tpb_user, tpb_search)

        if not tpb_user or not tpb_search:
            self.response.headers['Content-Type'] = 'text/html'
            self.response.out.write(search_form)
        else:
            self.response.headers['Content-Type'] = 'application/rss+xml'
            feed_data = memcache.get(cache_key)
            feed_data = None
            if feed_data is None:
                # cache expired, time to update the db
                items = search(self, tpb_user, tpb_search)
                feed_data = generate_rss(tpb_user, tpb_search, items)
                memcache.add(cache_key, feed_data, 900)

            self.response.out.write(feed_data)


application = webapp.WSGIApplication(
    [('/', MainPage)],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
