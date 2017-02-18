#!/usr/bin/env python
# coding: utf-8
import model
import config
import htmlproc
import logging as log
import utils

log.basicConfig(format='%(asctime)s %(message)s', level=log.INFO)


def iterate_feeds_needing_update():
    # return config.db.select('feed', {'now': utils.now()}, where='lastcheck + update_interval< $now')
    return config.db.select('feed')


def get_summary_from_diff(s):
    assert s
    i1 = s.find('<ins>')
    if i1 > -1:
        i2 = s.find('</ins>')
        assert i2 > -1
    else:
        i1 = s.find('<del>')
        assert i1 > -1
        i2 = s.find('</del>')
        assert i2 > -1
    assert i2 > i1
    summary = s[i1 + 5:i2]
    summary = summary[:100]
    return summary

def update_feed(feed):
    log.debug('Updating feed %d (%s)', feed['id'], feed['url'])
    feed_fields_updates = {'lastcheck': utils.now()}

    selectors = str(feed['selector']).splitlines()
    res = htmlproc.get_prepared_html(feed['url'], selectors)
    if 'error' in res:
        if feed['lasterror'] == res['error']:
            log.warn('Repeated error getting page content" %s', res['error'])
        else:
            log.warn('New error getting page content: %s', res['error'])
            feed_fields_updates['lasterror'] = res['error']
            model.add_feed_change(feed['id'], summary='Error getting page', details=res['error'], is_error=True)
    else:
        changes = htmlproc.get_web_safe_diff(feed['lastcontent'], res['txt'])
        feed_fields_updates['lasterror'] = None
        if not changes:
            log.debug('Page not changed')
            if feed['lasterror']:
                model.add_feed_change(feed['id'], summary='Fixed getting page',
                                      details='Page retreiving now works fine, no changes detected', is_error=True)
        else:
            log.debug('Page changed')
            details = changes
            summary = get_summary_from_diff(changes)
            model.add_feed_change(feed['id'], details=details, is_error=False, summary=summary)
            feed_fields_updates['lastcontent'] = res['txt']
    model.update_feed(feed['id'], feed_fields_updates)



if __name__ == '__main__':
    log.info('Updater started')
    for feed in iterate_feeds_needing_update():
        update_feed(feed)
    log.info('Updater ended')
