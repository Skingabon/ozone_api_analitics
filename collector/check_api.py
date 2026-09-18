"""Проверка доступа к Ozon Seller API: читает OZON_SELLER_* из .env."""
import asyncio
from ozonapi import SellerAPI


async def main():
    async with SellerAPI() as api:
        info = await api.seller_info()
        print("Компания:", info.company.name)
        print("ИНН:", info.company.inn)


if __name__ == "__main__":
    asyncio.run(main())
