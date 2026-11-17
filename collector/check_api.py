"""Проверка доступа к Ozon Seller API: читает OZON_SELLER_* из .env."""
import asyncio, sys
from ozonapi import SellerAPI

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы


async def main():
    async with SellerAPI() as api:
        info = await api.seller_info()
        print("Компания:", info.company.name)
        print("ИНН:", info.company.inn)


if __name__ == "__main__":
    asyncio.run(main())
