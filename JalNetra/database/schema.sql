PRAGMA foreign_keys = ON;

CREATE TABLE zone (
    id TEXT PRIMARY KEY,
    lake_name TEXT NOT NULL,
    name TEXT NOT NULL,
    latitude REAL CHECK (latitude BETWEEN -90 AND 90),
    longitude REAL CHECK (longitude BETWEEN -180 AND 180),
    marker_x REAL NOT NULL CHECK (marker_x BETWEEN 0 AND 1),
    marker_y REAL NOT NULL CHECK (marker_y BETWEEN 0 AND 1),
    UNIQUE (lake_name, name),
    CHECK ((latitude IS NULL) = (longitude IS NULL))
);

CREATE TABLE report (
    id TEXT PRIMARY KEY,
    data_mode TEXT NOT NULL CHECK (data_mode IN ('demo', 'live')),
    request_id TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    zone_id TEXT NOT NULL REFERENCES zone (id),
    observed_at TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    image_path TEXT NOT NULL UNIQUE,
    image_fingerprint TEXT NOT NULL,
    note TEXT,
    ph REAL,
    temperature_c REAL,
    current_attempt INTEGER,
    UNIQUE (data_mode, request_id),
    UNIQUE (id, data_mode, zone_id),
    FOREIGN KEY (id, current_attempt) REFERENCES analysis_attempt (report_id, attempt)
);

CREATE TABLE analysis_attempt (
    report_id TEXT NOT NULL REFERENCES report (id),
    attempt INTEGER NOT NULL CHECK (attempt > 0),
    source TEXT NOT NULL CHECK (source IN ('live_model', 'captured_replay', 'simulated')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'classified', 'no_target_signs', 'needs_review')),
    image_quality TEXT CHECK (image_quality IN ('usable', 'unclear')),
    started_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    finished_at TEXT,
    review_reason TEXT,
    PRIMARY KEY (report_id, attempt)
);

CREATE TABLE detection (
    report_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('foam', 'algae_like_growth', 'dumping')),
    cue TEXT NOT NULL CHECK (length(trim(cue)) > 0),
    PRIMARY KEY (report_id, attempt, category),
    FOREIGN KEY (report_id, attempt) REFERENCES analysis_attempt (report_id, attempt)
);

CREATE TABLE complaint_draft (
    id TEXT PRIMARY KEY,
    data_mode TEXT NOT NULL CHECK (data_mode IN ('demo', 'live')),
    zone_id TEXT NOT NULL REFERENCES zone (id),
    category TEXT NOT NULL CHECK (category IN ('foam', 'algae_like_growth', 'dumping')),
    recipient TEXT,
    draft_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (id, data_mode, zone_id, category)
);

CREATE TABLE complaint_evidence (
    draft_id TEXT NOT NULL,
    data_mode TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    category TEXT NOT NULL,
    report_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    PRIMARY KEY (draft_id, report_id),
    FOREIGN KEY (draft_id, data_mode, zone_id, category)
        REFERENCES complaint_draft (id, data_mode, zone_id, category),
    FOREIGN KEY (report_id, data_mode, zone_id)
        REFERENCES report (id, data_mode, zone_id),
    FOREIGN KEY (report_id, attempt, category)
        REFERENCES detection (report_id, attempt, category)
);

CREATE INDEX report_active_zone ON report (data_mode, zone_id, observed_at);
CREATE INDEX evidence_report ON complaint_evidence (report_id);

CREATE TABLE report_photo (
    report_id TEXT PRIMARY KEY REFERENCES report (id) ON DELETE CASCADE,
    png BLOB NOT NULL
);
