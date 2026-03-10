from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "plugin_data" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "plugin_name" VARCHAR(100) NOT NULL,
            "key" VARCHAR(255) NOT NULL,
            "value" JSON NOT NULL,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE ("plugin_name", "key")
        );
        CREATE INDEX IF NOT EXISTS "idx_plugin_data_plugin_name" ON "plugin_data" ("plugin_name");
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "plugin_data";
        """


MODELS_STATE = (
    "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"
    "g/KtAkfw=="
)
