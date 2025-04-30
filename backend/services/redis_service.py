import redis
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class RedisService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = redis.from_url(self.redis_url)
            self._initialized = True

    def get_company_data(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Get company data from cache"""
        data = self.redis.get(company_name.lower())
        if data:
            return json.loads(data)
        return None

    def set_company_data(self, company_name: str, data: Dict[str, Any], ttl: int = 86400) -> bool:
        """Set company data in cache with TTL (default 24 hours)"""
        try:
            self.redis.setex(
                company_name.lower(),
                ttl,
                json.dumps(data)
            )
            return True
        except Exception as e:
            print(f"Error setting cache: {str(e)}")
            return False

    def update_company_data(self, company_name: str, updates: Dict[str, Any]) -> bool:
        """Update specific fields in company data"""
        try:
            current_data = self.get_company_data(company_name)
            if not current_data:
                current_data = {
                    "full_transcript": "",
                    "likely_to_buy_count": 0,
                    "champions": []
                }
            
            # Update fields
            for key, value in updates.items():
                if key == "champions":
                    # Merge champions list
                    current_data["champions"].extend(value)
                else:
                    current_data[key] = value
            
            return self.set_company_data(company_name, current_data)
        except Exception as e:
            print(f"Error updating cache: {str(e)}")
            return False

    def delete_company_data(self, company_name: str) -> bool:
        """Delete company data from cache"""
        try:
            self.redis.delete(company_name.lower())
            return True
        except Exception as e:
            print(f"Error deleting cache: {str(e)}")
            return False

    def get_all_company_keys(self) -> List[str]:
        """Get all company keys in cache"""
        return [key.decode('utf-8') for key in self.redis.keys("*")] 