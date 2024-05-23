# coding: utf-8
import web
from web import form
import htmlproc
import model
import utils
import datetime
import config

urls = (
    '/', 'NewFeed',
    r'/(\d+)', 'Feed',
    r'/change/(\d+)', 'Change',
    r'/rss/(\d+)', 'RSS'
)

DEFAULT_UPDATE_INTERVAL = 1 * 3600

new_feed_form = form.Form(
    form.Textbox('url', form.notnull, description='Page URL', size=100),
    form.Textarea('selector', description='Element(s) selector', rows=10, cols=20)
)


def rss_format_date(ts):
    dt = datetime.datetime.utcfromtimestamp(ts)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

def html_filter_pre(s):
    s = web.websafe(s)
    s = s.replace(' ', '&nbsp;').replace('\n', '<br/>\n')
    return s

render = web.template.render('templates/', base='layout', globals={'pre': html_filter_pre})
render_raw = web.template.render('templates/', globals={'format_time': rss_format_date})


class NewFeed(object):
    def GET(self):
        frm = new_feed_form()
        return render.newfeed(frm)

    def POST(self):
        frm = new_feed_form()
        if not frm.validates():
            return render.newfeed(frm)
        selectors = frm['selector'].value.splitlines()
        selectors = [s.strip() for s in selectors]
        selectors = [sel for sel in selectors if sel]

        feed = model.find_feed(frm['url'].value, selectors)
        if feed:
            return web.redirect('/%s' % feed['id'])
        res = htmlproc.get_prepared_html(frm['url'].value, selectors)
        if 'error' in res:
            frm.note = res['error']
            return render.newfeed(frm)
        # TODO: limit document size
        url = res['url']
        feed = model.find_feed(url, selectors)
        if feed:
            return web.redirect('/%s' % feed['id'])
        frm['url'].value = url
        feed_name = res['title'] or url
        if 'do_preview' in web.input():
            return render.newfeed(frm, page_preview=res['txt'], feed_name=feed_name)
        else:
            title = res['title']
            feedid = model.create_feed(url=url, name=feed_name,  selectors=selectors,
                                       favicon=utils.get_favicon(url), update_interval=DEFAULT_UPDATE_INTERVAL,
                                       content=res['txt'])
            return web.redirect('/%s' % feedid)


class Feed(object):
    def GET(self, feedid):
        feed = model.get_feed(feedid)
        if not feed:
            return web.notfound()
        changes = model.get_changes(feedid)
        rss_url = config.base_url + '/rss/%s' % feed['id']
        return render.feed(feed=feed, changes=changes, rss_url=rss_url)


class Change(object):
    def GET(self, changeid):
        change = model.get_change(changeid)
        if not change:
            return web.notfound()
        feed = model.get_feed(change['feedid'])
        return render.change(feed, change)


class RSS(object):
    def GET(self, feedid):
        feed = model.get_feed(feedid)
        if not feed:
            return web.notfound()
        changes = model.get_changes(feed['id'])
        return render_raw.rss(feed, changes)


app = web.application(urls, globals())
application = app.wsgifunc()

if __name__ == "__main__":
    app.run()
