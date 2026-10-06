-- TET-0 DDL DRAFT v3 (2026-10-06; v3 = review round 1, comments only for R-1/R-6; v2 = owner decisions applied) — PostgreSQL 16. Not a migration yet: unit `db` turns it into Flyway V1__init.sql.
-- [unverified]: never run on a real PG 16 yet — syntax/semantics are proven only when unit `db` applies it (Testcontainers).
-- Money: bigint VND. Ids: uuid (v7 generated in app, Q-D1 — owner decision 2026-10-06) for public entities, bigint identity for catalog/internal.
-- Data access: Spring Data JDBC + hand-written SQL on hot paths (Q-D2 = J1, owner decision 2026-10-06).
-- Every "never duplicate / exactly one" rule below is a PK / UNIQUE / CHECK / EXCLUDE — see data-model.md §4.

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS btree_gist;          -- only for order_item_no_overlap (Q-I2 = yes, owner decision 2026-10-06)

-- ───────────── identity ─────────────
CREATE TABLE account (
    id             uuid PRIMARY KEY,
    email          citext NOT NULL UNIQUE,
    password_hash  text   NOT NULL,                  -- argon2id
    full_name      varchar(100) NOT NULL,
    role           varchar(16) NOT NULL DEFAULT 'PASSENGER' CHECK (role IN ('PASSENGER','STAFF','ADMIN')),
    status         varchar(16) NOT NULL DEFAULT 'ACTIVE'    CHECK (status IN ('ACTIVE','LOCKED')),
    email_verified boolean NOT NULL DEFAULT false,      -- must be true to join a waiting room (R-6, 403 EMAIL_NOT_VERIFIED)
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- ───────────── catalog (admin) ─────────────
CREATE TABLE station (
    id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code  varchar(8)   NOT NULL UNIQUE,
    name  varchar(100) NOT NULL
);

CREATE TABLE route (
    id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code  varchar(16)  NOT NULL UNIQUE,              -- e.g. SE1
    name  varchar(100) NOT NULL
);

CREATE TABLE route_station (
    route_id        bigint   NOT NULL REFERENCES route(id),
    idx             smallint NOT NULL CHECK (idx BETWEEN 0 AND 63),   -- bit position limit of occupied_mask
    station_id      bigint   NOT NULL REFERENCES station(id),
    arr_offset_min  integer  NOT NULL CHECK (arr_offset_min >= 0),    -- minutes after trip.departs_at
    dep_offset_min  integer  NOT NULL CHECK (dep_offset_min >= arr_offset_min),
    PRIMARY KEY (route_id, idx),
    UNIQUE (route_id, station_id)
);

CREATE TABLE train (
    id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code  varchar(16) NOT NULL UNIQUE
);

CREATE TABLE seat (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    train_id    bigint      NOT NULL REFERENCES train(id),
    coach_no    smallint    NOT NULL CHECK (coach_no > 0),
    seat_no     smallint    NOT NULL CHECK (seat_no > 0),
    seat_class  varchar(16) NOT NULL CHECK (seat_class IN ('SOFT_SEAT','HARD_SEAT','BERTH_4','BERTH_6')),
    UNIQUE (train_id, coach_no, seat_no)
);

CREATE TABLE segment_fare (                           -- price of one segment idx→idx+1 per class; ticket = Σ
    route_id    bigint      NOT NULL,
    idx         smallint    NOT NULL,
    seat_class  varchar(16) NOT NULL,
    amount      bigint      NOT NULL CHECK (amount > 0),
    PRIMARY KEY (route_id, idx, seat_class),
    FOREIGN KEY (route_id, idx) REFERENCES route_station(route_id, idx)
);

CREATE TABLE sale_wave (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name               varchar(100) NOT NULL,
    opens_at           timestamptz NOT NULL,
    closes_at          timestamptz NOT NULL CHECK (closes_at > opens_at),
    trip_date_from     date        NOT NULL,                                -- F-10: trips departing in
    trip_date_to       date        NOT NULL CHECK (trip_date_to >= trip_date_from),   -- [from, to] join the wave on publish
    status             varchar(16) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','PUBLISHED','CLOSED')),
    max_per_account    smallint NOT NULL DEFAULT 10 CHECK (max_per_account BETWEEN 1 AND 50),
    max_per_cccd       smallint NOT NULL DEFAULT 4  CHECK (max_per_cccd BETWEEN 1 AND 10),
    queue_enabled      boolean  NOT NULL DEFAULT true,
    admit_rate_per_s   integer  NOT NULL DEFAULT 100   CHECK (admit_rate_per_s >= 0),   -- waiting-room.md §3
    active_cap         integer  NOT NULL DEFAULT 50000 CHECK (active_cap >= 0)
);

CREATE TABLE trip (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    route_id        bigint NOT NULL REFERENCES route(id),
    train_id        bigint NOT NULL REFERENCES train(id),
    sale_wave_id    bigint REFERENCES sale_wave(id),                       -- set by wave publish, same tx as seat_inventory (F-10)
    departure_date  date   NOT NULL,
    departs_at      timestamptz NOT NULL,                                  -- at route idx 0
    status          varchar(16) NOT NULL DEFAULT 'SCHEDULED' CHECK (status IN ('SCHEDULED','CANCELLED')),
    cancelled_at    timestamptz,                                           -- F-1: when cancelled; trip-cancel job is condition-bound (R-1), not time-bound
    UNIQUE (train_id, departure_date),
    CHECK ((status = 'CANCELLED') = (cancelled_at IS NOT NULL))
);
CREATE INDEX trip_route_date ON trip (route_id, departure_date);

-- ───────────── inventory (seat-inventory.md) ─────────────
CREATE TABLE seat_inventory (                         -- created for every trip × seat when the wave is published;
                                                      -- kept after the wave: order_item FK needs it (F-9)
    trip_id        bigint  NOT NULL REFERENCES trip(id),
    seat_id        integer NOT NULL REFERENCES seat(id),
    occupied_mask  bigint  NOT NULL DEFAULT 0,       -- bit i = segment idx i..i+1 held or sold
    PRIMARY KEY (trip_id, seat_id)
);

CREATE TABLE quota_usage (                            -- AC-4
    sale_wave_id  bigint      NOT NULL REFERENCES sale_wave(id),
    kind          varchar(8)  NOT NULL CHECK (kind IN ('ACCOUNT','CCCD')),
    subject       bytea       NOT NULL,              -- account uuid bytes | HMAC-SHA256(pepper, cccd)
    used          integer     NOT NULL CHECK (used >= 0),
    PRIMARY KEY (sale_wave_id, kind, subject)
);

-- ───────────── booking ─────────────
CREATE TABLE booking_order (
    id            uuid PRIMARY KEY,
    account_id    uuid   NOT NULL REFERENCES account(id),
    sale_wave_id  bigint NOT NULL REFERENCES sale_wave(id),
    trip_id       bigint NOT NULL REFERENCES trip(id),
    from_idx      smallint NOT NULL,
    to_idx        smallint NOT NULL,
    status        varchar(20) NOT NULL CHECK (status IN ('PENDING_PAYMENT','PAID','EXPIRED','CANCELLED')),
    total_amount  bigint NOT NULL CHECK (total_amount > 0),
    expires_at    timestamptz NOT NULL,
    paid_at       timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    CHECK (from_idx < to_idx),
    CHECK ((status = 'PAID') = (paid_at IS NOT NULL))
);
CREATE INDEX booking_order_account ON booking_order (account_id, created_at DESC);
CREATE INDEX booking_order_expiry  ON booking_order (expires_at) WHERE status = 'PENDING_PAYMENT';   -- sweeper

CREATE TABLE order_item (
    id              uuid PRIMARY KEY,
    order_id        uuid    NOT NULL REFERENCES booking_order(id),
    trip_id         bigint  NOT NULL,
    seat_id         integer NOT NULL,
    from_idx        smallint NOT NULL,
    to_idx          smallint NOT NULL,
    seg_mask        bigint  NOT NULL CHECK (seg_mask <> 0),
    price           bigint  NOT NULL CHECK (price > 0),
    passenger_name  varchar(100) NOT NULL,
    cccd_hmac       bytea   NOT NULL,                -- quota key + lookup
    cccd_enc        bytea   NOT NULL,                -- AES-256-GCM(nonce || ciphertext || tag), key from secret
    cccd_last4      char(4) NOT NULL,
    status          varchar(10) NOT NULL CHECK (status IN ('ACTIVE','RELEASED','REFUNDED')),
    FOREIGN KEY (trip_id, seat_id) REFERENCES seat_inventory(trip_id, seat_id),
    CHECK (from_idx < to_idx),
    UNIQUE (order_id, seat_id),
    UNIQUE (order_id, cccd_hmac),                    -- one passenger per seat in an order
    CONSTRAINT order_item_no_overlap EXCLUDE USING gist (   -- AC-1 safety net (Q-I2 = yes, owner decision 2026-10-06)
        trip_id WITH =, seat_id WITH =, int4range(from_idx, to_idx) WITH &&
    ) WHERE (status = 'ACTIVE')
);
CREATE INDEX order_item_order ON order_item (order_id);

-- ───────────── payment ─────────────
CREATE TABLE payment_attempt (
    id               uuid PRIMARY KEY,
    order_id         uuid   NOT NULL REFERENCES booking_order(id),
    provider         varchar(16) NOT NULL DEFAULT 'VNPAY',
    txn_ref          varchar(32) NOT NULL,
    amount           bigint NOT NULL CHECK (amount > 0),
    status           varchar(20) NOT NULL CHECK (status IN ('PENDING','SUCCEEDED','FAILED','EXPIRED','REFUNDED','PARTIALLY_REFUNDED')),  -- FAILED|EXPIRED -> SUCCEEDED allowed (F-6)
    provider_txn_no  varchar(64),
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, txn_ref)
);
CREATE UNIQUE INDEX payment_attempt_one_pending ON payment_attempt (order_id) WHERE status = 'PENDING';
CREATE INDEX payment_attempt_pending_age ON payment_attempt (created_at) WHERE status = 'PENDING';   -- R1

