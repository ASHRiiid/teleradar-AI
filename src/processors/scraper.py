import httpx
from datetime import datetime
from src.models import ScrapedContent
from loguru import logger

class JinaScraper:
    def __init__(self, base_url: str = "https://r.jina.ai/"):
        self.base_url = base_url

    async def scrape(self, url: str) -> ScrapedContent:
        target_url = f"{self.base_url}{url}"
        logger.info(f"Scraping: {url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(target_url)
                response.raise_for_status()
                
                # Jina returns markdown directly in body
                content = response.text
                
                return ScrapedContent(
                    url=url,
                    title=None, # Jina usually puts title in the markdown header
                    markdown=content
                )
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                return ScrapedContent(url=url, title="Error", markdown=f"Failed to scrape: {str(e)}")
