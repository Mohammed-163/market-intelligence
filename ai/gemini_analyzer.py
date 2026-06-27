import google.generativeai as genai
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger()
settings = Settings.load()

class GeminiAnalyzer:
    def __init__(self):
        if not settings.gemini_rotator:
            logger.warning("No Gemini keys configured.")
            self.model = None
            return
            
        api_key = settings.gemini_rotator.get_current_key()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_market_report(self, target: str, data: list):
        if not self.model:
            return "AI Analysis unavailable due to missing keys."
            
        logger.info(f"Generating market report for {target}")
        prompt = f"Analyze the following recent data for '{target}':\n\n{data}\n\nProvide a summary of the market trends, sentiment, and key insights."
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API failed: {e}")
            return "Error during AI analysis."
