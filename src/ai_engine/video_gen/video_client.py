import os
import time
import subprocess
import requests
import imageio_ffmpeg
from PIL import Image
from core.config.config_manager import ConfigManager

class VideoGenClient:
    def __init__(self, api_key=None, base_url=None, model=None, provider=None, api_config=None):
        self.api_key = api_key or "sk-placeholder"
        self.base_url = base_url
        self.model = model or "luma-dream-machine"
        self.provider = provider or "mock"
        # Pass-through of full API config (from resources/config/config.json)
        # This may contain provider-specific options like 'duration', 'hd', 'watermark', 'private', 'notify_hook'
        self.api_config = api_config or {}

    def generate_video(self, image_path, prompt, output_path, text=None, voice_id=None, aspect_ratio="16:9", language="Chinese", end_image_path=None, input_video_path=None):
        """
        Generates a video from an image and saves it to output_path.
        Returns: (video_path, task_id) tuple for retry capability, or just video_path for legacy support
        """
        print(f"Generating video from {image_path} with prompt '{prompt}' using {self.model} (Ratio: {aspect_ratio})")
        
        # Mock generation (Local FFmpeg)
        if self.provider == "mock" or self.api_key == "sk-placeholder":
            return self._generate_ken_burns_video(image_path, output_path)

        # Luma Dream Machine API (Placeholder)
        if self.provider.lower() == "luma":
            return self._generate_luma_video(image_path, prompt, output_path)

        # Runway (via 302.ai or direct)
        if "runway" in self.provider.lower() or "runway" in self.model.lower() or "302" in self.provider.lower():
            return self._generate_runway_video(image_path, prompt, output_path)

        # Veo 3.1 / Sora (including Google official and Comfly)
        # Check provider, model, or base_url for veo/sora/google/comfly
        base_url_lower = (self.base_url or "").lower()
        if ("veo" in self.provider.lower() or "veo" in self.model.lower() or 
            "google" in self.provider.lower() or "comfly" in self.provider.lower() or
            "sora" in self.model.lower() or "comfly" in base_url_lower):
            return self._generate_veo_video(image_path, prompt, output_path, text, voice_id, aspect_ratio, language, end_image_path, input_video_path)

        # ComfyUI (Local)
        if "comfy" in self.provider.lower():
            return self._generate_comfyui_video(image_path, prompt, output_path)

        # Default fallback
        return self._generate_ken_burns_video(image_path, output_path)

    def retry_fetch_video(self, task_id, output_path):
        """
        Retry fetching a video using a previously saved task_id.
        Useful when initial generation timed out during download.
        """
        from ai_engine.veo_service import VeoService
        
        print(f"Retrying video fetch for task_id: {task_id}")
        base_url = self.base_url if self.base_url else "https://api.veo.ai/v1"
        veo = VeoService(self.api_key, base_url, extra_config=self.api_config)
        return veo.retry_fetch_video(task_id, output_path)

    def _generate_comfyui_video(self, image_path, prompt, output_path):
        """
        Generates video using ComfyUI.
        """
        from ai_engine.video_gen.comfyui_service import ComfyUIService
        import json
        
        print("Calling ComfyUI API...")
        
        # Use configured base_url or default
        base_url = self.base_url if self.base_url else "http://127.0.0.1:8188"
        
        comfy = ComfyUIService(base_url)
        
        # Load Workflow
        # Try to find a workflow file in resources/workflows
        # We look for one matching the model name, e.g., "svd.json"
        workflow_name = f"{self.model}.json" if self.model else "svd.json"
        
        # Base dir resolution
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        workflow_path = os.path.join(base_dir, "resources", "workflows", workflow_name)
        
        if not os.path.exists(workflow_path):
            # Fallback to default svd.json if specific model not found
            workflow_path = os.path.join(base_dir, "resources", "workflows", "svd.json")
            
        if not os.path.exists(workflow_path):
            print(f"Error: Workflow file not found at {workflow_path}")
            return None
            
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_template = json.load(f)
        except Exception as e:
            print(f"Error loading workflow: {e}")
            return None
            
        return comfy.generate_video(image_path, prompt, output_path, workflow_template)

    def _generate_veo_video(self, image_path, prompt, output_path, text=None, voice_id=None, aspect_ratio="16:9", language="Chinese", end_image_path=None, input_video_path=None):
        """
        Generates video using Veo 3.1 API.
        """
        from ai_engine.veo_service import VeoService
        
        print("Calling Veo 3.1 API...")
        
        # Use configured base_url or default
        base_url = self.base_url if self.base_url else "https://api.veo.ai/v1"
        
        veo = VeoService(self.api_key, base_url, extra_config=self.api_config)
        
        # If text is provided, use generate_scene for full video+audio
        if text:
            print(f"Using Veo Scene Generation (Video+Audio) for: {text[:30]}...")
            return veo.generate_scene(
                image_path=image_path,
                text=text,
                voice_id=voice_id,
                prompt=prompt,
                output_path=output_path,
                model=self.model,
                aspect_ratio=aspect_ratio,
                language=language,
                end_image_path=end_image_path,
                input_video_path=input_video_path
            )
        
        # Otherwise just video
        return veo.generate_video(
            prompt=prompt, 
            image_path=image_path, 
            output_path=output_path,
            model=self.model,
            aspect_ratio=aspect_ratio,
            end_image_path=end_image_path,
            input_video_path=input_video_path
        )

    def _ensure_runway_resolution(self, image_path):
        """
        Resizes/Crops image to meet Runway Gen-4 requirements: 1280x768 or 768x1280.
        Returns path to the processed image (or original if no change needed).
        """
        try:
            with Image.open(image_path) as img:
                w, h = img.size
                
                # Determine target resolution
                if w >= h:
                    target_w, target_h = 1280, 768
                else:
                    target_w, target_h = 768, 1280
                
                if (w, h) == (target_w, target_h):
                    return image_path
                
                print(f"Resizing image from {w}x{h} to {target_w}x{target_h} for Runway...")
                
                # Resize and Crop (Aspect Fill)
                img_ratio = w / h
                target_ratio = target_w / target_h
                
                if img_ratio > target_ratio:
                    # Image is wider than target: resize by height, then crop width
                    new_h = target_h
                    new_w = int(w * (target_h / h))
                else:
                    # Image is taller than target: resize by width, then crop height
                    new_w = target_w
                    new_h = int(h * (target_w / w))
                    
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # Center Crop
                left = (new_w - target_w) / 2
                top = (new_h - target_h) / 2
                right = (new_w + target_w) / 2
                bottom = (new_h + target_h) / 2
                
                img = img.crop((left, top, right, bottom))
                
                # Save to temp file
                dir_name = os.path.dirname(image_path)
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                temp_path = os.path.join(dir_name, f"{base_name}_runway_temp.png")
                img.save(temp_path)
                return temp_path
                
        except Exception as e:
            print(f"Error resizing image: {e}")
            return image_path

    def _generate_runway_video(self, image_path, prompt, output_path):
        """
        Generates video using Runway Gen-3/Gen-4 API (specifically 302.ai interface).
        """
        print("Calling Runway API...")
        
        # Ensure resolution
        image_path = self._ensure_runway_resolution(image_path)
        
        # Determine endpoints based on base_url or default to 302.ai
        base_url = self.base_url if self.base_url else "https://api.302.ai"
        if base_url.endswith("/"):
            base_url = base_url[:-1]
            
        # Construct Submit URL
        # Default to gen4-turbo if not specified, or use model name to decide
        submit_url = f"{base_url}/runway_gen4_turbo/submit"
        
        # If model implies Gen3, adjust URL (optional, but good for flexibility)
        if "gen3" in self.model.lower():
             submit_url = f"{base_url}/runway_gen3/submit" # Example, adjust if needed
        
        api_key = self.api_key
        if api_key.startswith("Bearer "):
            api_key = api_key.replace("Bearer ", "")
            
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        try:
            # 1. Submit Task
            print(f"Submitting task to {submit_url}")
            with open(image_path, 'rb') as img_file:
                # Explicitly provide filename to ensure correct multipart handling
                files = {
                    'init_image': (os.path.basename(image_path), img_file)
                }
                data = {
                    'text_prompt': prompt if prompt else "",
                    'seconds': "10", # Default to 10s
                    'seed': "",
                    'callback': ""
                }
                
                response = requests.post(submit_url, headers=headers, files=files, data=data)
                
                if response.status_code != 200:
                    print(f"Submit failed: {response.status_code}")
                    print(f"Response body: {response.text}")
                    response.raise_for_status()
                    
                result = response.json()
                
                task_id = result.get("task", {}).get("id")
                if not task_id:
                    print(f"Error: No task ID returned. Response: {result}")
                    return None
                
                print(f"Task submitted. ID: {task_id}")
                
            # 2. Poll for Result
            fetch_url = f"{base_url}/runway/task/{task_id}/fetch"
            
            max_retries = 60 # 5 minutes (5s * 60)
            for i in range(max_retries):
                time.sleep(5)
                print(f"Polling status... ({i+1}/{max_retries})")
                
                resp = requests.get(fetch_url, headers=headers)
                if resp.status_code != 200:
                    print(f"Poll failed: {resp.status_code} - {resp.text}")
                    continue
                    
                task_data = resp.json().get("task", {})
                status = task_data.get("status")
                
                if status == "SUCCEEDED":
                    artifacts = task_data.get("artifacts", [])
                    if artifacts and len(artifacts) > 0:
                        video_url = artifacts[0].get("url")
                        if video_url:
                            print(f"Video generated successfully: {video_url}")
                            # 3. Download Video
                            self._download_file(video_url, output_path)
                            return output_path
                    print("Task succeeded but no video URL found.")
                    return None
                    
                elif status in ["FAILED", "CANCELLED", "THROTTLED"]: # Throttled might need retry logic, but treating as fail for now
                    print(f"Task failed with status: {status}")
                    return None
                    
            print("Timeout waiting for video generation.")
            return None
            
        except Exception as e:
            print(f"Runway API error: {e}")
            return None

    def _download_file(self, url, output_path):
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(f"Downloaded video to {output_path}")
        except Exception as e:
            print(f"Failed to download video: {e}")

    def _generate_luma_video(self, image_path, prompt, output_path):
        """
        Generates video using Luma Dream Machine API (via 302.ai or compatible).
        """
        print("Calling Luma Dream Machine API...")
        
        base_url = self.base_url if self.base_url else "https://api.302.ai"
        if base_url.endswith("/"):
            base_url = base_url[:-1]
            
        # Endpoint for Luma on 302.ai
        submit_url = f"{base_url}/luma/submit"
        
        api_key = self.api_key
        if api_key.startswith("Bearer "):
            api_key = api_key.replace("Bearer ", "")
            
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        try:
            # Submit Task
            # We use multipart/form-data to upload the image directly
            print(f"Submitting task to {submit_url}")
            
            with open(image_path, 'rb') as img_file:
                files = {
                    'image_url': (os.path.basename(image_path), img_file) # 302.ai often maps file fields flexibly, trying 'image_url' as file or 'file'
                }
                # Note: Some proxies might require 'file' or 'image'. 
                # If 'image_url' as a file field doesn't work, we might need to try 'file'.
                # However, based on Runway implementation, we'll try to be consistent.
                # Let's try a safer approach: check if we can use a standard field name.
                # But for now, we'll assume the proxy handles file uploads if we send them.
                
                # Actually, for Luma specifically, if the API expects a URL string in JSON, 
                # and we send a file, the proxy needs to handle it.
                # Let's assume the user has a proxy that supports this, or we fallback.
                
                # Alternative: If we can't upload, we might need to fail or use mock.
                # But let's try the upload.
                
                data = {
                    'prompt': prompt if prompt else "animate this image",
                }
                
                # Note: If the provider is strictly official Luma, this won't work without a URL.
                # But since we are optimizing for the "Local Software" context, we assume the 
                # configured provider (likely 302.ai) supports file upload.
                
                response = requests.post(submit_url, headers=headers, files=files, data=data)
                
                if response.status_code != 200:
                    print(f"Luma Submit failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    # Fallback to Ken Burns if API fails
                    print("Falling back to local effect...")
                    return self._generate_ken_burns_video(image_path, output_path)
                    
                result = response.json()
                task_id = result.get("id") or result.get("task_id")
                
                if not task_id:
                    print(f"Error: No task ID returned. Response: {result}")
                    return self._generate_ken_burns_video(image_path, output_path)
                
                print(f"Luma Task submitted. ID: {task_id}")
                
            # Poll for Result
            fetch_url = f"{base_url}/luma/task/{task_id}/fetch"
            
            max_retries = 60 # 5 minutes
            for i in range(max_retries):
                time.sleep(5)
                print(f"Polling Luma status... ({i+1}/{max_retries})")
                
                resp = requests.get(fetch_url, headers=headers)
                if resp.status_code != 200:
                    continue
                    
                task_data = resp.json()
                status = task_data.get("status")
                
                if status == "succeeded" or status == "SUCCEEDED":
                    video_data = task_data.get("video")
                    video_url = None
                    if isinstance(video_data, dict):
                        video_url = video_data.get("url")
                    elif isinstance(video_data, str):
                        video_url = video_data
                        
                    if video_url:
                        print(f"Video generated successfully: {video_url}")
                        self._download_file(video_url, output_path)
                        return output_path
                        
                elif status in ["failed", "FAILED"]:
                    print(f"Luma task failed: {task_data}")
                    break
                    
            print("Luma generation timed out or failed.")
            return self._generate_ken_burns_video(image_path, output_path)

        except Exception as e:
            print(f"Luma API error: {e}")
            return self._generate_ken_burns_video(image_path, output_path)

    def _generate_ken_burns_video(self, image_path, output_path):
        """
        Uses FFmpeg to create a video with a 'Ken Burns' (slow zoom) effect.
        """
        time.sleep(1) # Simulate processing
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if not os.path.exists(image_path):
            print(f"Input image not found: {image_path}")
            return None
            
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            # Zoom in effect: zoom 1.0 -> 1.1 over 3 seconds (75 frames @ 25fps)
            # scale=trunc(iw/2)*2:trunc(ih/2)*2 ensures dimensions are even (required by some codecs)
            # format=yuv420p ensures compatibility
            
            filter_complex = "zoompan=z='min(zoom+0.0015,1.2)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1024x1024,scale=trunc(iw/2)*2:trunc(ih/2)*2"
            
            cmd = [
                ffmpeg_exe,
                "-y",
                "-i", image_path,
                "-c:v", "libx264",
                "-t", "4", # 4 seconds
                "-pix_fmt", "yuv420p",
                "-vf", filter_complex,
                output_path
            ]
            
            # Suppress output unless error
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return output_path
        except Exception as e:
            print(f"Video generation failed: {e}")
            # Do NOT create a dummy file, so the UI knows it failed
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except: pass
            return None
