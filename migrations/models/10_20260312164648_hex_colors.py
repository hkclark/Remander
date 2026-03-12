from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- Step 1: Recreate dashboard_button with VARCHAR(7) color column
        CREATE TABLE "dashboard_button_new" (
            "id"            INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "name"          VARCHAR(255)  NOT NULL,
            "color"         VARCHAR(7)    NOT NULL DEFAULT '#3B82F6',
            "delay_seconds" INT           NOT NULL DEFAULT 0,
            "operation_type" VARCHAR(5)   NOT NULL,
            "sort_order"    INT           NOT NULL DEFAULT 0,
            "is_enabled"    INT           NOT NULL DEFAULT 1,
            "show_on_main"  INT           NOT NULL DEFAULT 1,
            "show_on_guest" INT           NOT NULL DEFAULT 0,
            "created_at"    TIMESTAMP     NOT NULL,
            "updated_at"    TIMESTAMP     NOT NULL
        );

        -- Step 2: Copy rows, converting old name-based colors to hex
        INSERT INTO "dashboard_button_new"
            SELECT
                id, name,
                CASE color
                    WHEN 'blue'    THEN '#3B82F6'
                    WHEN 'sky'     THEN '#0EA5E9'
                    WHEN 'cyan'    THEN '#06B6D4'
                    WHEN 'teal'    THEN '#14B8A6'
                    WHEN 'emerald' THEN '#10B981'
                    WHEN 'green'   THEN '#22C55E'
                    WHEN 'lime'    THEN '#84CC16'
                    WHEN 'yellow'  THEN '#EAB308'
                    WHEN 'amber'   THEN '#F59E0B'
                    WHEN 'orange'  THEN '#F97316'
                    WHEN 'rose'    THEN '#F43F5E'
                    WHEN 'red'     THEN '#EF4444'
                    WHEN 'pink'    THEN '#EC4899'
                    WHEN 'fuchsia' THEN '#D946EF'
                    WHEN 'purple'  THEN '#A855F7'
                    WHEN 'violet'  THEN '#8B5CF6'
                    WHEN 'indigo'  THEN '#6366F1'
                    WHEN 'slate'   THEN '#64748B'
                    WHEN 'gray'    THEN '#6B7280'
                    WHEN 'zinc'    THEN '#71717A'
                    WHEN 'stone'   THEN '#78716C'
                    WHEN 'neutral' THEN '#737373'
                    WHEN 'cobalt'  THEN '#1E3A8A'
                    WHEN 'navy'    THEN '#1E3A8A'
                    WHEN 'plum'    THEN '#4C1D95'
                    WHEN 'grape'   THEN '#7C3AED'
                    WHEN 'crimson' THEN '#7F1D1D'
                    WHEN 'forest'  THEN '#14532D'
                    WHEN 'jade'    THEN '#059669'
                    WHEN 'russet'  THEN '#92400E'
                    ELSE COALESCE(color, '#3B82F6')
                END,
                delay_seconds, operation_type, sort_order,
                is_enabled, show_on_main, show_on_guest, created_at, updated_at
            FROM "dashboard_button";

        DROP TABLE "dashboard_button";
        ALTER TABLE "dashboard_button_new" RENAME TO "dashboard_button";

        -- Step 3: Migrate tag colors from names to hex (tags that already have hex are left alone)
        UPDATE "tag" SET color = CASE color
            WHEN 'blue'    THEN '#3B82F6'
            WHEN 'sky'     THEN '#0EA5E9'
            WHEN 'cyan'    THEN '#06B6D4'
            WHEN 'teal'    THEN '#14B8A6'
            WHEN 'emerald' THEN '#10B981'
            WHEN 'green'   THEN '#22C55E'
            WHEN 'lime'    THEN '#84CC16'
            WHEN 'yellow'  THEN '#EAB308'
            WHEN 'amber'   THEN '#F59E0B'
            WHEN 'orange'  THEN '#F97316'
            WHEN 'rose'    THEN '#F43F5E'
            WHEN 'red'     THEN '#EF4444'
            WHEN 'pink'    THEN '#EC4899'
            WHEN 'fuchsia' THEN '#D946EF'
            WHEN 'purple'  THEN '#A855F7'
            WHEN 'violet'  THEN '#8B5CF6'
            WHEN 'indigo'  THEN '#6366F1'
            WHEN 'slate'   THEN '#64748B'
            WHEN 'gray'    THEN '#6B7280'
            WHEN 'zinc'    THEN '#71717A'
            WHEN 'stone'   THEN '#78716C'
            WHEN 'neutral' THEN '#737373'
            WHEN 'cobalt'  THEN '#1E3A8A'
            WHEN 'navy'    THEN '#1E3A8A'
            WHEN 'plum'    THEN '#4C1D95'
            WHEN 'grape'   THEN '#7C3AED'
            WHEN 'crimson' THEN '#7F1D1D'
            WHEN 'forest'  THEN '#14532D'
            WHEN 'jade'    THEN '#059669'
            WHEN 'russet'  THEN '#92400E'
            ELSE color
        END
        WHERE color IS NOT NULL;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- Recreate dashboard_button with the old VARCHAR(10) color column
        CREATE TABLE "dashboard_button_old" (
            "id"            INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "name"          VARCHAR(255)  NOT NULL,
            "color"         VARCHAR(10)   NOT NULL DEFAULT 'blue',
            "delay_seconds" INT           NOT NULL DEFAULT 0,
            "operation_type" VARCHAR(5)   NOT NULL,
            "sort_order"    INT           NOT NULL DEFAULT 0,
            "is_enabled"    INT           NOT NULL DEFAULT 1,
            "show_on_main"  INT           NOT NULL DEFAULT 1,
            "show_on_guest" INT           NOT NULL DEFAULT 0,
            "created_at"    TIMESTAMP     NOT NULL,
            "updated_at"    TIMESTAMP     NOT NULL
        );

        INSERT INTO "dashboard_button_old"
            SELECT id, name, 'blue', delay_seconds, operation_type,
                   sort_order, is_enabled, show_on_main, show_on_guest,
                   created_at, updated_at
            FROM "dashboard_button";

        DROP TABLE "dashboard_button";
        ALTER TABLE "dashboard_button_old" RENAME TO "dashboard_button";
        """


MODELS_STATE = (
    "eJztXW1zm7gW/iuM75fuTJppvE2a9TfikK03jp1rO9vtrncYYss2NyAoL8m63fz3K/GOEB"
    "hsiMHWl04j6cjw6OjovOnwo6Vqc6CYp/zMkp9la93Xlq0O96MFJRWg/9C6T7iWpOthJ26w"
    "pEfFGS95A0XFG/loWgZqRH0LSTEBapoDc2bIuiVrELVCW1FwozZDA2W4DJtsKH+zgWhpS2"
    "CtgIE6/vobNctwDv4Bpv+n/iQuZKDMY08tz/FvO+2itdadth60bpyB+NcexZmm2CoMB+tr"
    "a6XBYLQMLdy6BBAYkgXw9JZh48fHT+e9rf9G7pOGQ9xHjNDMwUKyFSvyujkxmGkQ44eexn"
    "RecIl/5X377OOnj5c/X3y8REOcJwlaPr26rxe+u0voIDCYtF6dfsmS3BEOjCFupgV00fkj"
    "AV93JRl0/GJEBIzo4UkYfdCycPQbQiBD5ikJSVX6R1QAXFor9OfZhw8ZuP3Oj7qf+dE7NO"
    "on/DYaYmiX2wdeV9vtw+BGwZQs26QjKUBbddDsoaeS4AxQUPWp9wxpazzhRxPhusOhRzLQ"
    "D07h+KHbFYRrp82ezQCY49YbvtfHTQtJVpxRt737e2fMk6zrwGWcggvzS45l+SV1UX4hl2"
    "QOLPRwySWZgH9ShENIsdUyePv/DRk7A7CJ8McEP7Nqmt+UKFLv7vg/HBDVtdfTHw5+9YdH"
    "kO32h1ckpDZ6ffSMokph9VSZS1BtFr61wLYc8RtiNzMAfj1RspLQXaMeS1YBHb84JQHf3C"
    "M99f9TUxGM3mE+hMraW8sszu3dCUgM3d3H2Peanwi4px1jXb/13QUhF4JJuC+9yWcO/8n9"
    "ORwIDoKaaS0N5xfDcZM/W/iZJNvSRKi9iNI8cqT7rT4w8YXVVFWCc7GQHhIn2mpL7GMVS9"
    "4Tc/Asz0Ax5GI0RyRLsP67eKJqch4zJUG80QwgL+EtWCf0DwI5T/XvhjPVj/tefVbwW8O1"
    "NKSXwDIg9hZ6SfRqwHLVMX7c5a+FFoULS0DvOpiodhyYF7vY7opBNxYm3OCh3285nPgozZ"
    "5eJGMuxlgS92htjWgJxia71LZKtkhQWjoQ4BfBj+1bpbre1eBCppusQedJpsGq6xgCf9wm"
    "c7U1thALmBwiU+SZo8NwiLE4XbGXMuRMYFkIc/OE056BoUhr9Ad3CuAz562aeUqqwbvPOI"
    "VTzJEcBsDUpRka0ZnC91wXzRvQd9CEaJE5B1pnKPcOnC5PuWkLPhviCh2AU/Ro05apWrqo"
    "awb68yc8y338OTpoiPtopz/wLK+nP5wpX6etYEKvf6VZ4gvieOPU1KC2WIiyjuZsnexk2j"
    "+BdRHj1Btejg1VuXkfs33auYzSdoZR2vaN0nSL/1lSbIqc+208HNABDQhIpVOeWdy/nCKb"
    "NVVUMrDEb5ttGJE2EKEy4glIw8jW51sq93FKptzvVbl3Hj6haO3tvBtbknP20o47t2/jaW"
    "cGw/bimz0eAV6iV7GwAE8HNE2AN8RVe54L1PMMUM+Trlomq5msLllW+2YzRVRHLOp0SR0x"
    "4FkMrW6OlyyB7LsaHBSocnlz8IecY+8hIGEi8l/4r+Jg+KWDTUFRepHWeNdNYdB3LfT5r0"
    "68x+9HTC2tnVAQGvN5eCeE9CtNBS79Pf8wxh2T3k2vy096w8EY2aqSbeJ+S154NrHpjxwJ"
    "3eHoujf41R9lgJlmzNGSTyF/f9//Kl71Jnf8+LbjmNRr8VG2VMl82ib8dJYn/nSWHoA6S0"
    "SgmhcUbOkAYnRbSba4FwbeQrhDpvC/D8IDZgE0vY0XfvQwGDgjDBtCZ0S+2GGXH3SFvtM0"
    "w0gobuvw7r4vTIRrER8cojAaDUeIWdBu0bFLai6+yNZKBIahGeY2y90+y2Nwn6Xb22fJgC"
    "PaAaIqQ9sCheJjJN0RebWT+Jloh8N5cfwidEeKnyshi/Nfgu5I8bOkJRqpWMAoYmLFqRqS"
    "OPAGZpYMZUt2zKXHtSjrRSClkDYS14/nOWD9eJ6KKu7KABXt2kKcSiVuJLDt8zzIolHpp/"
    "d5AltT+ib+T3ukRqMzEuJiVAxNH01HMRNNG9k2BsUHmJ6ElSBsCKZvnYvF8okOwo2VzCdy"
    "zakt1jVGWMKy1msP1WgV/dfOXEYvgXaLdYxTsoXc80KGHoctRC1ByxZzz4s5l8zVo4Yd/o"
    "+2ZaGlKJZ7SKc+Ins5IwuRBCeJa/GEOn/Kq2DG2qGaO7OOzjuFc+xCwKPXryj+niuP/OZ2"
    "BBTHrZ4ONHHlq376XhrKhAX3jCStk/KwIx5jPJObzhkkWjQIlCpjneSepMQ8Kds2PfZJEx"
    "ssCFo3uX+SEQQteoew2dcHK/GWIHC0Qr68gOANY4P/+fnqsn1zkYwNbolkFtf5OH5KRfET"
    "Pfy2r/DRVpB+2PemDtHTdODd0tsllyE5y76zGXC2QofDGQpTiLMSOhzORpjC4eSzMOpwmn"
    "NIbMG8eYRAughIOp81wxI1Y07z6KdybpzoKNlWNkUA8btQzu4rTVOABFPO7xghgd0joqwK"
    "vOBwL9sWvxoO+zEz/KpHupEf7q6E0Ts3pwENkl2rI4mquUJWNb6wi363IK4kKUOWiuzSBi"
    "bFm5QL2oD2DbEtqobvBVwWEjnQkAhL2T6IhS2asp3Is93Rq5P/dnN93IixfeBlt4qGrezq"
    "4SJ8NFfuzCM0cT03QR18XVGQNru9CEjze8DE6DKX7w77i+pys6Rl62/mKavWU1af6NM+jr"
    "GSTb+VZhvBVikEJIXyWEHE2auFsAsJjgmyuoc9a3Qgn2wR96SWZcEn0u5YTqSGRTRJ/MIN"
    "txmyqGArAbvPaLqrcLbmYkgR+DEwR8iOGfW6k33VtvEKB9F0yqCkUIb+GI5hcdOaHRxZ2u"
    "B+46ZvXN+miqipV6xql4AVMcW+o1Vd/k4Y8fgepIp+cQrvh19wlErXXraLUl3kAJ10/4SQ"
    "X6QAbtqP6ZinBVlJyoak9ZM3pXJdlMq4J0VC+mhQK/fl496AeN98OxKG/d7gtsMZQFNk+D"
    "SFE/5+iNZL0rUpHA8Hw5ubDudWBtuGj0tOFXAO0cK1rx2qxrJuJRJ49SI+A8OUaWZPOpBx"
    "qkaiWb4gWMiGijTJQhwZpWkkjJXUYpd1HIEwgJlSeiFFMY1RNRLN8u+bzlYShIBSRD29sH"
    "FIcURp8URKyotsINuSxn+bclKilCy8nwBW1yjycROmHhGDMw4nEnUIJavg2R2naqSYbOcr"
    "tZpRaTWhBkmIy6zvBVkzQsV4kyhlYn13q0rpiN8AJesjvZhJkvJIzyGMhFN5aysMCcojxt"
    "DUAS27NBO9gOZIcfuuQSBib/u26bn0CZiYTIHZEXlJiNOrbCQpG3KUv3WZjRAoLBG3g9in"
    "ZBBTIYYa9b5mOrIBAQOUCii7FFGFsGXZ5QeRhMyyyw90YRPZ0k7UVNzmG2MUyiNS5DOS3a"
    "LAJPE8xg9mUViliSU96gNwcgsjAevmQ+x65aF53Ea9/SGZJtplKsC0JQDiZfjxwaz1PKdy"
    "QTRHu24W3D8vBZ5rf8qJl7jSUGhYcZxyLgzFEpQpSN5JcD3R8L/VZihXnb+XcQBG0mcSr2"
    "Fg9kGMFk8Zc3HSDAdh/JWnTjSxOcDe64mdptbK0OzlKtLuJYZT06FRu0imkb7myL1NCsHU"
    "ZFyqvNyUnSsmhbdDVvbNruCIw0/i6LUxiciueFWd1Ovjvk06n0+772y+aJ2UsH5KKx++8Y"
    "yUPAkp6fkoyfzTGDNvCXNyln0DfjfEn8LpcKqGW6bwXhiN8d86MEz89+/C5163j9bkGaxk"
    "BBNalkHvju+jhYGyKin4mypdAf/eDOBP53Rv+V8F/Mmc2RMSetssXOm1mfbxoe99eFMO7p"
    "JjM30Y9BBOIQBJsiNCL+u645v7fmpkO5zk/lp6/a7n1cepQaK46XZe6EKj7uoSkPwTzXXX"
    "dBhJeVXYDVn9Dce4LyXVwkq4XDZaV0mVrjrLillUb1w0gyn9zVT6WRpCgF6JaQjMlGKK7D"
    "4U2f3oDVEdl6IvECpwup5Aqt6sUkLdtmqWCsAqJex4Tzfzxn6OT1HveG2/RK1pPOEnvW6H"
    "w4FMeTaF118H/B1umK/Ry8qzGug97qOJz5JiF+Jakq4h2a0E++Zx+bfTff7thNPftKEhm0"
    "DUFgv8Mfni3zdOn+CIXHoEohiIXQCl0x8pngtZUYpv9zhVIzf7WZ7L++lX9xO3zVmG9SEk"
    "4rIM6wNd2O3rd1MKG7P61ckcvRpkdtYnvlFpZe97xV7KEMkeqUVxK0R6T7K8CrozTpz7Az"
    "c5FVq3YP3eOfKR/aIZgFtoBudOwuFJTjjpWZPnCC3sBX7v9ajy0v2oknlKWjelTEiNd3iv"
    "5lvSODOPRToqdnMQmOdVJAmyqiz0Sr0elRSCwkxbAEdvOPssYQBgik3z23g4oEOYZs7M5Z"
    "nF/cspslnTYEMGdvhtY+pY4ooueRuX0LPwBOQVXWbqHIRGzEydA13YoqZOlbpq4r4NRWOl"
    "3clJ11vdu0B+Td5gPIuJNUhZZGkxDU2LcTdfdi5oRpCISt1M7/HFZR6d/+IyXefHfTR0M5"
    "JDN0EbI20krh8vcxlTeFj61ZtLSl1d03HS2Oo2CV1RSlbGixkDB6gzJo0B77OVxZL14kTH"
    "lK3H0hzLT3Ochd883THPMf/XU2sUXjkhEh3jm2vzlR2WJdqELFFce4BiFHslCdLtYK+SAD"
    "N86ybQTjIM32NKBq0kLGKukBKDt68fQi+ozVPpmU5P6PSaohlF2DQgaKTNWc73cFhuSa0y"
    "KEg1qIxqR9vrQXUreBS+CVnzKCgMFS94FFOfyJpHYTWk3QoeuUZoprb0YDqKSkJdctoz9S"
    "XbH8EUpgYpTECVZMonnNKPooCgiSpTNV8alU1dkdaFU3NIukae7ZUgqkum+aIh+bdCh20R"
    "SBOEDNPg3NGeQKGPOQUEpWB4APtcNkWnBO8WXxkL6diF9QSmc1WmMOZGSH0yZlyygNFRBI"
    "xY9thBLOz2F2WkGTKzzRLKv2Njjncmy1cA/oDcFhuN3xCXFCs4Bly2OSyGK8Ys46ZZxlgU"
    "mpak6kWlbYyQCduanaLsA+CZeV9FPgCuIlmkUaRLOowhRUMv0pT+dWBdsgp6OKzmOjbOc0"
    "UszzMilufJiKVz0BY65CIULBEo5rvfMY/FDxLUD7+8WSwR1qhTDktQg5aik0br06aro7HM"
    "ZaaI1m1vZimix5TTUonj1gn9Fy7BE6dqpr5SVbY/8zEeqHXEfIwHsbA7+BhZlZk3cjbywJ"
    "BnK5pG5/Vk6nNSOIYpcw1S5p6BYXr7Jq8iEiFpphZSiVKHt0YBEL3hzQSwkkxv9IuWJ5Dj"
    "IKZXcImQsBouyRouBQ7c8g+W1/8DdKe+PA=="
)
