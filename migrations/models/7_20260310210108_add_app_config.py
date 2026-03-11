from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "app_config" (
            "key" VARCHAR(200) NOT NULL PRIMARY KEY,
            "value" JSON NOT NULL,
            "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "app_config";
        """


MODELS_STATE = (
    "eJztXetz2rgW/1c8fOrOpJkNt2m7fHOI07LhdYFsN7vseAQI8I2RXT+SZbv536/kJ5ZlYx"
    "sINuhLp0g6iv3T0dF56fhHbaXNoGpeilNLeVasdVtb1BrCjxoCK4j/w+q+EGpA18NO0mCB"
    "ieqMB95AWfVGTkzLwI24bw5UE+KmGTSnhqJbioZwK7JVlTRqUzxQQYuwyUbKdxvKlraA1h"
    "IauOPPv3Czgmbwb2j6P/Unea5AdRZ5amVG/rbTLltr3WlrIevOGUj+2kSeaqq9QuFgfW0t"
    "NRSMVpBFWhcQQQNYkExvGTZ5fPJ03tv6b+Q+aTjEfcQNmhmcA1u1Nl43IwZTDRH88NOYzg"
    "suyF95X7/68OnD5/98/PAZD3GeJGj59Oq+XvjuLqGDQHdUe3X6gQXcEQ6MIW6mBXXZ+RGD"
    "r7kEBhu/CBEFI354GkYftDQc/YYQyJB59oTkCvwtqxAtrCX+efXzzym4/SYOml/FwTs86i"
    "fyNhpmaJfbu15X3e0j4G6CCSzbZCMpIXvloNnCTwXQFDJQ9amPDGltOBIHI+m2IeBHMvAf"
    "HKPhQ7MpSbdOmz2dQjgjrXdiq02a5kBRnVH3rX7fGfOk6Dp0GSfnwvySYVl+SVyUX+glmU"
    "ELP1x8SUbw7wThEFIUWgZv/78hY6cANpJ+H5FnXpnmd3UTqXcd8XcHxNXa62n3ul/84RvI"
    "Ntu9GxpSG78+fkZ5xWD1RJlLUW0XvqXAdj/iN8RuakDyejKw4tDd4h5LWUE2flFKCr6ZR3"
    "rp/6ekIhi/w6yH1LW3lmmc2+pIWAx1+hH2vRVHEumpR1jXb333kZILwSTCt9boq0B+Cn/0"
    "upKDoGZaC8P5i+G40R818kzAtjQZaS8ymG0c6X6rD0x0YbXVCqCZnEsPiRIV2hLHWMU974"
    "kZfFamMB9yEZozkiVE/50/MTU5j5niIN5pBlQW6B6uY/oHhZyn+jfDmcrHfa8+K/it4Voa"
    "4CWwDKi9hV8Svxq0XHVMHDbFW6nG4MI9oHcbTFQ6DsyKXWR3RaAbSiOh+9Bu1xxOnIDp0w"
    "swZnKEJUmPVteolmBsvGtVX9EtAIGFAwF5EfLYvlWq600NzRW2yRp0XqQarLpOIPDHbTNX"
    "a0MLs4ApYDJVmTo6jIAZS9BVe6EgwYSWhTE3LwTtGRoqWOMfwiVEz4K3auYlrQbvPuMYjQ"
    "lHCgQAUwdTPKIxRu+FJp43oG/gCfEiCw60zlDhHbxcXArjGno25CU+AMf40cY1c2Xpsq4Z"
    "+OdPZJZ+9DkaeIj7aJc/yCyvlz+cKV/HtWBCr3+pWfIL5njj0tSQNp/Lio7nrF3sZNo/wX"
    "Ue49Qbvh8b6uDmfcT2qWcySuspRmndN0qTLf5noNoMOffrsNdlAxoQ0EqnMrWEfwVVMUuq"
    "qKRgSd423TCibSBKZSQT0IaRrc8KKvdRSq7cH1W5dx4+pmgd7bwbWsA5e1nHndu39bQzg2"
    "FH8c2ejwDfo1cxtwBPBjRJgFfEVXudCdTrFFCv465aLqu5rN6zrPbNZoao3rCokyX1hgHP"
    "Y2hlc7ykCWTf1eCgwJTL24M/9BxHDwFJI1n8Jj7K3d63BjEFZfAC1mTXjVHQdyu1xUcn3u"
    "P3Y6YGaycUhMd87XWkkH6praBL3xcfhqRj1LprNcVRq9cdYlsV2Cbpt5S5ZxOb/siB1OwN"
    "blvdL/4oA041Y4aXfIzEfr/9KN+0Rh1xeN9wTOq1PFGsFTCfioSfrrLEn66SA1BXsQhU9Y"
    "KCNR0igm4tzhZ9qesthDtkjP77ID0QFsDT22ThBw/drjPCsBFyRmSLHTbFblNqO01TgoTq"
    "tvY6/bY0km5lcnDI0mDQG2BmwbtFJy6pmfyiWEsZGoZmmEWWu36VxeC+Sra3r+IBR7wD5J"
    "WCbAvmio/RdGfk1Y7jZ+Idjmb58dugO1P8XAmZn/9idGeKnwUWeKRqQSOPiRWlqkjiwBuY"
    "WQpSLMUxlyZrWdHzQMogrSSuH64zwPrhOhFV0pUCKt61uTiVSVxJYOvXWZDFo5JP7+sYti"
    "b4Lv9PmzCj0SkJcREqjqaPpqOYyaaNbRuD4QNMTsKKEVYE07fOxeL5RCfhxornE7nmVIF1"
    "jRDuYVnLtYdKtIr+a6cuo5dAW2Ado5R8IY+8kKHHoYCopWj5Yh55MWfAXE404vCf2JaFly"
    "Jf7iGb+ozs5ZQsRBqcOK75E+r8KW+CGUuHaubMOjbv5M6xCwHfvH7F8PfceOR39wOoOm71"
    "ZKCpK1/l0/eSUKYsuGcsaZ2Uhx3xGJKZ3HTOINGiQqAcMtZJ70lGzJOxbZNjnyyxwYOgZZ"
    "P7FylB0Lx3CKt9ffAg3hIMjpbgy8sSQPaI3zBOOPHyiqgg4U37QWoIpHOMWt3b1pdeQ8Dz"
    "KAttjPoPg34b9+q2gXVi/LvVvce/FPQ0RoPeEPcYmonbByQQaJAQYG8gdr/gdgwiWuAesX"
    "MjDRoCWE2gMUaPUrtNIsxrqKokttzG6mFDULEWPUZfBpLUbQhYc4RojEaS2Ma7CgJ1jJqP"
    "Iu6YrgEilxYfyYXFNRkvPpLhYF0klPgxA0PQSm/IDh/ZccRjxcEK8cPPx5ZOIXqaDr3rhr"
    "skZcRnOXZaBkm7wLz/AjC7kvSKhkDSKvAmGX0lm0JzTrsCzJtFmiXLsrgXXTMsWTNmrNBE"
    "IudGic6SbRVThoi8C0MJudE0FQKUoIhECCnsJpjyUOAFWsq+nQo3vV474k+4adH+8AdyEr"
    "xzkzPwIMU1n+KomkvtRSY3j/HfzYkrTcqRZSK7sKHJcItlgjagfUNs89oTRwGXx3ZONLbD"
    "c89PYmHz5p7HEoZ3dE9lv6ZdHn9oZB94abqyYau7uuooZ9ONO/MAT1zOTVAGp90mSNv9dx"
    "Sk2V158uYy79+v9yfTd2iBRe0v7vI7rMuvPGG0Yxxjezb9lpptBFslF5AMynMFkaTh5sIu"
    "JDgnyMoevy3RgXxRIIDLrC9DTqTdsRyBioVmafzCDbcdsk3BtgfsvuLpbsLZqoshQ+BHwB"
    "xgO2bQao6OVaTHq4DE0imD2kgp+mM4hgeAS3ZwpGmDxw0Av3GhnkOEf72qW7sErKgpjh2t"
    "aoodaSCSC50r/BfHqN/7RqJUuvZSLEq19xCrg5ZpT5IxTwqy0pQVuZ9AX/nKdOMr5cIXDe"
    "nEYJYgzMa9AfGx+XYg9dpOXoIBNdVJTRiJ/R5eL6BrYzTsdXt3dw3BLXFWhI/TBK0P+6dE"
    "1D/RoDuHaO4i3g5VZVn3IBJ4+SI/Q8NUWGZPMpBRqkqiuX9BMFeMFdYkc3HkJk0lYTxIUX"
    "lFJxEIA5oJNSQSFNMIVSXR3P/F2ekSIAQZ1eCTKzSHFGeU30+lpLwoBrYtWfy3LSdlk5KH"
    "92PA6hpDPm7D1CPicEbhxKIOo2TlPLujVJUUk/VsNWNTSsbG1CCAucz6JydrblBx3qRqsl"
    "j/uOWxdMxvkJH1kVyVJU55pucQQcIpIVYIQ4ryjDE0dcjKLk1FL6A5U9z+0RCUibe9aHou"
    "ewIuJhNgdkReHOLkciFxyooc5W9dLyQEikjEYhD7lBxiJsRIY148TUY2IOCAMgHllyIOIW"
    "x5dvlJJCHz7PITXdhYtrQTNZWLfCyNQXlGinxKstsmMHE8z/HLXwxWqWJtkvIAHN/CWMC6"
    "+RC7XnmoHrcxb38A08S7bAUJ7R4A8TL8xGDWcp5TmSCa4V03De6f7wWeW3/KkZe4UlFoeJ"
    "Wf/VwYiiQoM5DsALQeaeTfw2YoHzp/L+UA3Eifib2GQdgHM1o0ZczFSTMchMnnqhqbic0B"
    "9l5P5DS1loZmL5Yb7V5iODMdGrfLdBrpa4bc27gQTEzGZcrLbdm5clx4O2T7vtkVHHHkSR"
    "y9NiIR+RWvQyf1+rgXSefzaY+dzbdZJyWsn1LLhm80IyVLQkpyPko8/zTCzAVhjs9ybMA7"
    "PfJNn4aw0kjLGPWlwZD81qFhkt+/SV9bTVIE6hkulSmpAiV2Wx1SnQkgZUXqM92JTYn8vS"
    "mpECU270VSAErHchULvSILt+eEy+N8sfwY3pSTu+RYTR8GO4STC0Ca7IzQS7vu+Oa+nxLZ"
    "DheZP/tevut55XFq0Chuu50XutCYu3oPSP6B5+pUHUZaXuV2Qx7+hmPUl5JoYcVcLlutq7"
    "hKdzjLiltUb1w0gyv91VT6eRpCgN4e0xC4KcUV2WMossfRGzZ1XIa+QKnAyXoCrXrzSgll"
    "26ppKgCvlLDjPd3UG/sZvqm947X9PWpNw5E4ajUbAglkKtMxun3sih3SMFvjl1WmJdB73E"
    "eTn4FX7D8r19J0Fclupdg3i8u/nuzzr8ec/qaNDMWEsjafm9Aq8KHm5AnOyKVHIUqA2AVQ"
    "Nv2Z4jlXVDX/do9SVXKzX2W5vJ98dT9225xnWJ9CIi7PsD7RhS1ev5tR2JjXr47n6JUgs7"
    "M88Y2DVvbuq/ZCQVj2gBrDrbDRe5HmVdCdcfLMH7jNqVC7h+v3zpGP7RfNgMJcMwR3EoFM"
    "ciGAZ02ZYbSIF/i917NSFu5HlcxL2rrZy4TMeIf3ar4lTTLzeKTjwG4OCvOsiiRFdigL/a"
    "Bej4MUgiJMmwNHbzj/vmIAYIJN8+uw12VDmGTOzJSpJfwrqIpZ0mBDCnbkbSPqWOyKLn0b"
    "l9KzyAT0FV1u6pyERsxNnRNd2LymziF11dh9G4bGyrqTk6y3uneB/Jq8wXgeE6uQssjTYi"
    "qaFuNuvvRc0JQgEZO6mt7jj5+z6PwfPyfr/KSPhW5Kcug2aCOklcT1w+dMxhQZlnz15jOj"
    "rq7pOGnsVZGErk1KXsaLGwMnqDPGjQHvs5X5kvWiROeUrcfTHPef5jgNv3m6Y55j9q+nli"
    "i8ckElOkY31/YrOzxLtApZoqT2AMMo9koSJNvBXiUBbviWTaBdpBi+55QMepCwiLnESgzZ"
    "vn4IPac2z6TnOj3jGOapEcdMAKBP8X0U6yl+jJetXk/4JnTJnqCuUbReT+T0p0v2hMV8dq"
    "vX49pQqYd9cFmXceJvXuRNPvYjLh5++PPDvyx7+A1C+s4hkztXOUpVzQyJQ7lFuffuRL13"
    "PJR/EgtbPGuZp+O+VTquCA1lumRpdF5Pqj4HwjFcmauQMlfg07G7fjf26FrIQZQ6sjVygO"
    "gNryaAB3GJ4b9oeQI5a6rrBglPdo0nux41d+71/zJXaII="
)
