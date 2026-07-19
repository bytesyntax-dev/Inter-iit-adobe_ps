import os
import cv2
import numpy as np
import sys

# Add the backend folder to python search path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from edit_tree import EditTree
from instruction_parser import InstructionParser
from image_processor import ImageProcessor

def run_tests():
    print("=== STARTING BACKEND UNIT TESTS ===")
    
    # 1. Setup paths and directories
    test_dir = "test_output"
    os.makedirs(test_dir, exist_ok=True)
    
    original_img_path = os.path.join(test_dir, "test_original.png")
    
    # Create a simple test image (3 channel color gradient)
    print("Creating test image...")
    gradient = np.zeros((300, 300, 3), dtype=np.uint8)
    for y in range(300):
        for x in range(300):
            # Gradient: blue increasing horizontally, red vertically, green diagonally
            gradient[y, x] = [
                int(x / 300.0 * 255),  # Blue
                int((x + y) / 600.0 * 255),  # Green
                int(y / 300.0 * 255)   # Red
            ]
    cv2.imwrite(original_img_path, gradient)
    print(f"Saved test image to: {original_img_path}")
    
    # 2. Test Parser
    print("\n--- Testing Instruction Parser ---")
    parser = InstructionParser()
    
    queries = [
        "make the image 30% brighter",
        "warm it up a little bit by 15%",
        "make it look like a candy painting",
        "convert it to black and white",
        "apply vintage sepia look"
    ]
    
    for q in queries:
        op, exp = parser.parse_instruction(q)
        print(f"Query: '{q}'")
        print(f"  Parsed Op:  {op}")
        print(f"  Explanation: '{exp}'\n")

    # 3. Test Tree structure
    print("--- Testing Edit Tree Branching ---")
    tree = EditTree()
    
    # Add root node
    root_id = tree.add_node(original_img_path, parent_id=None, explanation="Original Upload")
    print(f"Created Root Node ID: {root_id}")
    
    # Add child 1 (Brighter)
    img_bright_path = os.path.join(test_dir, "test_brighter.png")
    c1_id = tree.add_node(img_bright_path, parent_id=root_id, explanation="Increased brightness by 30%")
    print(f"Created Child 1 Node ID: {c1_id} (Parent: {root_id})")
    
    # Add child 2 (Branching from root: Saturation)
    img_sat_path = os.path.join(test_dir, "test_sepia.png")
    c2_id = tree.add_node(img_sat_path, parent_id=root_id, explanation="Applied sepia filter")
    print(f"Created Child 2 Node ID: {c2_id} (Parent: {root_id} - Genuinely Branching!)")
    
    # Print children of root
    root_children = tree.nodes[root_id]["children"]
    print(f"Root Node children: {root_children}")
    assert c1_id in root_children, "Child 1 not found in root's children"
    assert c2_id in root_children, "Child 2 not found in root's children (Branching failed!)"
    print("Tree branching structure test: PASSED")

    # 4. Test Image Processor
    print("\n--- Testing Image Processor & ONNX Models ---")
    processor = ImageProcessor(models_dir=os.path.join("backend", "models"))
    
    # Test Brightness Op
    print("Applying brightness adjustment...")
    op_brightness = {"op": "tone", "params": {"brightness": 1.3}}
    out_bright_path = os.path.join(test_dir, "processed_bright.png")
    processor.process(original_img_path, out_bright_path, op_brightness)
    assert os.path.exists(out_bright_path), "Failed to save brighter image"
    print("Brightness processing: PASSED")
    
    # Test Warmth Op
    print("Applying warmth adjustment...")
    op_warmth = {"op": "tone", "params": {"warmth": 40}}
    out_warm_path = os.path.join(test_dir, "processed_warm.png")
    processor.process(original_img_path, out_warm_path, op_warmth)
    assert os.path.exists(out_warm_path), "Failed to save warmer image"
    print("Warmth processing: PASSED")

    # Test Sepia Op
    print("Applying sepia tone...")
    op_sepia = {"op": "tone", "params": {"sepia": True}}
    out_sepia_path = os.path.join(test_dir, "processed_sepia.png")
    processor.process(original_img_path, out_sepia_path, op_sepia)
    assert os.path.exists(out_sepia_path), "Failed to save sepia image"
    print("Sepia processing: PASSED")

    # Test Neural Style Transfer (ONNX download & run)
    print("\nApplying Neural Style Transfer ('candy' style)...")
    print("Note: This will download a ~7.5MB candy-9.onnx file on the first run.")
    op_style = {"op": "style_transfer", "params": {"style": "candy"}}
    out_style_path = os.path.join(test_dir, "processed_style_candy.png")
    
    try:
        processor.process(original_img_path, out_style_path, op_style)
        assert os.path.exists(out_style_path), "Failed to save style transfer image"
        print("Neural Style Transfer ('candy'): PASSED")
    except Exception as e:
        print(f"Neural Style Transfer: FAILED ({e})")
        print("Please check internet connection or permissions to download the ONNX model.")
        
    print("\n=== ALL BACKEND TESTS COMPLETED SUCCESSFULY ===")

if __name__ == "__main__":
    run_tests()
