PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS songs (
    id              INTEGER PRIMARY KEY,
    entity_id       TEXT NOT NULL,
    title           TEXT NOT NULL,
    artist          TEXT NOT NULL,
    thumbnail_url   TEXT,
    platform_links  TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS songs_entity_id ON songs(entity_id);

CREATE TABLE IF NOT EXISTS chat_songs (
    id              INTEGER PRIMARY KEY,
    chat_id         INTEGER NOT NULL,
    song_id         INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    first_user_id   INTEGER NOT NULL,
    first_user_name TEXT NOT NULL,
    mentions        INTEGER NOT NULL DEFAULT 1,
    first_seen_at   TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(chat_id, song_id)
);
CREATE INDEX IF NOT EXISTS chat_songs_by_chat ON chat_songs(chat_id, last_seen_at DESC);

CREATE TABLE IF NOT EXISTS reactions (
    chat_song_id    INTEGER NOT NULL REFERENCES chat_songs(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('like', 'dislike')),
    reacted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (chat_song_id, user_id)
);

CREATE TABLE IF NOT EXISTS chats (
    chat_id         INTEGER PRIMARY KEY,
    title           TEXT,
    digest_weekly   INTEGER NOT NULL DEFAULT 1,
    digest_monthly  INTEGER NOT NULL DEFAULT 1,
    last_active_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
