import os
import requests
import json
import time
import base64

class VeoService:
    def __init__(self, api_key, base_url, extra_config=None):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        # Extra provider-specific configuration passed from the caller (VideoGenClient)
        # e.g. {"duration": 10, "hd": true, "watermark": false, "notify_hook": "https://..."}
        self.extra_config = extra_config or {}
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _post(self, endpoint, payload):
        # Handle 302.ai style URLs where base_url is the full endpoint
        # Also handle Comfly style URLs ending in /generations
        # And Google Vertex AI URLs
        if (("submit" in self.base_url or self.base_url.endswith("/generations") or "googleapis.com" in self.base_url) and 
            (endpoint.startswith("video/") or endpoint.startswith("v2/videos/") or endpoint == "google_predict")):
             # If base_url is a full endpoint, use it directly
             url = self.base_url
        else:
             url = f"{self.base_url}/{endpoint}"
             
        # Handle Google API Key if using generativelanguage.googleapis.com
        if "generativelanguage.googleapis.com" in url:
            if "key=" not in url:
                url += f"?key={self.api_key}"
            # Remove Authorization header as we are using API Key in query param
            if "Authorization" in self.headers:
                del self.headers["Authorization"]

        print(f"Veo Request URL: {url}")
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Veo API Error ({endpoint}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None

    def _download_file(self, url, output_path):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        print(f"[Download] Starting download from: {url}")
        print(f"[Download] Output path: {output_path}")
        try:
            # Try standard download first
            with requests.get(url, stream=True, headers=headers, timeout=120) as r:
                r.raise_for_status()
                print(f"[Download] Status: {r.status_code}, Content-Type: {r.headers.get('content-type')}")
                
                # Check if content is actually a video
                content_type = r.headers.get('content-type', '')
                if 'video' not in content_type and 'octet-stream' not in content_type:
                    print(f"[WARNING] Unexpected content type: {content_type}")
                    # Read response for debugging
                    content = r.content
                    print(f"[DEBUG] Response content (first 500 chars): {content[:500]}")
                    return None
                
                file_size = 0
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        file_size += len(chunk)
                
                print(f"[Download] ✓ Downloaded {file_size} bytes")
                
                # Validate file size
                if file_size < 1000:
                    print(f"[ERROR] Downloaded file is too small ({file_size} bytes), likely invalid")
                    return None
                    
            return output_path
        except Exception as e:
            print(f"[Download] Error: {e}")
            return None

    def generate_scene(self, image_path, text, voice_id, prompt, sfx_prompt=None, output_path=None, model="veo-3.1", aspect_ratio="9:16", voice_description=None, language="English", end_image_path=None, input_video_path=None):
        """
        Generates a full scene (Video + Audio + LipSync + SFX) in one call using Veo 3.1.
        Constructs a rich prompt including dialogue and visual description.
        """
        # 302.ai / Veo 3.1 Endpoint
        # If base_url is the submit URL, we use it. Otherwise we default to a standard endpoint.
        # But for 302.ai, the user likely configured the full submit URL.
        endpoint = "video/generate" 
        
        # Construct Rich Prompt for Veo 3.1
        # Best Practice: [Visual Description]. [Character] says, "[Dialogue]". [SFX].
        
        full_prompt = prompt.strip()
        if not full_prompt.endswith('.'):
            full_prompt += "."
            
        if text:
            # Add dialogue instruction
            # We specify language to guide the TTS/LipSync model
            voice_part = f" with a {voice_description}" if voice_description else ""
            full_prompt += f' The character speaks in {language}{voice_part}, saying: "{text}"'
        
        if sfx_prompt:
            full_prompt += f". Audio atmosphere: {sfx_prompt}"

        # Disable embedded subtitles to avoid garbled text.
        # We will handle subtitles in the final synthesis stage locally.
        
        # Check if using Comfly API (v2 format) or Sora models
        is_comfly = ("comfly" in self.base_url.lower() or 
                     model in ["veo3-pro-frames", "veo2-fast-frames", "veo2-fast-components"] or
                     "sora" in model.lower())
        
        if is_comfly:
            # Use Comfly v2/videos/generations format
            return self._generate_scene_comfly(image_path, text, voice_id, prompt, output_path, model, aspect_ratio, language, end_image_path, input_video_path)
        
        # Legacy 302.ai format
        payload = {
            "model": model,
            "prompt": full_prompt,
            "enhance_prompt": True,
            "subtitle_mode": "none", 
            "enable_subtitles": False,
            "aspect_ratio": aspect_ratio,
            "generation_config": {
                "subtitle_mode": "none",
                "audio_sample_rate": 44100, # Standardize audio output
                "audio_bitrate": 320000
            }
        }
        
        # Handle Images (Start and Optional End)
        images_list = []
        
        # 1. Start Image
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = os.path.splitext(image_path)[1].lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    data_uri = f"data:{mime};base64,{b64_string}"
                    images_list.append(data_uri)
            except Exception as e:
                print(f"Error encoding start image: {e}")

        # 2. End Image (Optional)
        if end_image_path and os.path.exists(end_image_path):
            try:
                with open(end_image_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = os.path.splitext(end_image_path)[1].lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    data_uri = f"data:{mime};base64,{b64_string}"
                    images_list.append(data_uri)
                    print(f"Added end frame from {end_image_path}")
            except Exception as e:
                print(f"Error encoding end image: {e}")

        if images_list:
            # 302.ai / Veo usually accepts "images" list for start/end frames
            payload["images"] = images_list
            # Fallback for single image endpoints
            if len(images_list) > 0:
                payload["image_url"] = images_list[0]
            if len(images_list) > 1:
                payload["end_image_url"] = images_list[1] # Some endpoints might use this key

        # Input Video (for extension)
        if input_video_path and os.path.exists(input_video_path):
            try:
                with open(input_video_path, "rb") as vid_file:
                    b64_string = base64.b64encode(vid_file.read()).decode('utf-8')
                    ext = os.path.splitext(input_video_path)[1].lower()
                    mime = "video/mp4" # Assume mp4
                    payload["video_url"] = f"data:{mime};base64,{b64_string}"
            except Exception as e:
                print(f"Error encoding input video: {e}")

        print(f"Calling Veo Scene API with prompt: {full_prompt[:100]}... Ratio: {aspect_ratio}")
        result = self._post(endpoint, payload)
        print(f"Veo Submit Result: {result}") # Debug print
        
        if result:
            # 302.ai returns {"data": { "id": "..." }} or {"data": "id"} or {"id": "..."}
            task_id = None
            if "data" in result:
                if isinstance(result["data"], dict):
                    task_id = result["data"].get("id")
                else:
                    task_id = result["data"]
            
            if not task_id:
                task_id = result.get("id") or result.get("task_id")
            
            if task_id:
                # If base_url ends with /generations, we use _poll_task_v2 logic which handles .../generations/{id}
                if self.base_url.endswith("/generations"):
                     return self._poll_task_v2(task_id, output_path)
                return self._poll_task(task_id, output_path)
            elif "url" in result:
                if output_path:
                    return self._download_file(result["url"], output_path)
                return result["url"]
        
        return None

    def _generate_scene_comfly(self, image_path, text, voice_id, prompt, output_path, model, aspect_ratio, language, end_image_path, input_video_path):
        """
        Generate scene using Comfly v2/videos/generations API with Veo 3.1.
        Veo 3.1 supports automatic audio generation with three types:
        1. Dialogue (对话): Use quotes, e.g., "This must be the key," he said in a low voice
        2. Sound Effects (音效/SFX): Describe sounds explicitly, e.g., The tires emit a harsh scream
        3. Ambient Noise (环境噪声): Describe soundscape, e.g., A faint and distant noise echoes in the background
        """
        # Comfly uses simpler format - just prompt, images, and basic settings
        images = []
        
        # Start Image
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = os.path.splitext(image_path)[1].lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    images.append(f"data:{mime};base64,{b64_string}")
            except Exception as e:
                print(f"Error encoding start image: {e}")

        # End Image (for veo2-fast-frames which supports 2 frames)
        if end_image_path and os.path.exists(end_image_path) and model == "veo2-fast-frames":
            try:
                with open(end_image_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = os.path.splitext(end_image_path)[1].lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    images.append(f"data:{mime};base64,{b64_string}")
                    print(f"Added end frame for veo2-fast-frames")
            except Exception as e:
                print(f"Error encoding end image: {e}")
        
        # Construct enhanced prompt following Veo 3 audio guidelines
        full_prompt = prompt.strip()
        if not full_prompt.endswith('.'):
            full_prompt += "."
        
        # Add dialogue if provided
        # Veo 3 format: "dialogue text," character says/whispers/shouts
        if text:
            full_prompt += f' "{text}," the character says.'
            print(f"[Comfly Veo 3.1] Adding dialogue: {text[:50]}...")
        
        # Note: SFX and ambient noise from video_params['audio'] are already in the prompt
        # They were added by construct_video_prompt() in the format:
        # - Audio: [description of sounds/ambient noise]
        # Veo 3 will automatically generate these sounds based on the descriptions
        
        # Construct endpoint
        if self.base_url.endswith("/generations"):
            endpoint = "v2/videos/generations"
        elif "comfly" in self.base_url and not self.base_url.endswith("/generations"):
            endpoint = "v2/videos/generations"
        else:
            endpoint = "v2/videos/generations"
        
        payload = {
            "prompt": full_prompt,
            "model": model,
            "enhance_prompt": True,  # Enable auto-translation, optimization, and audio generation
            "images": images,
            "aspect_ratio": aspect_ratio
        }

        # Include provider-specific options if provided via extra_config (Sora2/Comfly supports these)
        # Accept common keys: duration, hd, watermark, private, notify_hook, fps
        try:
            for k in ["duration", "hd", "watermark", "private", "notify_hook", "fps"]:
                if k in self.extra_config and self.extra_config.get(k) is not None:
                    payload[k] = self.extra_config.get(k)
        except Exception as e:
            print(f"[DEBUG] Ignoring extra_config merge error: {e}")
        
        print(f"[Comfly Veo 3.1] Calling v2/videos/generations")
        print(f"[Comfly Veo 3.1] Model: {model}, enhance_prompt: True (auto-audio enabled)")
        print(f"[Comfly Veo 3.1] Full Prompt: {full_prompt[:150]}...")
        print(f"[Comfly Veo 3.1] Images: {len(images)} frame(s), Aspect: {aspect_ratio}")
        
        result = self._post(endpoint, payload)
        
        print(f"[DEBUG] Comfly API Response: {result}")
        
        if result:
            # Check for task_id in different possible locations
            task_id = None
            if "task_id" in result:
                task_id = result["task_id"]
            elif "data" in result:
                if isinstance(result["data"], dict) and "task_id" in result["data"]:
                    task_id = result["data"]["task_id"]
                elif isinstance(result["data"], str):
                    task_id = result["data"]
            
            if task_id:
                print(f"[Comfly Veo 3.1] Got task_id: {task_id}")
                video_path = self._poll_task_v2(task_id, output_path)
                
                if video_path:
                    if text:
                        print(f"[Comfly Veo 3.1] ✓ Video generated with automatic dialogue audio")
                    else:
                        print(f"[Comfly Veo 3.1] ✓ Video generated (ambient/SFX audio only)")
                
                # Return both video_path and task_id for retry capability
                return (video_path, task_id)
            else:
                print(f"[ERROR] No task_id found in response: {result}")
        else:
            print(f"[ERROR] API request failed, no response")
            
        return (None, None)

    def retry_fetch_video(self, task_id, output_path):
        """
        Retry fetching a video using a previously saved task_id.
        This is useful when the initial fetch timed out but the video generation succeeded.
        """
        print(f"[Retry] Attempting to fetch video for task_id: {task_id}")
        return self._poll_task_v2(task_id, output_path)

    def _generate_video_google(self, prompt, image_url, image_path, output_path, model, aspect_ratio):
        # Map friendly model name to Google API model name
        google_model = model
        if model == "veo-3.1":
            google_model = "veo-3.1-generate-preview"
        
        # Construct Vertex AI / Gemini payload
        # This is a best-effort implementation for Google's official API formats
        
        # 1. Try Vertex AI "instances" format (Standard for Google Cloud Models)
        instance = {"prompt": prompt}
        
        if image_path and os.path.exists(image_path):
             try:
                 with open(image_path, "rb") as f:
                     b64_data = base64.b64encode(f.read()).decode("utf-8")
                     instance["image"] = {"bytesBase64Encoded": b64_data}
             except Exception as e:
                 print(f"Error encoding image for Google API: {e}")

        payload = {
            "instances": [instance],
            "parameters": {
                "aspectRatio": aspect_ratio,
                "sampleCount": 1
            }
        }
        
        # If using Gemini API (generativelanguage), format is different
        # However, veo-3.1:predict might use 'instances' even on generativelanguage
        # Let's try to stick to 'instances' if the endpoint is :predict
        if "generativelanguage" in self.base_url and ":predict" not in self.base_url:
             # If it's not explicitly :predict, maybe it's generateContent? 
             # But for Veo we know it's predict or predictLongRunning.
             pass

        print(f"Calling Google Veo API ({google_model}): {prompt[:50]}...")
        
        # Determine endpoint method
        method = "predict"
        if "veo" in google_model:
            method = "predictLongRunning"
            
        # Construct URL if base_url is just the root
        if "models/" not in self.base_url:
             endpoint = f"models/{google_model}:{method}"
        else:
             # If base_url already has model, just append method if missing
             if not self.base_url.endswith(f":{method}"):
                 # Replace existing method or append
                 if ":predict" in self.base_url:
                     endpoint = self.base_url.replace(":predict", f":{method}")
                 else:
                     endpoint = f"{self.base_url}:{method}"
                 # We need to handle the case where _post expects a relative endpoint or full URL
                 # _post logic: if base_url has googleapis.com, it uses it directly.
                 # So we should update self.base_url or pass the full URL to _post?
                 # _post takes 'endpoint'. If we pass "google_predict", it uses base_url.
                 # Let's update base_url temporarily or pass a special marker.
                 pass
             endpoint = "google_predict" # Marker for _post to use base_url (but we might need to update it)

        # Actually, let's just construct the full URL and pass it to _post if we can, 
        # but _post logic is a bit rigid. 
        # Let's rely on _post using self.base_url if it contains googleapis.com.
        # We need to ensure self.base_url is correct.
        
        # If the user provided a base_url like .../models/veo-3.1:predict, we need to change it to .../models/veo-3.1-generate-preview:predictLongRunning
        current_url = self.base_url
        if "veo-3.1:predict" in current_url:
            current_url = current_url.replace("veo-3.1:predict", f"{google_model}:{method}")
        elif "veo-3.1" in current_url and method not in current_url:
             # Append method
             current_url = f"{current_url}:{method}"
        
        # Temporarily swap base_url for this request
        original_base_url = self.base_url
        self.base_url = current_url
        
        try:
            result = self._post("google_predict", payload)
        finally:
            self.base_url = original_base_url
        
        if result:
            print(f"Google API Response: {json.dumps(result, indent=2)}")
            
            # Handle Long Running Operation
            if "name" in result and ("operations" in result["name"] or "models" in result["name"]):
                return self._poll_google_operation(result["name"], output_path)

            # Handle Vertex AI Response (Immediate)
            predictions = result.get("predictions")
            if predictions and len(predictions) > 0:
                pred = predictions[0]
                if isinstance(pred, dict):
                    if "bytesBase64Encoded" in pred:
                        video_data = base64.b64decode(pred["bytesBase64Encoded"])
                        if output_path:
                            with open(output_path, "wb") as f:
                                f.write(video_data)
                            return output_path
                    elif "gcsUri" in pred:
                        return pred["gcsUri"] # Return GCS URI if we can't download it easily
            
        return None

    def _poll_google_operation(self, operation_name, output_path):
        print(f"Polling Google Operation: {operation_name}")
        # Operation name is like "projects/.../operations/..." or "operations/..."
        # We need to construct the poll URL.
        # If using generativelanguage, it's https://generativelanguage.googleapis.com/v1beta/{operation_name}
        
        root_url = "https://generativelanguage.googleapis.com/v1beta"
        if "aiplatform" in self.base_url:
             # Extract root from base_url (e.g. https://us-central1-aiplatform.googleapis.com/v1)
             # Simple heuristic: split by /projects/
             root_url = self.base_url.split("/projects/")[0] + "/v1"
        
        poll_url = f"{root_url}/{operation_name}"
        if "key=" not in poll_url and "generativelanguage" in poll_url:
             poll_url += f"?key={self.api_key}"
             
        for i in range(60): # Poll for 5 minutes (5s interval)
            try:
                # Remove Auth header if using API Key
                headers = self.headers.copy()
                if "key=" in poll_url and "Authorization" in headers:
                    del headers["Authorization"]
                    
                response = requests.get(poll_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("done"):
                        if "error" in data:
                            print(f"Operation failed: {data['error']}")
                            return None
                        
                        # Success
                        print("Operation done. Extracting result...")
                        # Result is usually in response.result or response
                        # For Veo, it might be in 'response' -> 'result' -> 'videos' ?
                        # Let's dump it to see
                        # print(json.dumps(data, indent=2))
                        
                        # Try to find video bytes or URI
                        # Structure might be: { "response": { "@type": "...", "videos": [ ... ] } }
                        res = data.get("response", {})
                        # Check for video bytes
                        # This part depends on the specific response schema of Veo 3.1
                        # Assuming it returns a GCS URI or Base64
                        
                        # If we can't find it easily, return the whole response for now
                        # But let's try to find 'bytesBase64Encoded' or 'uri'
                        
                        # Common patterns:
                        # 1. response.videos[0].uri
                        # 2. response.result.videos[0]...
                        
                        # Let's look for any string starting with "gs://" or "https://"
                        # Or just return the raw data if we can't parse
                        return str(res) 
                        
                    else:
                        print(f"Operation status: Running... ({i})")
                else:
                    print(f"Poll error: {response.status_code}")
            except Exception as e:
                print(f"Poll exception: {e}")
            
            time.sleep(5)
            
        return None

    def generate_video(self, prompt, image_url=None, image_path=None, output_path=None, model="veo-3.1", aspect_ratio="9:16", end_image_path=None, input_video_path=None):
        """
        Generates a video from text or image.
        """
        # Check for Google Official API
        if "googleapis.com" in self.base_url:
            return self._generate_video_google(prompt, image_url, image_path, output_path, model, aspect_ratio)

        # Check for Comfly API (force V2 logic if comfly is in URL or sora model)
        if "comfly" in self.base_url or model in ["veo3-pro-frames", "veo2-fast-frames", "veo2-fast-components"] or "sora" in model.lower():
            return self._generate_video_v2(prompt, image_url, image_path, output_path, model, aspect_ratio, end_image_path)

        endpoint = "video/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio
        }
        
        images_list = []
        
        # Start Image
        if image_url:
            images_list.append(image_url)
        elif image_path and os.path.exists(image_path):
            try:
                with open(image_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = os.path.splitext(image_path)[1].lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    images_list.append(f"data:{mime};base64,{b64_string}")
            except Exception as e:
                print(f"Error encoding start image: {e}")

        # End Image
        if end_image_path and os.path.exists(end_image_path):
            try:
                with open(end_image_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = os.path.splitext(end_image_path)[1].lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    images_list.append(f"data:{mime};base64,{b64_string}")
            except Exception as e:
                print(f"Error encoding end image: {e}")

        if images_list:
            payload["images"] = images_list
            if len(images_list) > 0:
                payload["image_url"] = images_list[0]
            if len(images_list) > 1:
                payload["end_image_url"] = images_list[1]

        # Input Video (for extension)
        if input_video_path and os.path.exists(input_video_path):
            try:
                with open(input_video_path, "rb") as vid_file:
                    b64_string = base64.b64encode(vid_file.read()).decode('utf-8')
                    ext = os.path.splitext(input_video_path)[1].lower()
                    mime = "video/mp4" # Assume mp4
                    payload["video_url"] = f"data:{mime};base64,{b64_string}"
            except Exception as e:
                print(f"Error encoding input video: {e}")

        print(f"Calling Veo Video API: {prompt[:50]}...")
        result = self._post(endpoint, payload)
        
        if result and "url" in result:
            if output_path:
                return self._download_file(result["url"], output_path)
            return result["url"]
        elif result and "id" in result:
            task_id = result["id"]
            return self._poll_task(task_id, output_path)
            
        return None

    def _generate_video_v2(self, prompt, image_url, image_path, output_path, model, aspect_ratio, end_image_path):
        # Handle Comfly endpoint logic
        if "comfly" in self.base_url and not self.base_url.endswith("/generations"):
             # If base_url is just the domain, append the correct path
             endpoint = "v2/videos/generations"
        elif self.base_url.endswith("/generations"):
             # If base_url is already the full endpoint, use it directly (handled by _post)
             endpoint = "v2/videos/generations" # _post will ignore this if base_url is full
        else:
             endpoint = "v2/videos/generations"
        
        images = []
        # Handle Start Image
        if image_url:
            images.append(image_url)
        elif image_path and os.path.exists(image_path):
            try:
                with open(image_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = os.path.splitext(image_path)[1].lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    images.append(f"data:{mime};base64,{b64_string}")
            except Exception as e:
                print(f"Error encoding start image: {e}")

        # Handle End Image (only for supported models)
        if end_image_path and os.path.exists(end_image_path):
             try:
                with open(end_image_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = os.path.splitext(end_image_path)[1].lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    images.append(f"data:{mime};base64,{b64_string}")
             except Exception as e:
                print(f"Error encoding end image: {e}")

        payload = {
            "prompt": prompt,
            "model": model,
            "enhance_prompt": True,  # Enable auto-translation and optimization
            "images": images,
            "aspect_ratio": aspect_ratio
        }

        # Merge optional provider fields (duration, hd, watermark, private, notify_hook, fps)
        try:
            for k in ["duration", "hd", "watermark", "private", "notify_hook", "fps"]:
                if k in self.extra_config and self.extra_config.get(k) is not None:
                    payload[k] = self.extra_config.get(k)
        except Exception as e:
            print(f"[DEBUG] Ignoring extra_config merge error (v2): {e}")
        
        print(f"[Veo V2] Calling v2/videos/generations with model={model}")
        print(f"[Veo V2] enhance_prompt=True (auto-translate enabled)")
        print(f"[Veo V2] Prompt: {prompt[:100]}...")
        print(f"[Veo V2] Images: {len(images)} frame(s), Aspect: {aspect_ratio}")
        result = self._post(endpoint, payload)
        
        if result and "task_id" in result:
            return self._poll_task_v2(result["task_id"], output_path)
            
        return None

    def _poll_task_v2(self, task_id, output_path=None, max_retries=60, interval=5):
        # Handle URL construction
        if self.base_url.endswith("/generations"):
             url = f"{self.base_url}/{task_id}"
        else:
             endpoint = f"v2/videos/generations/{task_id}"
             url = f"{self.base_url}/{endpoint}"
        
        print(f"[Poll] Starting to poll task: {task_id}")
        print(f"[Poll] URL: {url}")
        
        for i in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    
                    print(f"[Poll] Attempt {i+1}/{max_retries}")
                    print(f"[Poll] Response: {json.dumps(data, indent=2)}")
                    
                    # Comfly Response Format: {"data": {"status": "SUCCESS", "output": "url"}}
                    status = None
                    video_url = None
                    
                    # Check top level status
                    status = data.get("status") or data.get("state")
                    
                    # Check nested data status (Comfly)
                    if not status and "data" in data and isinstance(data["data"], dict):
                        status = data["data"].get("status")
                        video_url = data["data"].get("output")
                    
                    print(f"[Poll] Status: {status}, Video URL: {video_url[:50] if video_url else 'None'}...")

                    if status in ["SUCCEEDED", "COMPLETED", "succeeded", "completed", "SUCCESS"]:
                        if not video_url:
                             video_url = data.get("video_url") or data.get("url") or (data.get("videos")[0]["url"] if data.get("videos") else None)
                        
                        # Check Comfly data.output if still not found
                        if not video_url and "data" in data and isinstance(data["data"], dict):
                            video_url = data["data"].get("output")

                        if video_url:
                            print(f"[Poll] ✓ Task completed! Video URL: {video_url}")
                            if output_path:
                                return self._download_file(video_url, output_path)
                            return video_url
                        else:
                            print(f"[Poll ERROR] Task succeeded but no video URL found")
                            print(f"[Poll ERROR] Full response: {json.dumps(data, indent=2)}")
                            return None
                    elif status in ["FAILED", "failed", "FAILURE"]:
                        print(f"[Poll ERROR] Task failed: {data}")
                        return None
                    elif status in ["PROCESSING", "processing", "PENDING", "pending", "IN_PROGRESS"]:
                        print(f"[Poll] Task still processing... waiting {interval}s")
                    else:
                        print(f"[Poll WARNING] Unknown status: {status}")
                else:
                    print(f"[Poll ERROR] HTTP {response.status_code}: {response.text[:200]}")
            except Exception as e:
                print(f"[Poll ERROR] Exception: {e}")
                import traceback
                traceback.print_exc()
                
            time.sleep(interval)
        
        print(f"[Poll ERROR] Timeout after {max_retries} attempts")
        return None

    def generate_audio(self, text, voice_id, output_path=None, model="veo-audio-3.1", language=None, prompt=None):
        """
        Generates speech from text.
        """
        endpoint = "audio/generate"
        payload = {
            "model": model,
            "text": text,
            "voice_id": voice_id
        }
        
        if language:
            payload["language"] = language
            
        if prompt:
            payload["prompt"] = prompt
        
        print(f"Calling Veo Audio API: {text[:50]}... (Lang: {language})")
        result = self._post(endpoint, payload)
        
        if result and "url" in result:
            if output_path:
                return self._download_file(result["url"], output_path)
            return result["url"]
        
        return None

    def generate_sfx(self, prompt, output_path=None, duration=5.0):
        """
        Generates sound effects from text.
        """
        endpoint = "audio/sfx"
        payload = {
            "prompt": prompt,
            "duration": duration
        }
        
        print(f"Calling Veo SFX API: {prompt[:50]}...")
        result = self._post(endpoint, payload)
        
        if result and "url" in result:
            if output_path:
                return self._download_file(result["url"], output_path)
            return result["url"]
        
        return None

    def sync_lips(self, video_url, audio_url, output_path=None):
        """
        Syncs video lips to audio.
        """
        endpoint = "video/lipsync"
        payload = {
            "video_url": video_url,
            "audio_url": audio_url
        }
        
        print(f"Calling Veo LipSync API...")
        result = self._post(endpoint, payload)
        
        if result and "url" in result:
            if output_path:
                return self._download_file(result["url"], output_path)
            return result["url"]
        elif result and "id" in result:
             return self._poll_task(result["id"], output_path)
        
        return None

    def generate_subtitles(self, audio_url, output_path=None):
        """
        Generates subtitles (SRT) from audio.
        """
        endpoint = "audio/transcribe"
        payload = {
            "audio_url": audio_url,
            "format": "srt"
        }
        
        print(f"Calling Veo Subtitle API...")
        result = self._post(endpoint, payload)
        
        if result and "text" in result:
            # If it returns text content directly
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result["text"])
                return output_path
            return result["text"]
        elif result and "url" in result:
            if output_path:
                return self._download_file(result["url"], output_path)
            return result["url"]
            
        return None

    def _poll_task(self, task_id, output_path=None, max_retries=60, interval=2):
        """
        Polls for task completion.
        """
        from urllib.parse import urlparse
        
        urls_to_try = []
        
        # Handle 302.ai style fetch URL
        if "submit" in self.base_url:
            # Strategy 0: Direct append (Documentation style: .../submit/veo3-v2/{task_id})
            urls_to_try.append(f"{self.base_url}/{task_id}")

            # Strategy 1: Replace /submit/xxx with /task/{id}/fetch
            if "/submit/" in self.base_url:
                base_root = self.base_url.split("/submit/")[0]
                urls_to_try.append(f"{base_root}/task/{task_id}/fetch")
            
            # Strategy 2: Use domain root + /task/{id}/fetch
            parsed = urlparse(self.base_url)
            domain_root = f"{parsed.scheme}://{parsed.netloc}"
            urls_to_try.append(f"{domain_root}/task/{task_id}/fetch")
            
            # Strategy 3: Use domain root + /302/task/{id}/fetch (Common 302 pattern)
            urls_to_try.append(f"{domain_root}/302/task/{task_id}/fetch")

            # Strategy 4: Try without /fetch (some endpoints use just /task/{id})
            urls_to_try.append(f"{base_root}/task/{task_id}")
            urls_to_try.append(f"{domain_root}/task/{task_id}")
        else:
            endpoint = f"tasks/{task_id}"
            urls_to_try.append(f"{self.base_url}/{endpoint}")
            
        # Deduplicate
        urls_to_try = list(dict.fromkeys(urls_to_try))
        
        active_url = urls_to_try[0]
        print(f"Polling Veo task {task_id}. Initial URL: {active_url}")
        
        for i in range(max_retries):
            try:
                response = requests.get(active_url, headers=self.headers, timeout=30)
                
                # If 404 or 500, try switching to next URL strategy
                if response.status_code in [404, 500]:
                    print(f"Poll {response.status_code} at {active_url}")
                    current_idx = urls_to_try.index(active_url)
                    if current_idx + 1 < len(urls_to_try):
                        active_url = urls_to_try[current_idx + 1]
                        print(f"Switching poll URL to: {active_url}")
                        continue # Retry immediately with new URL
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    
                    # Comfly support: Check nested data status
                    if not status and "data" in data and isinstance(data["data"], dict):
                        status = data["data"].get("status")

                    print(f"Poll status: {status}") # Debug
                    
                    if status in ["succeeded", "completed", "SUCCEEDED", "SUCCESS"]:
                        print(f"DEBUG: Full Task Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                        
                        # Check for subtitles
                        subtitle_url = data.get("subtitleUrl") or data.get("subtitle_url")
                        if not subtitle_url and "output" in data and isinstance(data["output"], dict):
                            subtitle_url = data["output"].get("subtitleUrl") or data["output"].get("subtitle_url")
                        
                        if subtitle_url and output_path:
                            srt_path = os.path.splitext(output_path)[0] + ".srt"
                            print(f"Downloading subtitles to {srt_path}")
                            self._download_file(subtitle_url, srt_path)

                        # ... (Success handling logic) ...
                        result_url = None
                        if "videoUrl" in data:
                             result_url = data["videoUrl"]
                        elif "url" in data: 
                             result_url = data["url"]
                        elif "output" in data and isinstance(data["output"], dict) and "url" in data["output"]: # 302.ai sometimes uses output.url
                             result_url = data["output"]["url"]
                        elif "result" in data and "url" in data["result"]:
                             result_url = data["result"]["url"]
                        elif "videos" in data and len(data["videos"]) > 0:
                             result_url = data["videos"][0]["url"]
                        elif "data" in data and isinstance(data["data"], dict) and "output" in data["data"]: # Comfly
                             result_url = data["data"]["output"]
                             
                        if result_url:
                             if output_path:
                                 return self._download_file(result_url, output_path)
                             return result_url
                        else:
                            print(f"Task succeeded but no URL found in: {data}")
                            
                    elif status in ["failed", "FAILED"]:
                        print(f"Veo task failed: {data.get('error')}")
                        return None
                else:
                    print(f"Poll error: {response.status_code} at {active_url}")
            except Exception as e:
                print(f"Poll exception: {e}")
            
            time.sleep(interval)
            
        print("Veo task timed out.")
        return None
