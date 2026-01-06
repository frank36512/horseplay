import os
import requests
import base64
from openai import OpenAI
from core.config.config_manager import ConfigManager

class ImageGenClient:
    def __init__(self, api_key=None, base_url=None, model=None, provider=None):
        config = ConfigManager()
        key = api_key or os.environ.get("OPENAI_API_KEY") or config.get("OPENAI_API_KEY") or "sk-placeholder"
        self.api_key = key
        self.base_url = base_url
        
        # Fix base_url for OpenAI client if it contains the full path
        openai_base_url = base_url
        if base_url and "/images/generations" in base_url:
            openai_base_url = base_url.split("/images/generations")[0]
            
        self.client = OpenAI(
            api_key=key,
            base_url=openai_base_url,
            timeout=180.0,
            max_retries=1
        )
        self.model = model or "dall-e-3"
        self.provider = provider or "openai"

    def generate_image(self, prompt, output_path, ref_images=None, gen_settings=None, status_callback=None):
        """
        Generates an image and saves it to output_path.
        status_callback: Optional function to report status strings.
        """
        gen_settings = gen_settings or {}
        print(f"Generating image for: {prompt} using {self.model}")
        
        if status_callback: status_callback("正在初始化...")

        # Check if it's Google provider but NOT Comfly (Comfly uses OpenAI format)
        is_comfly = self.base_url and "comfly" in self.base_url
        if self.provider and self.provider.lower() == "google" and not is_comfly:
            return self._generate_google_image(prompt, output_path, gen_settings, ref_images, status_callback)

        if ref_images:
            print(f"Using reference images: {ref_images}")
        
        # Mock generation if key is placeholder
        if self.client.api_key == "sk-placeholder":
            return self._generate_mock_image(output_path, ref_images, gen_settings)

        try:
            full_prompt = prompt
            
            # 1. Handle Reference Images (Character Consistency)
            ref_image_base64_list = []
            if ref_images and len(ref_images) > 0:
                # Comfly/nano-banana supports multiple reference images via base64 array
                for ref_img in ref_images:
                    try:
                        base64_str = self._encode_image(ref_img)
                        ref_image_base64_list.append(base64_str)
                        print(f"Encoded reference image: {ref_img}")
                    except Exception as e:
                        print(f"Failed to encode reference image {ref_img}: {e}")
                
                if ref_image_base64_list:
                    # Add instruction to prompt for better adherence
                    full_prompt = f"Using the provided reference images as a base, {full_prompt}. Maintain the scene composition, character appearance, and style from the references."
                    print(f"Total reference images encoded: {len(ref_image_base64_list)}")
            
            # 2. Append settings to prompt
            if gen_settings.get("style") and gen_settings.get("style") != "None":
                # Only add style if no reference image (to avoid conflict)
                if not ref_image_base64_list:
                    full_prompt += f", style: {gen_settings.get('style')}"
                else:
                    print(f"Skipping style setting due to reference images presence")
            
            # Determine size based on aspect ratio
            size = "1024x1024"
            ratio = gen_settings.get("aspect_ratio", "16:9")
            resolution = gen_settings.get("resolution", "1080P")
            
            if ratio in ["16:9", "4:3"]:
                size = "1792x1024" # Landscape (Default 1080P-ish for DALL-E 3)
                if resolution == "720P" and self.model != "dall-e-3":
                     # If not DALL-E 3, we might try smaller size if supported
                     # But for safety, we stick to standard sizes or maybe 1280x720 if model allows
                     # For now, let's just log it.
                     pass
            elif ratio in ["9:16", "3:4"]:
                size = "1024x1792" # Portrait
            
            # Determine quality
            quality = gen_settings.get("quality", "standard")

            if status_callback: status_callback("正在请求API生成...")
            
            print("\n" + "="*50)
            print(" [DEBUG] OpenAI/Comfly API Request Payload ")
            print("="*50)
            print(f"Model:      {self.model}")
            print(f"Size:       {size} (Ratio: {ratio})")
            print(f"Resolution: {resolution}")
            print(f"Quality:    {quality}")
            print(f"RefImages:  {len(ref_image_base64_list)} images" if ref_image_base64_list else "RefImages:  None")
            print(f"Prompt:     {full_prompt}")
            print("="*50 + "\n")

            # Comfly needs direct HTTP request for custom parameters
            if is_comfly or "comfly" in str(self.base_url).lower() or self.model == "nano-banana":
                # Use direct HTTP request for Comfly
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model,
                    "prompt": full_prompt,
                    "aspect_ratio": ratio,
                    "n": 1,
                }
                
                if ref_image_base64_list:
                    payload["image"] = ref_image_base64_list
                
                url = f"{self.base_url}/images/generations" if not self.base_url.endswith("/images/generations") else self.base_url
                
                if status_callback: status_callback("正在请求Comfly API...")
                print(f"[DEBUG] Sending request to {url}")
                
                response = requests.post(url, headers=headers, json=payload, timeout=180)
                
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and len(data["data"]) > 0:
                        image_url = data["data"][0].get("url")
                        if image_url:
                            print(f"Got Image URL: {image_url}")
                            
                            if status_callback: status_callback("正在下载图片...")
                            try:
                                img_response = requests.get(image_url, timeout=120)
                                img_response.raise_for_status()
                                
                                with open(output_path, 'wb') as f:
                                    f.write(img_response.content)
                                # Return tuple (path, url) for retry capability
                                return (output_path, image_url)
                            except Exception as download_error:
                                print(f"[ERROR] Download failed: {download_error}")
                                # Return (None, url) so UI can save URL and show retry button
                                raise Exception(f"下载失败: {download_error}. URL: {image_url}")
                
                    raise Exception(f"Unexpected response format: {data}")
                else:
                    raise Exception(f"Comfly API Error: {response.status_code} - {response.text}")
            else:
                # Standard OpenAI format
                api_params = {
                    "model": self.model,
                    "prompt": full_prompt,
                    "size": size,
                    "quality": quality,
                    "n": 1,
                }
                
                if status_callback: status_callback("正在请求OpenAI API...")
                response = self.client.images.generate(**api_params)
                
                if status_callback: status_callback("正在解析响应...")
                
                image_url = response.data[0].url
                print(f"Got Image URL: {image_url}")
                
                if status_callback: status_callback("正在下载图片...")
                
                # Download with validation
                try:
                    img_response = requests.get(image_url, timeout=120)
                    img_response.raise_for_status() # Ensure we got a 200 OK
                    
                    with open(output_path, 'wb') as f:
                        f.write(img_response.content)
                    
                    # Return tuple (path, url) for retry capability    
                    return (output_path, image_url)
                except Exception as download_error:
                    print(f"[ERROR] Download failed: {download_error}")
                    # Raise with URL included so it can be extracted
                    raise Exception(f"下载失败: {download_error}. URL: {image_url}")
            
        except Exception as e:
            print(f"Image Gen Error: {e}")
            # Re-raise exception so UI thread can catch it
            raise e

    def retry_download_image(self, image_url, output_path):
        """
        Retry downloading an image from a saved URL.
        Useful when initial download timed out or failed.
        """
        print(f"[Retry] Downloading image from: {image_url}")
        try:
            img_response = requests.get(image_url, timeout=120)
            img_response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(img_response.content)
            
            print(f"[Retry] ✓ Image downloaded successfully")
            return output_path
        except Exception as e:
            print(f"[Retry] Error: {e}")
            return None

    def _generate_google_image(self, prompt, output_path, gen_settings, ref_images=None, status_callback=None):
        try:
            # Construct URL
            url = self.base_url
            if not url:
                raise Exception("Base URL is required for Google provider")
                
            if "{model}" in url:
                url = url.replace("{model}", self.model)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            full_prompt = prompt
            parts = []
            
            if status_callback: status_callback("正在处理参考图...")
            
            # 1. Handle Reference Images
            if ref_images and len(ref_images) > 0:
                for img_path in ref_images:
                    try:
                        b64_data = self._encode_image(img_path)
                        mime_type = "image/png"
                        if img_path.lower().endswith(".jpg") or img_path.lower().endswith(".jpeg"):
                            mime_type = "image/jpeg"
                        elif img_path.lower().endswith(".webp"):
                            mime_type = "image/webp"
                            
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_data
                            }
                        })
                    except Exception as e:
                        print(f"Failed to encode reference image {img_path}: {e}")

            # 2. Handle Style
            if gen_settings.get("style") and gen_settings.get("style") != "None":
                 full_prompt += f", style: {gen_settings.get('style')}"
            
            # Strengthen Reference Image Adherence
            if ref_images and len(ref_images) > 0:
                full_prompt = "Reference Image Compliance: HIGH. The generated image MUST strictly follow the visual appearance, clothing, and facial features of the character in the attached reference image(s). \n\n" + full_prompt

            # Add text prompt to parts
            parts.insert(0, {"text": full_prompt})

            # 3. Handle Aspect Ratio
            aspect_ratio = gen_settings.get("aspect_ratio", "1:1")
            resolution = gen_settings.get("resolution", "1080P")
            
            payload = {
                "contents": [
                    {
                        "parts": parts
                    }
                ],
                "generationConfig": {
                    "responseModalities": ["IMAGE"],
                    "aspectRatio": aspect_ratio
                }
            }
            
            # 302.ai specific query param for URL output
            params = {"response_format": "url"}
            
            if status_callback: status_callback("正在请求Google API...")
            
            print("\n" + "="*50)
            print(" [DEBUG] Google API Request Payload ")
            print("="*50)
            print(f"URL:        {url}")
            print(f"Model:      {self.model}")
            print(f"Ratio:      {aspect_ratio}")
            print(f"Resolution: {resolution}")
            print(f"Prompt:     {full_prompt}")
            print(f"RefImgs:    {len(ref_images) if ref_images else 0}")
            print("="*50 + "\n")
            
            response = requests.post(url, headers=headers, json=payload, params=params, timeout=180)
            
            if response.status_code == 200:
                if status_callback: status_callback("正在解析Google响应...")
                data = response.json()
                # Extract URL: candidates[0].content.parts[0].url
                if "candidates" in data and len(data["candidates"]) > 0:
                    parts = data["candidates"][0].get("content", {}).get("parts", [])
                    if parts and "url" in parts[0]:
                        image_url = parts[0]["url"]
                        print(f"Image URL: {image_url}")
                        
                        if status_callback: status_callback("正在下载图片...")
                        img_response = requests.get(image_url, timeout=120)
                        img_response.raise_for_status()
                        
                        with open(output_path, 'wb') as f:
                            f.write(img_response.content)
                        return output_path
                
                print(f"Unexpected response format: {data}")
                raise Exception(f"Unexpected response format: {data}")
            else:
                print(f"Google Image Gen Error: {response.text}")
                raise Exception(f"Google API Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Google Image Gen Exception: {e}")
            raise e

    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _analyze_ref_image(self, image_path):
        """
        Uses a Vision model (GPT-4o) to describe the reference image.
        """
        try:
            base64_image = self._encode_image(image_path)
            
            # Ensure we are using a model that supports vision
            vision_model = "gpt-4o" 
            
            # If self.client is configured for Google (REST URL), we can't use it for OpenAI Chat Completion.
            # We need a client configured for an LLM provider (OpenAI compatible).
            analysis_client = self.client
            
            # Check if current client is likely incompatible (e.g. Google REST URL)
            if "api.302.ai/v1/v1beta" in str(self.base_url):
                # Create a temporary client using config
                config = ConfigManager()
                # Try to find a valid LLM config
                llm_config = None
                for c in config.get("api_configs", []):
                    if c.get("type") == "LLM" and c.get("provider") == "openai":
                        llm_config = c
                        break
                
                if llm_config:
                    analysis_client = OpenAI(
                        api_key=llm_config["api_key"],
                        base_url=llm_config["base_url"]
                    )
                else:
                    # Fallback to env vars or default config
                    key = os.environ.get("OPENAI_API_KEY") or config.get("OPENAI_API_KEY")
                    if key:
                        analysis_client = OpenAI(api_key=key)
                    else:
                        print("Warning: No OpenAI compatible client found for image analysis.")
                        return None

            response = analysis_client.chat.completions.create(
                model=vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe the character in this image in detail. Focus on physical features (hair color/style, eye color, skin tone, age), clothing (style, colors, specific items), and distinctive accessories. Keep the description precise and visual."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error analyzing reference image: {e}")
            # Fallback: return None so we just use the original prompt
            return None

    def _generate_mock_image(self, output_path, ref_images=None, gen_settings=None):
        # Create a simple colored placeholder image using Pillow
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        import random
        
        gen_settings = gen_settings or {}
        
        img = Image.new('RGB', (1024, 1024), color=(random.randint(0, 50), random.randint(0, 50), random.randint(0, 50)))
        
        if ref_images:
             # Use the first reference image as the base composition
             try:
                 ref = Image.open(ref_images[0]).convert('RGB')
                 # Resize to cover
                 ref = ref.resize((1024, 1024))
                 # Apply a slight blur to simulate "generation variation"
                 img = ref.filter(ImageFilter.GaussianBlur(2))
                 
                 # If multiple refs, maybe composite them (simple logic for now)
                 if len(ref_images) > 1:
                     ref2 = Image.open(ref_images[1]).convert('RGB').resize((300, 300))
                     img.paste(ref2, (700, 700))
                     
             except Exception as e:
                 print(f"Mock ref load failed: {e}")
                 pass

        d = ImageDraw.Draw(img)
        d.text((50, 50), "AI Generated Scene", fill=(255, 255, 255))
        if ref_images:
            d.text((50, 100), "Character Consistency Applied", fill=(0, 255, 0))
            
        # Draw settings
        y = 150
        if gen_settings:
            d.text((50, y), f"Style: {gen_settings.get('style', 'None')}", fill=(200, 200, 200))
            y += 30
            d.text((50, y), f"Steps: {gen_settings.get('steps', 30)}", fill=(200, 200, 200))
            y += 30
            d.text((50, y), f"CFG: {gen_settings.get('cfg_scale', 7.0)}", fill=(200, 200, 200))
        
        img.save(output_path)
        return output_path