CREATE TABLE payment_event (                          -- IPN / query results, dedup (THR-05)
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider            varchar(16) NOT NULL,
    event_key           varchar(128) NOT NULL,       -- txn_ref || ':' || provider_txn_no || ':' || response_code (F-8)
    payment_attempt_id  uuid REFERENCES payment_attempt(id),
    source              varchar(8) NOT NULL CHECK (source IN ('IPN','QUERY')),
    payload             jsonb NOT NULL,
    received_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, event_key)
);

CREATE TABLE refund (
    id                  uuid PRIMARY KEY,
    payment_attempt_id  uuid   NOT NULL REFERENCES payment_attempt(id),
    ticket_id           uuid,                        -- null = whole attempt (late/double payment); FK added after ticket (F-11)
    amount              bigint NOT NULL CHECK (amount > 0),
    reason              varchar(32) NOT NULL CHECK (reason IN ('PASSENGER_REQUEST','TRIP_CANCELLED','LATE_PAYMENT_UNFULFILLED','DOUBLE_PAYMENT')),
    status              varchar(12) NOT NULL CHECK (status IN ('REQUESTED','SUCCEEDED','FAILED')),
    attempts            smallint NOT NULL DEFAULT 0,
    provider_refund_no  varchar(64),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX refund_once_per_ticket  ON refund (ticket_id) WHERE ticket_id IS NOT NULL;
CREATE UNIQUE INDEX refund_once_per_attempt ON refund (payment_attempt_id) WHERE ticket_id IS NULL;

CREATE TABLE reconciliation_issue (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind                varchar(24) NOT NULL CHECK (kind IN ('MISSING_LOCAL','MISSING_GATEWAY','AMOUNT_MISMATCH','REFUND_FAILED','INVARIANT_BROKEN')),
    payment_attempt_id  uuid REFERENCES payment_attempt(id),
    detail              jsonb NOT NULL,
    status              varchar(10) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','RESOLVED')),
    resolved_by         uuid REFERENCES account(id),
    created_at          timestamptz NOT NULL DEFAULT now()
);

-- ───────────── ticketing ─────────────
CREATE TABLE ticket (
    id             uuid PRIMARY KEY,
    order_item_id  uuid NOT NULL UNIQUE REFERENCES order_item(id),   -- idempotent issuing
    account_id     uuid NOT NULL REFERENCES account(id),             -- ownership filter (THR-06)
    code           varchar(12) NOT NULL UNIQUE,                       -- human code printed on ticket
    qr             text NOT NULL,                                     -- base64url(payload).base64url(ed25519 sig)
    status         varchar(10) NOT NULL DEFAULT 'VALID' CHECK (status IN ('VALID','REFUNDED','USED')),
    issued_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ticket_account ON ticket (account_id, issued_at DESC);

ALTER TABLE refund ADD CONSTRAINT refund_ticket_fk FOREIGN KEY (ticket_id) REFERENCES ticket(id);   -- F-11

-- ───────────── plumbing ─────────────
CREATE TABLE idempotency_record (
    account_id       uuid NOT NULL,
    idem_key         varchar(64) NOT NULL,
    request_hash     bytea NOT NULL,                 -- sha256(method || path || body)
    response_status  smallint,
    response_body    jsonb,
    created_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, idem_key)
);

CREATE TABLE outbox_event (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    aggregate_id    uuid NOT NULL,
    event_type      varchar(32) NOT NULL,
    payload         jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    published_at    timestamptz
);
CREATE INDEX outbox_unpublished ON outbox_event (id) WHERE published_at IS NULL;

CREATE TABLE notification_sent (
    event_id  bigint PRIMARY KEY,                    -- outbox_event.id
    sent_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (                              -- staff/admin actions (THR-09 repudiation)
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id    uuid NOT NULL REFERENCES account(id),
    action      varchar(48) NOT NULL,
    target      varchar(100) NOT NULL,
    detail      jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);
