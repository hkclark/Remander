from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE "user" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "email" VARCHAR(255) NOT NULL UNIQUE,
            "display_name" VARCHAR(255),
            "password_hash" VARCHAR(255),
            "token" VARCHAR(255) UNIQUE,
            "is_active" INT NOT NULL DEFAULT 1,
            "is_admin" INT NOT NULL DEFAULT 0,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE "user_access_log" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
            "timestamp" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "ip_address" VARCHAR(45),
            "method" VARCHAR(20) NOT NULL,
            "path" VARCHAR(500)
        );
        CREATE INDEX "idx_user_access_log_user_id" ON "user_access_log" ("user_id");
        CREATE INDEX "idx_user_token" ON "user" ("token");
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "user_access_log";
        DROP TABLE IF EXISTS "user";
        """


MODELS_STATE = (
    "eJztXW1z2rgW/isePnVn0swmt2m7fHOI07IhwAWy3eyy41FAAd/YsuuXZNlu/vuV/G5ZNj"
    "aYYIO+dIqko9iPjo7Om45/tDR9DlXrVJzZyrNir3r6otUWfrQQ0CD+D6v7RGgBw4g6SYMN"
    "HlR3PPAHyqo/8sGyTdyI+x6BakHcNIfWzFQMW9ERbkWOqpJGfYYHKmgRNTlI+e5A2dYX0F"
    "5CE3f8+RduVtAc/g2t4KfxJD8qUJ0nnlqZk7/ttsv2ynDbusi+dgeSv/Ygz3TV0VA02FjZ"
    "Sx2FoxVkk9YFRNAENiTT26ZDHp88nf+2wRt5TxoN8R4xRjOHj8BR7djrFsRgpiOCH34ay3"
    "3BBfkr78/PPnz68Pk/Hz98xkPcJwlbPr16rxe9u0foItCftF7dfmADb4QLY4SbZUNDdn+k"
    "4OssgcnGL0FEwYgfnoYxAC0Px6AhAjJinoqQ1MDfsgrRwl7in2c//5yD22/iqPNVHL3Do3"
    "4ib6Njhva4ve93nXt9BNw4mMB2LDaSEnI0F80ufiqAZpCBakC9Z0hb44k4mkhXbQE/kon/"
    "4BSN7zodSbpy25zZDMI5ab0Wuz3S9AgU1R110x0O3TFPimFAj3FKLswvBZbll8xF+YVekj"
    "m08cOll2QC/84QDhHFRsvg7/83ZOwcwCbS7xPyzJplfVfjSL27FX93QdRWfk9v0P8SDI8h"
    "2+kNLmlIHfz6+BlljcHqmTKXolovfGuBbTXiN8JuZkLyejKw09Bd4R5b0SAbvyQlBd/cJz"
    "0N/lNTEYzfYT5A6spfyzzO7d5KWAzdDhPseyVOJNJznmDdoPXdR0ouhJMI37qTrwL5Kfwx"
    "6EsugrplL0z3L0bjJn+0yDMBx9ZlpL/IYB470oPWAJjkwuqaBtBcLqWHJIk22hL7WMWK98"
    "QcPiszWA65BM0RyRKi/z4+MTU5n5nSIF7rJlQW6AauUvoHhZyv+neimerHfa8BKwSt0Vqa"
    "4CW0DKi9hV8Svxq0PXVMHHfEK6nF4MIK0LsKJ6odBxbFLrG7EtCNpYnQv+v1Wi4nPoDZ0w"
    "sw53KCJUmPfq5TLeHYdJd2rtEtAIGFCwF5EfLYgVVqGB0dPSpskzXsPMk1WA2DQBCMW2eu"
    "tsY2ZgFLwGSqMnN1GAEzlmCozkJBggVtG2NunQj6MzRVsMI/hFOIngV/1axTWg3efsYpmh"
    "KOFAgAlgFmeER7it4LHTxvSN/GE+JFFlxo3aHCO3i6OBWmLfRsykt8AE7xo01blmYbsqGb"
    "+OdPZJZh8jnaeIj3aKc/yCyvpz/cKV+nrXBCv3+p2/IL5njz1NKR/vgoKwaes3WylWn/BF"
    "dljFN/eDU21M7N+4Ttc17IKD3PMUrPA6M02+J/BqrDkHO/jgd9NqAhAa10KjNb+FdQFaum"
    "ikoOluRt8w0j2gaiVEYyAW0YOcZ8Q+U+ScmV+70q9+7DpxStvZ13Yxu4Zy/ruPP61p52Vj"
    "hsL77Z4xHgFXoVSwvwbECzBHhDXLUXhUC9yAH1Iu2q5bKay+qKZXVgNjNEdcyizpbUMQOe"
    "x9Dq5njJE8iBq8FFgSmX1wd/6Dn2HgKSJrL4TbyX+4NvbWIKyuAFrMium6Kw70rqifduvC"
    "fox0wNVm4oCI/5OriVIvqlrkGPfijejUnHpHvd7YiT7qA/xrYqcCzSbyuPvk1sBSNHUmcw"
    "uur2vwSjTDjTzTle8ikSh8PevXzZndyK45u2a1Kv5AfF1oD1tEn46axI/OksOwB1lopANS"
    "8o2DIgIui20mwxlPr+QnhDpui/d9IdYQE8vUMWfnTX77sjTAchd0Sx2GFH7Heknts0I0io"
    "XuvgdtiTJtKVTA4OWRqNBiPMLHi3GMQlNZdfFHspQ9PUTWuT5T4/K2Jwn2Xb22fpgCPeAb"
    "KmIMeGpeJjNN0RebXT+Fl4h6N5efxidEeKnychy/Nfiu5I8bPBAo9UbWiWMbGSVA1JHHgD"
    "M0tBiq245tLDSlaMMpAySBuJ64eLArB+uMhElXTlgIp3bSlOZRI3EtjziyLI4lHZp/dFCl"
    "sLfJf/pz8wo9E5CXEJKo5mgKarmMmWg20bk+EDzE7CShE2BNO3zsXi+UQH4cZK5xN55tQG"
    "65ogrGBZ67WHarSKwWvnLqOfQLvBOiYp+ULueSEjj8MGopai5Yu558WcA2v5oBOH/4Nj23"
    "gpyuUesqmPyF7OyUKkwUnjWj6hLpjyMpyxdqgWzqxj807pHLsI8Pj1K4a/59Inv74ZQdV1"
    "q2cDTV35qp++l4UyZcE9Y0nrpjxsiceYzOSlc4aJFg0CZZexTnpPMmKejG2bHftkiQ0eBK"
    "2b3D/JCYKWvUPY7OuDO/GWYHD0DF9ekQCyT/yGccIHP6+IChJe9u6ktkA6p6jbv+p+GbQF"
    "PI+y0KdoeDca9nCv4ZhYJ8a/u/0b/EtBT1M0Goxxj6lbuH1EAoEmCQEORmL/C27HIKIF7h"
    "FvL6VRWwDaAzSn6F7q9UiEeQVVlcSWe1g9bAsq1qKn6MtIkvptAWuOEE3RRBJ7eFdBoE5R"
    "517EHbMVQOTS4j25sLgi48V7MhysNgklfizAELTSG7HDR3YccV9xsI344ed9S6cIPd2A/n"
    "XDbZIy0rPsOy2DpF1g3n8BmF1JekVbIGkVeJNMvpJNobun3QbMW0SaZcuytBddN21ZN+es"
    "0EQm5yaJjpJtFUuGiLwLQwm51HUVApShiCQIKeweMOWuwAu1lKqdCpeDQS/hT7js0v7wO3"
    "ISvPOSM/AgxTOf0qhaS/1FJjeP8d8tiStNypFlIrtwoMVwixWCNqR9Q2zL2hN7AZfHdg40"
    "tsNzzw9iYcvmnqcShrd0TxW/pl0ff2hiH/hpurLpqNu66ihn06U38whPXM9NUAenXRyk9f"
    "47CtLirjw5vszV+/X+ZPoObbBo/cVdfrt1+dUnjLaPY6xi02+pO2a4VUoByaA8VhBJGm4p"
    "7CKCY4Ks7vHbGh3IJxsEcJn1ZciJtD2WE9Cw0CyNX7Th1kMWF2wVYPcVT3cZzdZcDBkCPw"
    "HmCNsxo25nsq8iPX4FJJZOGdZGytEfozE8AFyzgyNPG9xvAPiNC/XsIvzrV93aJmBFTbHv"
    "aFVHvJVGIrnQqeG/OEXDwTcSpTL0l82iVJWHWF20LOchG/OsICtN2ZD7CfSVr0I3vnIufN"
    "GQPpjMEoTFuDck3jffjqRBz81LMKGuuqkJE3E4wOsFDH2KxoP+4Pq6LXglzjbh4zxBG8D+"
    "KRP1TzTo7iFauoi3S9VY1t2JBF6+yM/QtBSW2ZMNZJKqkWhWLwgeFVPDmmQpjozTNBLGnR"
    "SVVwwSgTChlVFDIkMxTVA1Es3qL87OlgAhyKgGn12hOaI4ovx+KiXlRTGxbcniv3U5KXFK"
    "Ht5PAWvoDPm4DlOfiMOZhBOLOoySXfLsTlI1UkyeF6sZm1MyNqUGAcxl9j8lWTNGxXmTqs"
    "li/+OVxzIwv0FG1kd2VZY05ZGeQwQJt4TYRhhSlEeMoWVAVnZpLnohzZHi9o+OoEy87Zum"
    "57In4GIyA2ZX5KUhzi4XkqZsyFH+1vVCIqCIRNwM4oCSQ8yEGOnMi6fZyIYEHFAmoPxSxC"
    "6ELc8uP4gkZJ5dfqALm8qWdqOm8iYfS2NQHpEin5PsFgcmjecxfvmLwSpNrE1SH4DTWxgL"
    "WC8fYtsrD83jNubtD2BZeJdpkNBWAIif4SeGs9bznCoE0Rzvull4/7wSeK6CKSd+4kpDoe"
    "FVfqq5MJRIUGYgeQvQaqKTf3ebobzr/L2cAzCWPpN6DZOwD2a0ZMqYh5NuugiTz1W144nN"
    "IfZ+T+I0tZem7iyWsXY/MZyZDo3bZTqN9LVA7m1aCGYm4zLl5brsXDktvF2yqm92hUcceR"
    "JXr01IRH7Fa9dJvQHum6TzBbT7zuaL10mJ6qe0iuGbzEgpkpCSnY+Szj9NMPOGMKdn2Tfg"
    "twPyTZ+2oOmkZYqG0mhMfhvQtMjv36Sv3Q4pAvUMl8qMVIES+91bUp0JIEUj9ZmuxY5E/t"
    "6MVIgSOzciKQBlYLmKhd4mC1dxwuV+vli+D2/KwV1ybKYPgx3CKQUgTXZE6OVdd3xz30+N"
    "bIeTwp99r9/1vPo4NWgU193Oi1xozF1dAZJ/4Llumw4jLa9KuyF3f8Mx6UvJtLBSLpe11l"
    "VapdudZcUtqjcumsGV/mYq/TwNIUSvwjQEbkpxRXYfiux+9Ia4jsvQFygVOFtPoFVvXimh"
    "bls1TwXglRK2vKebe2O/wDe1t7y2X6HWNJ6Ik26nLZBApjKboqv7vnhLGuYr/LLKrAZ6j/"
    "do8jPwi/0X5VqariHZrRT7FnH5n2f7/M9TTn/LQaZiQVl/fLSgvcGHmrMnOCKXHoUoAWIb"
    "QNn0R4rno6Kq5bd7kqqRm/2syOX97Kv7qdvmPMP6EBJxeYb1gS7s5vW7GYWNef3qdI5eDT"
    "I76xPf2Gll76HqLBSEZQ9oMdwKsd6TPK+C4Y6T58HAdU6F1g1cvXePfGy/6CYUHnVT8CYR"
    "yCQnAnjWlTlGi3iB3/s9mrLwPqpkndLWTSUTMuMd/qsFljTJzOORjh27OSjMiyqSFNmuLP"
    "Sdej12UgiKMG0JHP3h/PuKIYAZNs2v40GfDWGWOTNXZrbwr6AqVk2DDTnYkbdNqGOpK7r0"
    "bVxKzyIT0Fd0ualzEBoxN3UOdGHLmjq71FVT920YGivrTk623urdBQpq8objeUysQcoiT4"
    "tpaFqMt/nyc0FzgkRM6mZ6jz9+LqLzf/ycrfOTPha6Ocmh66BNkDYS1w+fCxlTZFj21ZvP"
    "jLq6luukcbRNErrilLyMFzcGDlBnTBsD/mcryyXrJYmOKVuPpzlWn+Y4i755umWeY/Gvp9"
    "YovHJCJTomN9f6Kzs8S7QJWaKk9gDDKPZLEmTbwX4lAW741k2gneQYvseUDLqTsIi1xEoM"
    "2b5BCL2kNs+k5zo94xjmqRH7TACgT/EqivVsfozXrV5P9CZ0yZ6wrlGyXk/i9KdL9kTFfL"
    "ar1+PZULmH/Z3lnrOp095tzz3unWAEP+8bdN5DDSiMLxBlH/ghQRNP/N18KFOxDBWsSmeW"
    "0HSNdIfuBFEDWNaLjuXfEh+2ZSBNEXJMw3NHf4KlvkUUElSC4QHsc8WS3QqyG3wkK6Lj96"
    "1TmM41hcGYayENyLhtxOMdRxHv4MlPB7Gwm9/zADNsZlsVVC8nxpzoTlasfvkBuS3WGr8R"
    "LhlWcAK4fHNYjlaMW8ZNs4yJKLRsoBllpW2CkAvbmp2i/PvVuWlLZb5frWFZpDOkSzaMEU"
    "VD74FU/nFbA9glPRx2cx0bF4UCbhc5AbeLdMDNPWhLHXIxCp7HkvDdb5mGEQQJ6odf0SSM"
    "GGvUKQUjLKHK0Enj5VWz1dFE4i1XROu2N/MU0WNKydiJ49YN/ZeuIJOkaqa+sqtkde5jPF"
    "DriPsYD2Jht/Ax8iIpb+RsFKGpzJYsjc7vydXnQDSGK3MNUuaeoWn5+6aoIhIjaaYWshOl"
    "jmyNEiD6w5sJ4E4SlfFftH2BnAQxuwBJjISXIEmXIClx4FZ/sLz+H51YnKA="
)
