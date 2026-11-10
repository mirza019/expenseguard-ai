"""Environment configuration without secret logging."""
import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    ollama_url: str = 'http://localhost:11434'
    ollama_model: str = 'qwen3:4b'
    timeout: int = 60
    max_calls: int = 4
    max_retries: int = 2

    def __post_init__(self) -> None:
        parsed = urlparse(self.ollama_url)
        if parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('Ollama must use an HTTP loopback address.')
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Ollama URL cannot include credentials, queries or fragments.')
        if not 1 <= self.max_calls <= 4 or not 0 <= self.max_retries <= 3:
            raise ValueError('Agent limits must be 1–4 tools and 0–3 retries.')


def settings() -> Settings:
    """Load local .env; process environment takes precedence."""
    load_dotenv()
    return Settings(ollama_url=os.getenv('OLLAMA_URL', 'http://localhost:11434'),
                    ollama_model=os.getenv('OLLAMA_MODEL', 'qwen3:4b'))
