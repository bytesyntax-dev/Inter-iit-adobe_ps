import cv2
import numpy as np
import os
import urllib.request

class ImageProcessor:
    """
    Handles core image processing operations including basic filters (Pillow/OpenCV style)
    and deep learning models (OpenCV DNN style transfer).
    """
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        # Ensure models directory exists
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
            
        # Mapping from style name to ONNX download URLs on Hugging Face ONNX Model Zoo
        self.style_urls = {
            "candy": "https://huggingface.co/onnxmodelzoo/candy-9/resolve/main/candy-9.onnx",
            "mosaic": "https://huggingface.co/onnxmodelzoo/mosaic-9/resolve/main/mosaic-9.onnx"
        }

    def process(self, input_path, output_path, operation):
        """
        Loads an image, applies the specified operation, and saves the output.
        input_path: Path to the input image file
        output_path: Path where the output image should be saved
        operation: Structured dictionary, e.g. {"op": "tone", "params": {"brightness": 1.2}}
        """
        # Load the image using OpenCV (BGR format)
        img = cv2.imread(input_path)
        if img is None:
            raise ValueError(f"Could not load image from {input_path}")
            
        op_type = operation.get("op", "noop")
        params = operation.get("params", {})
        
        # Branch to the correct operation pipeline
        if op_type == "tone":
            out_img = self._apply_tone_and_colour(img, params)
        elif op_type == "style_transfer":
            out_img = self._apply_style_transfer(img, params)
        elif op_type == "remove_background":
            out_img = self._apply_background_removal(img)
        else:
            # If no-op or unrecognized, just copy original image
            out_img = img.copy()
            
        # Save the result
        # Create output directories if they don't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, out_img)
        return output_path

    def _apply_tone_and_colour(self, img, params):
        """
        Applies basic tone, brightness, contrast, saturation, warmth, or sepia adjustments.
        Optimized using vectorized NumPy operations.
        """
        # Copy to avoid modifying original array
        res = img.copy().astype(float)
        
        # 1. Warmth / Color Temperature
        # Warmth shifts red up, blue down. Cooling shifts blue up, red down.
        if "warmth" in params:
            warmth = float(params["warmth"])
            if warmth > 0:
                # Add to Red (channel 2) and Green (channel 1)
                res[:, :, 2] += warmth
                res[:, :, 1] += warmth * 0.5
            else:
                # Add to Blue (channel 0)
                res[:, :, 0] += abs(warmth)
                
        # 2. Brightness
        # Multiply pixel values by brightness factor
        if "brightness" in params:
            factor = float(params["brightness"])
            res = res * factor
            
        # 3. Contrast
        # Formula: new_pixel = mean + contrast_factor * (old_pixel - mean)
        if "contrast" in params:
            factor = float(params["contrast"])
            # Calculate mean per channel to maintain color balance
            for c in range(3):
                channel_mean = np.mean(res[:, :, c])
                res[:, :, c] = channel_mean + factor * (res[:, :, c] - channel_mean)
                
        # Clip values to valid [0, 255] range
        res = np.clip(res, 0, 255).astype(np.uint8)
        
        # 4. Saturation (HSV channel modification)
        if "saturation" in params:
            factor = float(params["saturation"])
            hsv = cv2.cvtColor(res, cv2.COLOR_BGR2HSV).astype(float)
            hsv[:, :, 1] = hsv[:, :, 1] * factor  # scale Saturation channel
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            res = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            
        # 5. Sepia Tone Matrix
        if params.get("sepia", False):
            # Sepia transformation matrix for BGR format
            sepia_matrix = np.array([
                [0.131, 0.534, 0.272],  # Blue channel output
                [0.168, 0.686, 0.349],  # Green channel output
                [0.189, 0.769, 0.393]   # Red channel output
            ])
            res = cv2.transform(res, sepia_matrix)
            res = np.clip(res, 0, 255).astype(np.uint8)
            
        # 6. Auto-Enhance preset
        if params.get("auto", False):
            # Equalize histogram of Y channel in YCrCb for smart contrast
            ycrcb = cv2.cvtColor(res, cv2.COLOR_BGR2YCrCb)
            channels = list(cv2.split(ycrcb))
            channels[0] = cv2.equalizeHist(channels[0]) # Equalize luminance
            ycrcb = cv2.merge(channels)
            res = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
            
        return res

    def _apply_style_transfer(self, img, params):
        """
        Runs deep learning neural style transfer using a pre-trained ONNX model.
        """
        style = params.get("style", "mosaic")
        if style not in self.style_urls:
            style = "mosaic"  # fallback
            
        model_filename = f"{style}-9.onnx"
        model_path = os.path.join(self.models_dir, model_filename)
        
        # Download the model from the official ONNX Model Zoo if not present locally
        if not os.path.exists(model_path):
            url = self.style_urls[style]
            print(f"Downloading pre-trained style transfer model '{style}' (~7MB)...")
            try:
                urllib.request.urlretrieve(url, model_path)
                print(f"Downloaded model successfully: {model_path}")
            except Exception as e:
                raise RuntimeError(f"Failed to download model from {url}: {e}")
                
        # Load the model via OpenCV's Deep Neural Network (DNN) module
        try:
            net = cv2.dnn.readNetFromONNX(model_path)
        except Exception as e:
            raise RuntimeError(f"Error loading ONNX network: {e}")
            
        # Neural Style Transfer models perform best at standard training resolutions (e.g., 256x256).
        # We will resize the input image to a standard 256x256 size. This reduces memory usage,
        # avoids OutOfMemory errors, and ensures inference is extremely fast (~100ms) on CPU.
        h, w = img.shape[:2]
        target_w = 256
        target_h = 256
        resized_img = cv2.resize(img, (target_w, target_h))
        
        # Prepare the image blob for the neural network
        # Subtract Mean values (BGR order) used during training: (103.939, 116.779, 123.68)
        blob = cv2.dnn.blobFromImage(
            resized_img, 
            scalefactor=1.0, 
            size=(target_w, target_h), 
            mean=(103.939, 116.779, 123.68), 
            swapRB=False, 
            crop=False
        )
        
        # Run forward pass of the network
        net.setInput(blob)
        out = net.forward()
        
        # Post-process the output: shape is 1x3xHxW. Re-order to HxWxC
        out = out.squeeze(0)  # Remove batch dimension -> 3xHxW
        out = out.transpose(1, 2, 0)  # Convert to HxWxC
        
        # Add the mean values back to display the image correctly
        out[:, :, 0] += 103.939  # Blue
        out[:, :, 1] += 116.779  # Green
        out[:, :, 2] += 123.68   # Red
        
        # Clip pixel values back to [0, 255]
        out_img = np.clip(out, 0, 255).astype(np.uint8)
        
        # Resize back to original aspect ratio/size if user wants high-res, 
        # or keep the optimized resolution for performance.
        # Resizing back to original matches standard expected behavior.
        out_img_resized = cv2.resize(out_img, (w, h))
        
        return out_img_resized

    def _apply_background_removal(self, img):
        """
        Removes background using the pre-trained U2-Net model via rembg.
        """
        from rembg import remove
        # rembg takes an image array and returns an RGBA image array (transparent background)
        res = remove(img)
        return res
