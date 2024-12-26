import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    @staticmethod
    def validate():
        if not Config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is not set")
