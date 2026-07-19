import time
import uuid

class EditNode:
    """
    Represents a single state/version of the image in the editing history.
    """
    def __init__(self, image_path, parent_id=None, explanation="Original Image", operation=None):
        # A short unique ID to identify this specific version of the image
        self.node_id = f"node_{uuid.uuid4().hex[:8]}"
        self.parent_id = parent_id
        # The filesystem or web-accessible path to the image at this step
        self.image_path = image_path
        # A plain-English explanation of what was changed and why
        self.explanation = explanation
        # The structured operation applied to create this node (e.g., {"op": "brightness", "amount": 0.2})
        self.operation = operation or {}
        self.timestamp = time.time()

class EditTree:
    """
    Maintains the full branching history of image edits.
    Allows branching from any historical node, creating a non-linear history tree.
    """
    def __init__(self):
        # Flat dictionary mapping: node_id -> Node details (for fast lookup)
        self.nodes = {}
        self.root_id = None
        self.active_id = None  # Tracks which node the user is currently viewing/editing from

    def add_node(self, image_path, parent_id=None, explanation="Original Image", operation=None):
        """
        Adds a new node to the tree. If parent_id is specified, it attaches to that node
        as a child, effectively supporting branching.
        """
        # Create a new node instance
        node = EditNode(image_path, parent_id, explanation, operation)
        
        # Format node details as a dictionary for easy JSON serialization
        node_data = {
            "id": node.node_id,
            "parentId": node.parent_id,
            "imagePath": node.image_path,
            "explanation": node.explanation,
            "operation": node.operation,
            "timestamp": node.timestamp,
            "children": []  # Holds child node IDs
        }
        
        # Add to our flat nodes dictionary
        self.nodes[node.node_id] = node_data
        
        # If there is no parent, this is the root node (first upload)
        if parent_id is None:
            self.root_id = node.node_id
        else:
            # If parent exists, register this new node's ID in the parent's children list
            if parent_id in self.nodes:
                self.nodes[parent_id]["children"].append(node.node_id)
            else:
                raise ValueError(f"Parent node with ID '{parent_id}' does not exist.")
        
        # The newly added node becomes the active node of the canvas
        self.active_id = node.node_id
        return node.node_id

    def set_active(self, node_id):
        """
        Sets the current active canvas view to a historical node.
        """
        if node_id in self.nodes:
            self.active_id = node_id
            return True
        return False

    def get_node_path_from_root(self, node_id):
        """
        Retrieves the list of operations from the root to the specified node.
        This helps the LLM parser maintain conversational context (multi-turn session).
        """
        path = []
        current_id = node_id
        while current_id is not None:
            if current_id in self.nodes:
                node = self.nodes[current_id]
                path.append(node)
                current_id = node["parentId"]
            else:
                break
        path.reverse()  # Order from root node down to the target node
        return path

    def serialize(self):
        """
        Returns the entire tree state to be sent to the React frontend.
        """
        return {
            "nodes": self.nodes,
            "rootId": self.root_id,
            "activeId": self.active_id
        }
