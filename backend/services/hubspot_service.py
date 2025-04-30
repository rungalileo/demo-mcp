import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class HubspotService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HubspotService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.api_key = os.getenv("HUBSPOT_API_KEY")
            if not self.api_key:
                raise ValueError("HUBSPOT_API_KEY environment variable is not set")
            
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Cache for mappings
            self._stage_mapping = None
            self._owner_mapping = None
            
            # Initialize session for connection reuse
            self._session = requests.Session()
            self._session.headers.update(self.headers)
            
            self._initialized = True
            logger.info("Initialized new HubspotService instance")
        else:
            logger.info("Reusing existing HubspotService instance")

    def _initialize_stage_mapping(self):
        """Initialize the mapping of stage IDs to stage names"""
        if self._stage_mapping is not None:
            return
        
        self._stage_mapping = {}
        
        try:
            # Get all pipelines
            pipelines_url = "https://api.hubapi.com/crm/v3/pipelines/deals"
            response = self._session.get(pipelines_url)
            
            if response.status_code != 200:
                logger.error(f"Error fetching pipelines: {response.status_code}")
                return
                
            pipelines = response.json().get("results", [])
            
            for pipeline in pipelines:
                pipeline_id = pipeline.get("id")
                stages = pipeline.get("stages", [])
                
                for stage in stages:
                    stage_id = stage.get("id")
                    if stage_id:
                        self._stage_mapping[stage_id] = {
                            "label": stage.get("label", "Unknown"),
                            "pipeline_id": pipeline_id,
                            "display_order": stage.get("displayOrder", 0)
                        }
        except Exception as e:
            logger.error(f"Error initializing stage mapping: {str(e)}")

    def get_owner_id_name_mapping(self):
        """Get mapping of owner IDs to owner names"""
        if self._owner_mapping is not None:
            return self._owner_mapping
            
        try:
            owners_url = "https://api.hubapi.com/crm/v3/owners"
            response = self._session.get(owners_url)
            
            if response.status_code != 200:
                logger.error(f"Error fetching owners: {response.status_code}")
                return {}
            
            owners_data = response.json()
            self._owner_mapping = {
                owner["id"]: f"{owner.get('firstName', '')} {owner.get('lastName', '')}" 
                for owner in owners_data.get("results", [])
            }
            
            return self._owner_mapping
        except Exception as e:
            logger.error(f"Error getting owner mapping: {str(e)}")
            return {}

    def get_pipeline_stages(self) -> List[Dict[str, Any]]:
        """Get all pipeline stages with detailed information"""
        try:
            pipelines_url = "https://api.hubapi.com/crm/v3/pipelines/deals"
            response = self._session.get(pipelines_url)
            
            if response.status_code != 200:
                logger.error(f"Error fetching pipelines: {response.status_code}")
                return []
            
            pipelines = response.json()
            all_stages = []
            
            for pipeline in pipelines.get("results", []):
                pipeline_id = pipeline.get("id")
                pipeline_name = pipeline.get("label")
                
                for stage in pipeline.get("stages", []):
                    stage_info = {
                        "pipeline_id": pipeline_id,
                        "pipeline_name": pipeline_name,
                        "stage_id": stage.get("id"),
                        "stage_name": stage.get("label"),
                        "display_order": stage.get("displayOrder"),
                        "probability": stage.get("probability")
                    }
                    
                    all_stages.append(stage_info)
            
            # Sort by pipeline name and display order
            return sorted(all_stages, key=lambda x: (x["pipeline_name"], x["display_order"]))
        except Exception as e:
            logger.error(f"Error getting pipeline stages: {str(e)}")
            return []

    def get_all_deals(self) -> List[Dict[str, Any]]:
        """Get all deals with their properties"""
        try:
            all_deals = []
            after = None
            
            if not self._stage_mapping:
                self._initialize_stage_mapping()
            
            while True:
                params = {
                    "limit": "100"
                }
                
                if after:
                    params["after"] = after
                
                deals_url = "https://api.hubapi.com/crm/v3/objects/deals"
                response = self._session.get(deals_url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Error fetching deals: {response.status_code}")
                    break
                
                deals = response.json()
                
                for deal in deals.get("results", []):
                    props = deal.get('properties', {})
                    
                    deal_stage_id = props.get('dealstage', 'N/A')
                    mapped_stage = 'N/A'
                    
                    if self._stage_mapping:
                        stage_info = self._stage_mapping.get(deal_stage_id, {})
                        if isinstance(stage_info, dict):
                            mapped_stage = stage_info.get("label", "N/A")
                        else:
                            mapped_stage = stage_info

                    all_deals.append({
                        'dealname': props.get('dealname', 'N/A'),
                        'stage': mapped_stage,
                        'stage_id': deal_stage_id,
                        'amount': props.get('amount', 'N/A'),
                        'created_at': props.get('createdate', 'N/A'),
                        'close_date': props.get('closedate', 'N/A'),
                        'updated_at': props.get('hs_lastmodifieddate', 'N/A'),
                        'owner': self.get_owner_id_name_mapping().get(props.get('hubspot_owner_id', 'N/A'), 'N/A')
                    })
                
                # Check for pagination
                paging_info = deals.get("paging", {}).get("next", {})
                after = paging_info.get("after")
                
                if not after:
                    break  # No more pages, exit loop
            
            return all_deals
        except Exception as e:
            logger.error(f"Error getting all deals: {str(e)}")
            return []

    def get_deals_by_stage(self, stage_name: str) -> List[Dict[str, Any]]:
        """Get all deals in a specific pipeline stage"""
        logger.info(f"Getting deals for stage: '{stage_name}'")
        
        try:
            all_deals = self.get_all_deals()
            
            # Try exact match first
            stage_deals = [deal for deal in all_deals if deal['stage'] == stage_name]
            
            # If no deals found, try case-insensitive match
            if not stage_deals:
                logger.info(f"No exact matches for '{stage_name}', trying case-insensitive match...")
                stage_deals = [deal for deal in all_deals if deal['stage'].lower() == stage_name.lower()]
            
            # If still no deals, try matching with trimmed whitespace
            if not stage_deals:
                logger.info(f"No case-insensitive matches, trying with trimmed whitespace...")
                stage_deals = [deal for deal in all_deals if deal['stage'].strip() == stage_name.strip()]
            
            # If still no deals, try looser matching (contains)
            if not stage_deals:
                logger.info(f"No whitespace-trimmed matches, checking if any stage contains '{stage_name}'...")
                stage_deals = [deal for deal in all_deals if stage_name.lower() in deal['stage'].lower()]
                
                if stage_deals:
                    similar_stages = set(deal['stage'] for deal in stage_deals)
                    logger.info(f"Found similar stages: {similar_stages}")
            
            logger.info(f"Found {len(stage_deals)} deals in stage: '{stage_name}'")
            return stage_deals
            
        except Exception as e:
            logger.error(f"Error getting deals by stage: {str(e)}")
            return [] 