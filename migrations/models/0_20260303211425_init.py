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
    "name" VARCHAR(100) NOT NULL UNIQUE
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
    "5NXAie2ZPuD8Rd08nI3l8f9jlguZ"
)
