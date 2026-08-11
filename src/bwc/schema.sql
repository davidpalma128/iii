-- BWC schema. Idempotent: safe to run on every startup.

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS members (
    id             INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash  TEXT NOT NULL,
    business_name  TEXT DEFAULT '',
    category       TEXT DEFAULT '',
    phone          TEXT DEFAULT '',
    scheduling_url TEXT DEFAULT '',
    photo_path     TEXT,
    is_admin       INTEGER NOT NULL DEFAULT 0,
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS referrals (
    id            INTEGER PRIMARY KEY,
    giver_id      INTEGER NOT NULL REFERENCES members(id),
    receiver_id   INTEGER NOT NULL REFERENCES members(id),
    contact_name  TEXT NOT NULL,
    contact_info  TEXT DEFAULT '',
    notes         TEXT DEFAULT '',
    referral_type TEXT NOT NULL DEFAULT 'outside'
                  CHECK (referral_type IN ('inside', 'outside')),
    temperature   TEXT NOT NULL DEFAULT 'warm'
                  CHECK (temperature IN ('hot', 'warm', 'cold')),
    status        TEXT NOT NULL DEFAULT 'given'
                  CHECK (status IN ('given', 'contacted', 'in_progress', 'closed', 'lost')),
    referral_date TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    CHECK (giver_id != receiver_id)
);
CREATE INDEX IF NOT EXISTS idx_referrals_giver    ON referrals(giver_id);
CREATE INDEX IF NOT EXISTS idx_referrals_receiver ON referrals(receiver_id);
CREATE INDEX IF NOT EXISTS idx_referrals_date     ON referrals(referral_date);

CREATE TABLE IF NOT EXISTS referral_updates (
    id          INTEGER PRIMARY KEY,
    referral_id INTEGER NOT NULL REFERENCES referrals(id) ON DELETE CASCADE,
    author_id   INTEGER NOT NULL REFERENCES members(id),
    new_status  TEXT CHECK (new_status IS NULL OR
                            new_status IN ('given', 'contacted', 'in_progress', 'closed', 'lost')),
    note        TEXT DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_referral_updates_referral ON referral_updates(referral_id);

CREATE TABLE IF NOT EXISTS one_to_ones (
    id         INTEGER PRIMARY KEY,
    member1_id INTEGER NOT NULL REFERENCES members(id),
    member2_id INTEGER NOT NULL REFERENCES members(id),
    met_on     TEXT NOT NULL,
    location   TEXT DEFAULT '',
    notes      TEXT DEFAULT '',
    created_by INTEGER NOT NULL REFERENCES members(id),
    created_at TEXT NOT NULL,
    CHECK (member1_id != member2_id)
);
CREATE INDEX IF NOT EXISTS idx_one_to_ones_met_on ON one_to_ones(met_on);

CREATE TABLE IF NOT EXISTS tyfcb (
    id              INTEGER PRIMARY KEY,
    thanker_id      INTEGER NOT NULL REFERENCES members(id),
    thanked_id      INTEGER NOT NULL REFERENCES members(id),
    amount_cents    INTEGER NOT NULL CHECK (amount_cents > 0),
    referral_id     INTEGER REFERENCES referrals(id),
    is_new_business INTEGER NOT NULL DEFAULT 1,
    notes           TEXT DEFAULT '',
    tyfcb_date      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    CHECK (thanker_id != thanked_id)
);
CREATE INDEX IF NOT EXISTS idx_tyfcb_thanker ON tyfcb(thanker_id);
CREATE INDEX IF NOT EXISTS idx_tyfcb_thanked ON tyfcb(thanked_id);
CREATE INDEX IF NOT EXISTS idx_tyfcb_date    ON tyfcb(tyfcb_date);
