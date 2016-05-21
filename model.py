# coding: utf-8
from config import db
import utils

def get_one(response):
    try:
        result = response[0]
    except IndexError:
        result = None
    return result


def create_feed(url, name, selectors, favicon, update_interval, content):
    now = utils.now()
    selectors = '\n'.join(selectors)
    favicon = buffer(favicon) if favicon else None
    return db.insert('feed', url=url, name=name, selector=selectors, favicon=favicon,
                     update_interval=update_interval, created=now, lastcheck=now, lastcontent=content)


def update_feed(feedid, fields):
    db.update('feed', vars={'feedid': feedid}, where='id=$feedid', **fields)


def add_feed_change(feedid, summary, details, is_error):
    db.insert('change', feedid=feedid, time=utils.now(), is_error=is_error, summary=summary, details=details)


def get_feed(feedid):
    return get_one(db.select('feed', {'feedid': feedid}, where='id=$feedid'))


def get_changes(feedid):
    return db.select('change', {'feedid': feedid}, where='feedid=$feedid', order='id DESC', limit=25)


def get_change(changeid):
    return get_one(db.select('change', {'changeid': changeid}, where='id=$changeid'))

def find_feed(url, selector):
    return get_one(db.select('feed', {'url': url, 'selector': '\n'.join(selector)}, where='url=$url AND selector=$selector'))
