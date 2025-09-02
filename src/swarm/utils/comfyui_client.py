"""
ComfyUI client for generating avatar images for blueprints/agents.
"""

import json
import time
import requests
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from django.conf import settings

logger = logging.getLogger(__name__)

class ComfyUIClient:
    """Client for interacting with ComfyUI API for image generation."""
    
    def __init__(self):
        self.enabled = getattr(settings, 'COMFYUI_ENABLED', False)
        self.api_endpoint = getattr(settings, 'COMFYUI_API_ENDPOINT', 'http://localhost:8188/api')
        self.queue_endpoint = getattr(settings, 'COMFYUI_QUEUE_ENDPOINT', 'http://localhost:8188/queue')
        self.history_endpoint = getattr(settings, 'COMFYUI_HISTORY_ENDPOINT', 'http://localhost:8188/history')
        
        if not self.enabled:
            logger.info("ComfyUI is disabled. Avatar generation will not be available.")
    
    def is_available(self) -> bool:
        """Check if ComfyUI is available and responding."""
        if not self.enabled:
            return False
        
        try:
            response = requests.get(f"{self.api_endpoint}/object_info", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"ComfyUI not available: {e}")
            return False
    
    def generate_avatar(self, 
                       blueprint_name: str, 
                       description: str, 
                       category: str,
                       style: str = "professional") -> Optional[str]:
        """
        Generate an avatar image for a blueprint.
        
        Args:
            blueprint_name: Name of the blueprint
            description: Description of the blueprint
            category: Category of the blueprint
            style: Style of the avatar (professional, cartoon, anime, etc.)
            
        Returns:
            Path to the generated avatar image, or None if generation failed
        """
        if not self.enabled or not self.is_available():
            logger.warning("ComfyUI not available for avatar generation")
            return None
        
        try:
            # Create a prompt based on the blueprint information
            prompt = self._create_avatar_prompt(blueprint_name, description, category, style)
            
            # Generate the workflow
            workflow = self._create_avatar_workflow(prompt)
            
            # Submit the workflow
            prompt_id = self._submit_workflow(workflow)
            if not prompt_id:
                return None
            
            # Wait for completion and get the result
            image_path = self._wait_for_completion(prompt_id, blueprint_name)
            return image_path
            
        except Exception as e:
            logger.error(f"Error generating avatar for {blueprint_name}: {e}")
            return None
    
    def _create_avatar_prompt(self, 
                            blueprint_name: str, 
                            description: str, 
                            category: str,
                            style: str) -> str:
        """Create a prompt for avatar generation."""
        
        # Base prompts for different styles
        style_prompts = {
            "professional": "professional headshot, business portrait, clean background, high quality, detailed",
            "cartoon": "cartoon character, colorful, friendly, simple background, clean lines",
            "anime": "anime character, detailed face, expressive eyes, clean background, high quality",
            "realistic": "realistic portrait, detailed face, natural lighting, professional photography",
            "icon": "simple icon, minimalist, clean design, single color background, professional"
        }
        
        # Category-specific elements
        category_elements = {
            "ai_assistants": "AI assistant, intelligent, helpful, digital",
            "code_helpers": "programmer, developer, technical, coding",
            "content_creators": "creative, artistic, writer, content creator",
            "system_tools": "system administrator, technical, tools, utilities",
            "web_services": "web developer, internet, connectivity, modern"
        }
        
        style_prompt = style_prompts.get(style, style_prompts["professional"])
        category_element = category_elements.get(category, "AI assistant")
        
        # Create the main prompt
        main_prompt = f"{category_element} avatar for {blueprint_name}. {description}. {style_prompt}"
        
        # Add negative prompt to avoid unwanted elements
        negative_prompt = "text, watermark, signature, blurry, low quality, distorted, multiple faces"
        
        return f"{main_prompt}, {negative_prompt}"
    
    def _create_avatar_workflow(self, prompt: str) -> Dict[str, Any]:
        """Create a ComfyUI workflow for avatar generation."""
        
        # This is a basic workflow - you can customize it based on your ComfyUI setup
        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "realisticVisionV51_v51VAE.safetensors"
                }
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["1", 1]
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "blurry, low quality, distorted, multiple faces, text, watermark",
                    "clip": ["1", 1]
                }
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                }
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 42,
                    "steps": 20,
                    "cfg": 7,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0]
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2]
                }
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["6", 0],
                    "filename_prefix": "avatar"
                }
            }
        }
        
        return workflow
    
    def _submit_workflow(self, workflow: Dict[str, Any]) -> Optional[str]:
        """Submit a workflow to ComfyUI and return the prompt ID."""
        try:
            response = requests.post(
                self.api_endpoint,
                json={"prompt": workflow},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('prompt_id')
            else:
                logger.error(f"Failed to submit workflow: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error submitting workflow: {e}")
            return None
    
    def _wait_for_completion(self, prompt_id: str, blueprint_name: str) -> Optional[str]:
        """Wait for workflow completion and return the image path."""
        max_wait_time = 300  # 5 minutes
        check_interval = 2   # 2 seconds
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Check queue status
                response = requests.get(self.queue_endpoint, timeout=5)
                if response.status_code == 200:
                    queue_data = response.json()
                    
                    # Check if our prompt is still in queue
                    if not queue_data.get('queue_running') and not queue_data.get('queue_pending'):
                        # Check history for our result
                        history_response = requests.get(self.history_endpoint, timeout=5)
                        if history_response.status_code == 200:
                            history_data = history_response.json()
                            
                            if prompt_id in history_data:
                                # Get the image path from history
                                prompt_data = history_data[prompt_id]
                                outputs = prompt_data.get('outputs', {})
                                
                                for node_id, node_output in outputs.items():
                                    if 'images' in node_output:
                                        images = node_output['images']
                                        if images:
                                            # Get the first image
                                            image_info = images[0]
                                            filename = image_info.get('filename')
                                            
                                            if filename:
                                                # Move the image to our avatar storage
                                                return self._save_avatar_image(filename, blueprint_name)
                
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error checking completion: {e}")
                time.sleep(check_interval)
        
        logger.error(f"Timeout waiting for avatar generation for {blueprint_name}")
        return None
    
    def _save_avatar_image(self, filename: str, blueprint_name: str) -> Optional[str]:
        """Save the generated image to avatar storage."""
        try:
            # Get the image from ComfyUI output directory
            comfyui_output = Path("/tmp/ComfyUI/output")  # Default ComfyUI output path
            source_path = comfyui_output / filename
            
            if not source_path.exists():
                logger.error(f"Generated image not found: {source_path}")
                return None
            
            # Create avatar filename
            avatar_filename = f"{blueprint_name.lower().replace(' ', '_')}_avatar.png"
            avatar_path = settings.AVATAR_STORAGE_PATH / avatar_filename
            
            # Copy the image
            import shutil
            shutil.copy2(source_path, avatar_path)
            
            # Return the relative path for URL generation
            return f"{settings.AVATAR_URL_PREFIX}{avatar_filename}"
            
        except Exception as e:
            logger.error(f"Error saving avatar image: {e}")
            return None

# Global ComfyUI client instance
comfyui_client = ComfyUIClient()

