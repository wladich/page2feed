CREATE TABLE feed (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    selector TEXT,
    name TEXT NOT NULL,
    favicon BLOB,
    update_interval NUMBER NOT NULL,
    created NUMBER NOT NULL,
    lastcheck NUMBER,
    lastcontent TEXT,
    lasterror TEXT,
    UNIQUE(url, selector, update_interval)
);

CREATE INDEX idx_feed_lastcheck ON feed(lastcheck);
CREATE INDEX idx_feed_url ON feed(url);

CREATE TABLE change (
    id INTEGER PRIMARY KEY,
    feedid INTEGER,
    time INTEGER,
    summary TEXT,
    details TEXT,
    is_error BOOLEAN,
    FOREIGN KEY(feedid) REFERENCES feed(id)
);

CREATE INDEX idx_change_feedid ON change(feedid);
CREATE INDEX idx_change_time ON change(time);

PRAGMA foreign_keys = ON;