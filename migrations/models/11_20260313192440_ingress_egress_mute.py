from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE dashboard_button ADD COLUMN mute_notifications_enabled INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE dashboard_button ADD COLUMN mute_duration_seconds INTEGER NOT NULL DEFAULT 180;
        CREATE TABLE IF NOT EXISTS "dashboard_button_mute_tag" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "dashboard_button_id" INT NOT NULL REFERENCES "dashboard_button" ("id") ON DELETE CASCADE,
            "tag_id" INT NOT NULL REFERENCES "tag" ("id") ON DELETE CASCADE,
            UNIQUE ("dashboard_button_id", "tag_id")
        );
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "dashboard_button_mute_tag";
        """


MODELS_STATE = (
    "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"
    "XIEcBTG5wE2IhJe4iZe4ybHhFr+xvP4f6m3xKA=="
)
