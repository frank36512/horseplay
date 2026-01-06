import json
import os
import time
import requests
import uuid

class ComfyUIService:
    def __init__(self, base_url="http://127.0.0.1:8188"):
        self.base_url = base_url.rstrip('/')
        self.client_id = str(uuid.uuid4())

    def upload_image(self, image_path, subfolder=""):
        """
        Uploads an image to ComfyUI.
        """
        url = f"{self.base_url}/upload/image"
        
        try:
            with open(image_path, 'rb') as f:
                files = {'image': (os.path.basename(image_path), f)}
                data = {}
                if subfolder:
                    data['subfolder'] = subfolder
                    
                response = requests.post(url, files=files, data=data)
                response.raise_for_status()
                
                result = response.json()
                # Returns: {"name": "filename.png", "subfolder": "", "type": "input"}
                return result
        except Exception as e:
            print(f"ComfyUI Upload Error: {e}")
            return None

    def queue_prompt(self, workflow):
        """
        Queues a workflow (prompt) to ComfyUI.
        """
        url = f"{self.base_url}/prompt"
        payload = {
            "prompt": workflow,
            "client_id": self.client_id
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json() # {"prompt_id": "..."}
        except Exception as e:
            print(f"ComfyUI Queue Error: {e}")
            return None

    def get_history(self, prompt_id):
        url = f"{self.base_url}/history/{prompt_id}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"ComfyUI History Error: {e}")
            return None

    def get_image(self, filename, subfolder, folder_type):
        url = f"{self.base_url}/view"
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"ComfyUI View Error: {e}")
            return None

    def generate_video(self, image_path, prompt, output_path, workflow_template=None):
        """
        High-level function to generate video.
        Requires a workflow_template (dict) where we can inject the image and prompt.
        """
        if not workflow_template:
            print("Error: No ComfyUI workflow template provided.")
            return None

        # 1. Upload Image
        print(f"Uploading image {image_path} to ComfyUI...")
        upload_result = self.upload_image(image_path)
        if not upload_result:
            return None
        
        image_filename = upload_result.get("name")
        
        # 2. Modify Workflow
        # This is the tricky part. We need to know WHICH node is the LoadImage and WHICH is the Prompt/KSampler.
        # We'll assume the workflow has specific titles or we use a heuristic.
        # For now, let's assume the user provides a workflow where we replace specific placeholders
        # OR we look for "LoadImage" class type.
        
        workflow = workflow_template.copy()
        
        # Heuristic: Find LoadImage node
        load_image_node_id = None
        for node_id, node in workflow.items():
            if node.get("class_type") == "LoadImage":
                node["inputs"]["image"] = image_filename
                load_image_node_id = node_id
                print(f"Updated LoadImage node {node_id} with {image_filename}")
                break
        
        # Heuristic: Find CLIPTextEncode (Prompt)
        # Usually there are two: Positive and Negative.
        # We might look for one connected to KSampler 'positive'.
        # For simplicity, if we find a node with "text" input and it looks like a prompt, we update it.
        # Or we just don't update prompt if it's SVD (which is image-to-video mostly).
        
        # 3. Queue Prompt
        print("Queuing workflow...")
        queue_res = self.queue_prompt(workflow)
        if not queue_res or "prompt_id" not in queue_res:
            print("Failed to queue prompt.")
            return None
            
        prompt_id = queue_res["prompt_id"]
        print(f"Workflow queued. Prompt ID: {prompt_id}")
        
        # 4. Poll for completion
        # We can poll /history/{prompt_id}
        print("Waiting for generation...")
        while True:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                print("Generation finished.")
                outputs = history[prompt_id].get("outputs", {})
                
                # Find video output
                # Look for SaveVideo, VHS_VideoCombine, etc.
                for node_id, output_data in outputs.items():
                    if "gifs" in output_data:
                        # SVD often outputs gifs/webp in standard nodes, or mp4 in VHS
                        files = output_data["gifs"]
                    elif "videos" in output_data:
                        files = output_data["videos"]
                    elif "images" in output_data:
                        # Maybe it outputted frames?
                        files = output_data["images"]
                    else:
                        continue
                        
                    if files:
                        file_info = files[0]
                        filename = file_info.get("filename")
                        subfolder = file_info.get("subfolder", "")
                        folder_type = file_info.get("type", "output")
                        
                        print(f"Downloading result: {filename}")
                        video_data = self.get_image(filename, subfolder, folder_type)
                        
                        if video_data:
                            with open(output_path, 'wb') as f:
                                f.write(video_data)
                            return output_path
                break
            
            time.sleep(1)
            
        return None
