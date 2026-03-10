from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE "dashboard_button" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "name" VARCHAR(255) NOT NULL,
            "color" VARCHAR(10) NOT NULL DEFAULT 'blue',
            "delay_seconds" INT NOT NULL DEFAULT 0,
            "hour_bitmask_id" INT REFERENCES "hour_bitmask" ("id") ON DELETE SET NULL,
            "operation_type" VARCHAR(10) NOT NULL,
            "sort_order" INT NOT NULL DEFAULT 0,
            "is_enabled" INT NOT NULL DEFAULT 1,
            "created_at" TIMESTAMP NOT NULL,
            "updated_at" TIMESTAMP NOT NULL
        );
        ALTER TABLE "command" ADD COLUMN "delay_seconds" INT;
        ALTER TABLE "command" ADD COLUMN "dashboard_button_id" INT REFERENCES "dashboard_button" ("id") ON DELETE SET NULL;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "dashboard_button";
        """


MODELS_STATE = (
    "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"
)
