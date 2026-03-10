from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "dashboard_button" DROP COLUMN "hour_bitmask_id";
        CREATE TABLE "dashboard_button_bitmask_rule" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "dashboard_button_id" INT NOT NULL REFERENCES "dashboard_button" ("id") ON DELETE CASCADE,
            "tag_id" INT NOT NULL REFERENCES "tag" ("id") ON DELETE CASCADE,
            "hour_bitmask_id" INT NOT NULL REFERENCES "hour_bitmask" ("id") ON DELETE RESTRICT,
            UNIQUE ("dashboard_button_id", "tag_id")
        );
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "dashboard_button_bitmask_rule";
        ALTER TABLE "dashboard_button" ADD COLUMN "hour_bitmask_id" INT REFERENCES "hour_bitmask" ("id") ON DELETE SET NULL;
        """


MODELS_STATE = (
    "eJztXetzmzoW/1c8/tSdyd5pvEma+hu2SeONX2uT25te32EwVmw2WFAeSd27/d9X4o0QBD"
    "AOEPOl00g6Mvx0dHSe4u/2TlkDWf+NEQ3pWTL2I2XT7rb+bkNhB9B/aN1nrbagqn4nbjCE"
    "lWyNF5yBvOyMXOmGhhpR36Mg6wA1rYEuapJqSApErdCUZdyoiGigBDd+kwml7ybgDWUDjC"
    "3QUMeff6FmCa7BD6C7f6pP/KME5HXoqaU1/m2rnTf2qtU2hMaNNRD/2ooXFdncQX+wuje2"
    "CvRGS9DArRsAgSYYAE9vaCZ+fPx0ztu6b2Q/qT/EfsQAzRo8CqZsBF43JQaiAjF+6Gl06w"
    "U3+Ff+2Tm/+HRx/a+ri2s0xHoSr+XTL/v1/He3CS0EJlz7l9UvGII9woLRx003gMpbf0Tg"
    "628FjY5fiIiAET08CaMLWhKOboMPpM88BSG5E37wMoAbY4v+PP/4MQG335l5/5aZf0Cj/o"
    "HfRkEMbXP7xOnq2H0Y3CCYgmHqdCRZaO4sNIfoqQQoAgqqLnXJkLYXHDPn2EG3hR5JQz+4"
    "hIv7fp9lB1abKYoArHHrDTMc4aZHQZKtUXfD2cwa8ySpKrAZJ+PCfE6xLJ9jF+UzuSRrYK"
    "CHiy4JB37ECAefItcyOPv/DRk7ATCO/YPDz7zT9e9yEKkPY+YPC8Td3ukZTSdf3OEBZPuj"
    "aY+E1ESvj56R31FYPVbmElSvC99KYFuM+PWxEzWAX48XjCh0A9RjSDtAxy9MScC3dkh/c/"
    "9TURGM3mE9hfLeWcskzh2OWSSGxrMQ+w4YjsU9nRDruq0frgi54E3S+jrkblv4z9a36YS1"
    "EFR0Y6NZv+iP47618TMJpqHwUHnhhXXgSHdbXWDCC6vsdgJc85n0kDBRri1RxioWvCfW4F"
    "kSQTbkQjQnJEuw/vv4RNXkHGaKgnijaEDawDuwj+gfBHKO6t/3Z6oe9/1yWcFt9ddSE148"
    "y4DYW+gl0asBw1bHmEWfGbBtChcWgN7Am6hyHJgWu9DuCkG3YLnW5H40alucuBLEpxdBW/"
    "MhlsQ9SkchWryx0a5dZ0e2CFDYWBDgF8GP7VqlqrpAajJo0yxWt+8s0VxVVV73hpViqz6B"
    "fRZryxlejFFwdHv1WFZWvAn7LMhmJvPVI6in6XqZCtTLBFAvo6arqa5zKqZhykYxLVUxtR"
    "4+oiSUI6tdNYIiqgMaRrykDig0jU+xaopokkB2VS8LBapcft0ZRs5RukuM5XjmK/PAT6Zf"
    "uy0dGLzwIuzxrltCr2/AjpgHy//l9iOmFvaWawyNuZ2OWZ9+q+yATT9j7he4gxveDPsMN5"
    "xOFt2WKpg67jekR0m0PCe6O3LO9qfzwXDyxR2lAVHR1mjJl5CZzUYPfG/IjZnFXbeFdpe8"
    "51eSsRP0pzzuuPM0/rjzeIfcecQjVz8naVsFEKPbjrLFjJ04C2EPWcL/3LP3mAXQ9CZe+P"
    "n9ZGKN0EwIrRHpfKl9ZtJnR1aTiJGQ7dbpeDZiOXbA44ODZ+fz6RwxC9otKlbR1/yLZGx5"
    "oGmKpudZ7s55iuXunMcuN+4irXu0A/idBE0DZPIXknQnZOVH8dPRDofr7PgF6E4UP1tCZu"
    "e/CN2J4mcIGzRSNoCWxcQKU9UkkPIGZpYEJUOyzKXVnpfULJBSSGuJ68VlClgvLmNRxV0J"
    "oKJdm4lTqcS1BLZzmQZZNCr+9L6MYKsL3/n/Kiuqdz4hQSBE1aDpomkpZrxuIttGo/gA44"
    "PSEcKaYPrWsekmvvou3FjR+KptTuVY1xBhActarT1UoVV0XztxGZ2EohzrGKZsFrLkhfQ9"
    "DjlELUHbLGbJi7kW9O1KwQ7/lWkYaCmy5WLQqU/IXk7IyiDBKSLBwJ2y581YOVRTZxrQeS"
    "dzzoEPeDAdneLv6TnkN3dzIFtu9XigiRT46ul7cSgTFtwzkrRWysOBeCzwTHZ6i5doUSNQ"
    "jhnrJPckJeZJ2bbxsU+a2GiCoFWT+2cJQdCsNRX1Lqc4ircEgaPE+PLSBJAd4jeME66cvC"
    "IiSNgb3bPdFu5cwuFkMPwy7bbQPNJGWcLZ/Xw2Qr2qqSGdGP09nNyhvyT4tITz6QL1aIqO"
    "2uc4EKjhEOB0zky+oHYEItygHmbcY+fdlrBbAW0JH9jRCEeY90CWcWx5hNTDbktGWvQSfp"
    "mz7KTbQpojgEvIscwI7SogyEvYf2BQh7gXIC7ieMAFHHs8nnnAw4V9nlDiVQqGIJVenx2u"
    "6HHEsuJgufjhY9nSyUdPUYFTfnFIUkZ0lrLTMnDaBeL9FwGxK06v6LZwWgXaJNwt3hSKdd"
    "rlYN400ixelkW96Ipm8Iq2poUmYjk3THSSbCvpPID4XShKSE9RZCDAGEUkREhgt0KUxwLP"
    "01KKdir0ptNRyJ/QG5L+8Ht8EnywkzPQIMk2n5oipJNxkjdJvO9iYbMm8UYyLw+089PX/1"
    "THsRTaB06+I6+Z8qE+D8Jq79kzz9HE1dwEVfB+BEF63RFCQJreJ8IHl7l4B8mfVCeMIWza"
    "fzW+k+P6TqoTjyjjGCtYh94qpuZtlUxAUihPFUScz5gJO5/glCCreiCsQgfyWY5IGLVwGZ"
    "9Ih2PJCTWLcZH4+RvudciCgq0A7G7RdD1/tvpiSBH4ITDnyI6ZD/tcWdXfTmk9Taf0iu4T"
    "9Ed/TBNJq9jBkaQNlhtJe9uC+aPE0ZzrHA7x/BNTlO327zNjds7gyrgd+sUlnE2/Yne/qr"
    "zkc/cXHquy0NLNVTzmcdEqkrImid5k7Uyq0pmEyhkS0pVGvdsmHfd6xGXz7ZydjqwArwYU"
    "2YrxcsxsitZLUJUlXEwn05ubbktXoPL4mIePkwStC/unWNQ/kaBbh2jm2yEtqtqy7lEk8P"
    "aFfwaaLtHMnnggw1S1RLN4QfAoaTukSWbiyCBNLWE8ym2lkoojEBrQY4rxYxTTEFUt0Sy+"
    "AlHcChACyjWj8Vf/+RQnlChNxPZfJA3ZljT+ey24H6R8w+h+VmuxlPA+gkdVKPLxNUwdog"
    "bOMJxI1CGUjIxnd5iqlmKyk+bM6cQfOZ3IibMVEJcZPzOyZoCq4U3icgvjp33PkIr4DVCy"
    "PuKvt4hSnug5hJGw7mLKhSFBecIY6iqgpekloufRnChuPxUIeOxtz5vnSJ+gEZMxMFsiLw"
    "px/L0LUcqaHOVvffGCDxSWiPkgdikbiKkQQ4VawRePrEfQAEoFtMkuP4awbbLL30UScpNd"
    "/k4XNpItbUVN+Txf4aBQnpAin5DsFgQmiucpflKCwip1vOShOgBHtzASsHY+xKElD/XjNm"
    "r1h6DraJftAKYtABAnw4/xZq3mOZUKojXadaJXyFsIPAN3Ss5JXKkpNM11KcUUDIUSlClI"
    "jgW45xT873EzlI+dv5dwAAbSZyKvoWH2QYwWThmzcVI0C2H83Z9uMLHZw97pCZ2mxlZTzM"
    "020O4khlPToVE7T6aR/kqRexsVgrHJuFR5+Vp2Lh8V3hZZ0ZVd3hGHn8TSa0MSsSnxOnZS"
    "r4t7nnQ+l7bsbL7ghRP+RRTtdPiGM1LSJKTE56NQPnobZOacMEdnKRvw8RR/HKXb2im4ZQ"
    "ln7HyB/1aBpuO/f2dvh318m84z2Eoivk6HmQzH+JobAUo7fNHNDdNn8e+J+Kodpn/H4Jt0"
    "VCRXkdDLs3AFJ1yW8ynMMrwp767IsZ4+DHoIJxOAJNkJoZdU7vjmvp8K2Q5nqb8nWr3yvO"
    "o4NUgUX6vO811o1F1dAJLf0FzjusNIyqtKfd+W5kuJtbAiLpdXrauoSnc8y6qxqN740oxG"
    "6a+n0t+kIXjoFZiG0JhSjSJbhiJbjt4Q1HEp+gKhAsfrCaTq3dyUULWtmqQCNDclHFinm1"
    "ixn+LjxAeW7ReoNS04hhv2uy0cyJTEJRw8TJgxbljv0ctKYgX0HvvR+GfBuTU9LdeSdDXJ"
    "biXYN43LvxPv8+9EnP66CTVJB7zy+Ig/L579i7fxE5yQS49AFANxCKB0+hPF81GS5ezbPU"
    "xVy82e5qPq8d9Uj3xSvcmwfheJuE2G9Ttd2Pz3d1MuNm7ur47m6FUgs7M68Y2j3uwdyWGk"
    "OBdoeY7xHgY7v9K958wb3/gZKqe4NaGGdxdqsDdfcnw9wfCmUtdTI7+6TqOTX13Ha+W4j4"
    "ZuQsD9NWhDpLXE9eI61U1leFh8OuM15a4y3Tr4zF2eIFmQsrkaobEl36HJEbUlnU8BZQuA"
    "holOKQLahI6LDx2L/nekDowdp/8iVYVM1jMieBzeXK+nQTaR9zpE3nE9F8Uodsq84u1gpz"
    "qrMXyrJtDOmgD78e4c1rdIicHb13VLZtTmqfSNTk85hht3c5lOVfIUL6IAOv8xXrUaaP9N"
    "yDJor1Y8XAMdOv3JMmi/QPqwGmjbhko87L0CCMqJHyyOiD/2Qy6e5vBvDv+q7OE3yK6zDp"
    "nM+R9hqpJDBBVzizbeu3fqvWsyQd7FwubPBGlSHN4qxYEBmiRuaRqd05Oozwn+mEaZq5Ey"
    "l+NzXId+i6t0LeQoSh3eGhlAdIbXE8CjuMTQLxqOQA6D+O/FdBIXpvNIyANeEo3W/1qypF"
    "c05JSAH37f0CkeueObvM6bOJ7xBL1svrDiD5Zf/wfTxdfs"
)
