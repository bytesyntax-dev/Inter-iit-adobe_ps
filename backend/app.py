import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Import our custom classes
from edit_tree import EditTree
from instruction_parser import InstructionParser
from image_processor import ImageProcessor

# Resolve the static directory as an absolute path relative to the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')

# Configurations
UPLOAD_FOLDER = os.path.join(STATIC_DIR, 'uploads')
PROCESSED_FOLDER = os.path.join(STATIC_DIR, 'processed')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Initialize global instances for the session
# Since this runs locally on a single machine, we keep a single global session tree.
# This makes state management extremely easy and robust.
current_tree = EditTree()
parser = InstructionParser()
processor = ImageProcessor()

# Global dictionary to track multiple edit tree sessions: root_id -> EditTree
all_trees = {}

def allowed_file(filename):
    """
    Checks if the uploaded file has a valid image extension.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.after_request
def after_request(response):
    """
    Manually configures CORS headers to allow cross-origin requests from the React frontend.
    This avoids needing to install external 'flask-cors' dependencies.
    """
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """
    Endpoint to upload a new base image. 
    Initializes a fresh edit tree with the uploaded image as the root node.
    """
    global current_tree, all_trees
    
    # 1. Check if file is in request
    if 'image' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        # 2. Save the uploaded file securely
        filename = f"original_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 3. Reset the tree and add the root node
        # Use relative web-friendly path to store in node
        web_path = f"static/uploads/{filename}"
        
        current_tree = EditTree()
        root_id = current_tree.add_node(
            image_path=web_path, 
            parent_id=None, 
            explanation="Original image uploaded.",
            operation={"op": "upload", "params": {}}
        )
        
        # Store this tree session in the global dictionary
        all_trees[root_id] = current_tree
        
        return jsonify({
            "message": "Image uploaded successfully",
            "tree": current_tree.serialize()
        })
        
    return jsonify({"error": "Invalid file type. Allowed: PNG, JPG, JPEG, WEBP"}), 400

@app.route('/api/edit', methods=['POST'])
def edit_image():
    """
    Endpoint to process a conversational image editing instruction.
    Can branch from any historical node specified in parentId.
    """
    global current_tree
    
    # 1. Parse JSON payload from frontend
    data = request.json or {}
    instruction = data.get('instruction', '').strip()
    parent_id = data.get('parentId')  # Node ID to branch from
    
    if not instruction:
        return jsonify({"error": "Instruction text is required"}), 400
        
    if not current_tree.root_id:
        return jsonify({"error": "No image has been uploaded yet"}), 400
        
    # 2. Determine parent node (fallback to active node if not specified)
    if not parent_id:
        parent_id = current_tree.active_id
        
    if parent_id not in current_tree.nodes:
        return jsonify({"error": f"Parent node '{parent_id}' not found"}), 400
        
    parent_node = current_tree.nodes[parent_id]
    parent_image_path = parent_node['imagePath']
    
    # Resolve the relative web path to an absolute filesystem path
    if parent_image_path.startswith('static/'):
        parent_abs_path = os.path.join(BASE_DIR, parent_image_path)
    else:
        parent_abs_path = parent_image_path
    
    # 3. Run the instruction parser
    # Retrieve path from root to compile multi-turn context (history) if needed
    history = current_tree.get_node_path_from_root(parent_id)
    operation, explanation = parser.parse_instruction(instruction, history)
    
    # 4. Generate the output filename and path
    ext = parent_image_path.rsplit('.', 1)[-1]
    if operation.get("op") == "remove_background":
        ext = "png"
    out_filename = f"edit_{uuid.uuid4().hex[:8]}.{ext}"
    out_filepath = os.path.join(app.config['PROCESSED_FOLDER'], out_filename)
    out_web_path = f"static/processed/{out_filename}"
    
    # 5. Apply the editing operation in the ImageProcessor
    try:
        processor.process(parent_abs_path, out_filepath, operation)
    except Exception as e:
        return jsonify({"error": f"Image processing failed: {str(e)}"}), 500
        
    # 6. Add the new node to the tree (genuinely branching from parent_id)
    new_node_id = current_tree.add_node(
        image_path=out_web_path,
        parent_id=parent_id,
        explanation=explanation,
        operation=operation
    )
    
    return jsonify({
        "message": "Edit processed successfully",
        "explanation": explanation,
        "activeId": new_node_id,
        "tree": current_tree.serialize()
    })

@app.route('/api/session', methods=['GET'])
def get_session():
    """
    Returns the current serialized state of the edit tree.
    """
    return jsonify(current_tree.serialize())

@app.route('/api/select', methods=['POST'])
def select_node():
    """
    Allows the user to click any node in the tree and set it as active,
    restoring it as the active canvas.
    """
    data = request.json or {}
    node_id = data.get('nodeId')
    
    if not node_id:
        return jsonify({"error": "nodeId is required"}), 400
        
    if current_tree.set_active(node_id):
        return jsonify({
            "message": f"Active node changed to {node_id}",
            "tree": current_tree.serialize()
        })
    else:
        return jsonify({"error": "Node not found"}), 404



@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """
    Returns a list of all active image editing sessions.
    """
    global all_trees
    sessions_list = []
    for root_id, tree in all_trees.items():
        root_node = tree.nodes.get(root_id)
        active_node = tree.nodes.get(tree.active_id)
        if root_node and active_node:
            sessions_list.append({
                "rootId": root_id,
                "rootImage": root_node['imagePath'],
                "activeImage": active_node['imagePath'],
                "explanation": root_node['explanation'],
                "activeExplanation": active_node['explanation'],
                "nodeCount": len(tree.nodes),
                "timestamp": root_node.get('timestamp', 0)
            })
    # Sort sessions by timestamp descending (newest first)
    sessions_list.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return jsonify({"sessions": sessions_list})

@app.route('/api/sessions/select', methods=['POST'])
def select_session():
    """
    Restores an active session by its root node ID.
    """
    global current_tree, all_trees
    data = request.json or {}
    root_id = data.get('rootId')
    
    if not root_id:
        return jsonify({"error": "rootId is required"}), 400
        
    if root_id in all_trees:
        current_tree = all_trees[root_id]
        return jsonify({
            "message": "Session switched successfully",
            "tree": current_tree.serialize()
        })
    else:
        return jsonify({"error": "Session not found"}), 404


if __name__ == '__main__':
    # Run the server locally on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
