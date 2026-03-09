from tortoise import BaseDBAsyncClient


RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "device" ADD "zone_masks_enabled" INT NOT NULL DEFAULT 0;
        ALTER TABLE "device" ADD "zone_mask_away" TEXT;
        ALTER TABLE "device" ADD "zone_mask_home" TEXT;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "device" DROP COLUMN "zone_masks_enabled";
        ALTER TABLE "device" DROP COLUMN "zone_mask_away";
        ALTER TABLE "device" DROP COLUMN "zone_mask_home";
    """


MODELS_STATE = (
    "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"
    "+Obc+kg/MXdfMwNpbH/wOqU9bG"
)
