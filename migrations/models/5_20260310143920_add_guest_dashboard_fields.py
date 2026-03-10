from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "dashboard_button" ADD COLUMN "show_on_main" INT NOT NULL DEFAULT 1;
        ALTER TABLE "dashboard_button" ADD COLUMN "show_on_guest" INT NOT NULL DEFAULT 0;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "dashboard_button" DROP COLUMN "show_on_main";
        ALTER TABLE "dashboard_button" DROP COLUMN "show_on_guest";
        """


MODELS_STATE = (
    "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"
    "hRV/sPz6P3yOtyw="
)
