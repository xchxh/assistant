import asyncio
from api import scraper

async def main():
    models = await scraper.fetch_upstream_models()
    for k, v in models.items():
        print(f"{k}: {v['name']}")

if __name__ == "__main__":
    asyncio.run(main())
