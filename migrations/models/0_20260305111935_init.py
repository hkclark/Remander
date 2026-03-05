from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "app_state" (
    "key" VARCHAR(100) NOT NULL PRIMARY KEY,
    "value" VARCHAR(500) NOT NULL,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "command" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "command_type" VARCHAR(19) NOT NULL /* SET_AWAY_NOW: set_away_now\nSET_AWAY_DELAYED: set_away_delayed\nSET_HOME_NOW: set_home_now\nPAUSE_NOTIFICATIONS: pause_notifications\nPAUSE_RECORDING: pause_recording */,
    "status" VARCHAR(21) NOT NULL DEFAULT 'pending' /* PENDING: pending\nQUEUED: queued\nRUNNING: running\nSUCCEEDED: succeeded\nFAILED: failed\nCANCELLED: cancelled\nCOMPLETED_WITH_ERRORS: completed_with_errors */,
    "delay_minutes" INT,
    "pause_minutes" INT,
    "tag_filter" VARCHAR(500),
    "initiated_by_ip" VARCHAR(45),
    "initiated_by_user" VARCHAR(255),
    "saq_job_id" VARCHAR(255),
    "error_summary" TEXT,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "queued_at" TIMESTAMP,
    "started_at" TIMESTAMP,
    "completed_at" TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "device" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "device_type" VARCHAR(6) NOT NULL /* CAMERA: camera\nPOWER: power */,
    "device_subtype" VARCHAR(50),
    "brand" VARCHAR(7) NOT NULL /* REOLINK: reolink\nTAPO: tapo\nSONOFF: sonoff */,
    "model" VARCHAR(255),
    "hw_version" VARCHAR(50),
    "firmware" VARCHAR(100),
    "ip_address" VARCHAR(45),
    "channel" INT,
    "is_wireless" INT NOT NULL DEFAULT 0,
    "is_poe" INT NOT NULL DEFAULT 0,
    "resolution" VARCHAR(20),
    "has_ptz" INT NOT NULL DEFAULT 0,
    "ptz_away_preset" INT,
    "ptz_home_preset" INT,
    "ptz_speed" INT,
    "notes" TEXT,
    "is_enabled" INT NOT NULL DEFAULT 1,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "power_device_id" INT REFERENCES "device" ("id") ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS "activity_log" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "step_name" VARCHAR(100) NOT NULL,
    "status" VARCHAR(9) NOT NULL /* STARTED: started\nSUCCEEDED: succeeded\nFAILED: failed\nSKIPPED: skipped */,
    "detail" TEXT,
    "duration_ms" INT,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "command_id" INT NOT NULL REFERENCES "command" ("id") ON DELETE CASCADE,
    "device_id" INT REFERENCES "device" ("id") ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS "device_detection_type" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "detection_type" VARCHAR(7) NOT NULL /* MOTION: motion\nPERSON: person\nVEHICLE: vehicle\nANIMAL: animal\nFACE: face\nPACKAGE: package */,
    "is_enabled" INT NOT NULL DEFAULT 1,
    "device_id" INT NOT NULL REFERENCES "device" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_device_dete_device__1a863c" UNIQUE ("device_id", "detection_type")
);
CREATE TABLE IF NOT EXISTS "hour_bitmask" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "subtype" VARCHAR(7) NOT NULL /* STATIC: static\nDYNAMIC: dynamic */,
    "static_value" VARCHAR(24),
    "sunrise_offset_minutes" INT,
    "sunset_offset_minutes" INT,
    "fill_value" VARCHAR(1),
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "saved_device_state" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "detection_type" VARCHAR(7) NOT NULL /* MOTION: motion\nPERSON: person\nVEHICLE: vehicle\nANIMAL: animal\nFACE: face\nPACKAGE: package */,
    "saved_hour_bitmask" VARCHAR(24),
    "saved_zone_mask" VARCHAR(4800),
    "is_consumed" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "command_id" INT NOT NULL REFERENCES "command" ("id") ON DELETE CASCADE,
    "device_id" INT NOT NULL REFERENCES "device" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "tag" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "show_on_dashboard" INT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS "zone_mask" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "mask_value" VARCHAR(4800) NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "device_bitmask_assignment" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "mode" VARCHAR(4) NOT NULL /* HOME: home\nAWAY: away */,
    "detection_type" VARCHAR(7) NOT NULL /* MOTION: motion\nPERSON: person\nVEHICLE: vehicle\nANIMAL: animal\nFACE: face\nPACKAGE: package */,
    "device_id" INT NOT NULL REFERENCES "device" ("id") ON DELETE CASCADE,
    "hour_bitmask_id" INT REFERENCES "hour_bitmask" ("id") ON DELETE SET NULL,
    "zone_mask_id" INT REFERENCES "zone_mask" ("id") ON DELETE SET NULL,
    CONSTRAINT "uid_device_bitm_device__f34725" UNIQUE ("device_id", "mode", "detection_type")
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS "device_tag" (
    "tag_id" INT NOT NULL REFERENCES "tag" ("id") ON DELETE CASCADE,
    "device_id" INT NOT NULL REFERENCES "device" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_device_tag_tag_id_0bda0b" ON "device_tag" ("tag_id", "device_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
