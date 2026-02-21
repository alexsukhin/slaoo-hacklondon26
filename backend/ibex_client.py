import httpx
from typing import Dict, Any, Optional, List
import os
from datetime import date


class IBexClient:
    def __init__(self, api_key: str, base_url: str = "https://ibex.seractech.co.uk"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def search_by_location(
        self,
        latitude: float,
        longitude: float,
        radius: int = 300,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        extensions: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        payload = {
            "input": {
                "srid": 4326,
                "coordinates": [longitude, latitude],
                "radius": radius,
                "page": 1,
                "page_size": 1000
            }
        }
        
        if date_from:
            payload["input"]["date_from"] = date_from
        if date_to:
            payload["input"]["date_to"] = date_to
        if date_from or date_to:
            payload["input"]["date_range_type"] = "validated"
        
        if extensions:
            payload["extensions"] = extensions
        else:
            payload["extensions"] = {
                "appeals": True,
                "centre_point": True,
                "heading": True,
                "project_type": True,
                "num_new_houses": True,
                "document_metadata": True,
                "proposed_unit_mix": True,
                "proposed_floor_area": True,
                "num_comments_received": True
            }
        
        if filters:
            payload["filters"] = filters
        
        print(f"[IBex] Searching location: ({latitude}, {longitude}), radius: {radius}m")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            print(f"[IBex] Found {len(data) if isinstance(data, list) else 'unknown'} applications")
            return data
    
    async def search_by_council(
        self,
        council_ids: List[int],
        date_from: str,
        date_to: str,
        filters: Optional[Dict[str, Any]] = None,
        extensions: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        payload = {
            "input": {
                "date_range_type": "validated",
                "date_from": date_from,
                "date_to": date_to,
                "council_id": council_ids,
                "page": 1,
                "page_size": 1000
            }
        }
        
        if extensions:
            payload["extensions"] = extensions
        else:
            payload["extensions"] = {
                "project_type": True,
                "heading": True,
                "appeals": True,
                "num_new_houses": True,
                "document_metadata": True,
                "proposed_unit_mix": True,
                "proposed_floor_area": True,
                "num_comments_received": True
            }
        
        if filters:
            payload["filters"] = filters
        
        print(f"[IBex] Searching councils: {council_ids}, dates: {date_from} to {date_to}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/applications",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            print(f"[IBex] Found {len(data) if isinstance(data, list) else 'unknown'} applications")
            return data
    
    async def get_council_stats(
        self,
        council_id: int,
        date_from: str,
        date_to: str
    ) -> Dict[str, Any]:
        payload = {
            "input": {
                "council_id": council_id,
                "date_from": date_from,
                "date_to": date_to
            }
        }
        
        print(f"[IBex] Getting stats for council {council_id}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/stats",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            print(f"[IBex] Retrieved council stats")
            return data
