# Adobe Image Editor: Conversational AI Image Editor with Versioned Edit History

Inspired by Adobe — Inter IIT Tech Meet 14.0

Adobe Image Editor is a web-based conversational image editor that translates natural language editing requests into image processing operations, maintains a persistent branching version control tree of edits, and lets you explore alternative creative paths through a visual, interactive node graph.

---

## Key Features

1. **Conversational Edit Interface:** Upload an image and type instructions in plain English (e.g., *"make it 30% brighter"*, *"apply a vintage sepia look"*, *"remove the background"*).
2. **AI-Powered Style Transfer:** Runs deep-learning feedforward style transfer models (using pre-trained ONNX models Candy-9 and Mosaic-9) loaded via OpenCV DNN in ~100ms.
3. **AI-Powered Background Removal:** Extracts the primary subject from the image and removes the background using U2-Net via the `rembg` library, outputting a transparent PNG.
4. **Genuinely Branching Edit Tree:** Every edit produces a node in a persistent, branching version history. Selecting a historical state lets you branch off to try alternative edit paths, creating a non-linear history tree.
5. **Visual Node Graph:** Responsive SVG tree renderer in the sidebar displaying parent-child relationships and active canvas nodes.
6. **Context Retention:** Chained operations apply dynamically based on the parent state you are currently viewing.
7. **Session Management:** Ability to manage multiple editing sessions independently, with the ability to start new sessions, switch between them, and delete unwanted ones from the history sidebar.

---

## Tech Stack

*   **Frontend:** React (Vite, Lucide-React, Pure CSS)
*   **Backend:** Python (Flask, OpenCV DNN, NumPy, rembg, onnxruntime)

---

## Directory Structure

```text
├── backend/
│   ├── app.py                # Flask entrypoint & APIs
│   ├── edit_tree.py          # Branching version tree structure
│   ├── image_processor.py    # NumPy/OpenCV filters, ONNX DNN style loader, & U2-Net bg removal
│   ├── instruction_parser.py # Regex pattern keyword matching engine
│   └── models/               # Cached pre-trained ONNX models
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── TreeView.jsx  # SVG Tree layout and render node graph
│   │   ├── App.jsx           # Main workspace layout & API connector
│   │   ├── index.css         # Premium dark glassmorphic styling
│   │   └── main.jsx          # React entrypoint
│   └── package.json          # Node dependencies
├── static/                   # Uploaded/processed images storage
├── sample_images/            # High-quality test images for evaluations
├── test_backend.py           # Unit tests script
├── requirements.txt          # Python dependencies list
└── README.md
```

---

## Setup & Running Instructions

### Prerequisite
Ensure you have **Python 3.8+** and **Node.js 18+** installed.

### 1. Backend Server Setup
From the project root:
```bash
# Create a virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate  # On Windows

# Install python dependencies
pip install -r requirements.txt

# Start the Flask backend (runs on http://localhost:5000)
python backend/app.py
```
*Note: The server will automatically download the pre-trained style transfer models (~7.5MB) to `backend/models/` and the U2-Net background removal model (~176MB) on their first respective executions.*

### 2. Frontend Development Server Setup
From the project root:
```bash
# Navigate to the frontend directory
cd frontend

# Install package dependencies
npm install

# Start the React Vite server (runs on http://localhost:5173/)
npm run dev
```

Open `http://localhost:5173/` in your browser.

---

## Supported Conversational Instructions

*   **Tone & Colour (NumPy/OpenCV):**
    *   *Brightness:* `"make it 30% brighter"`, `"dim the image by 10%"`, `"make it less bright"`
    *   *Contrast:* `"increase contrast by 20%"`, `"make it less contrast"`
    *   *Saturation:* `"make it more vibrant"`, `"convert to black and white"`, `"make it monochrome"`
    *   *Warmth:* `"make the image warmer by 30%"`, `"give it a blue cool look by 20%"`
    *   *Sepia:* `"apply vintage sepia look"`, `"sepia filter"`
    *   *Auto-Enhance:* `"enhance the image"`, `"auto enhance"`
*   **AI Style Transfer (ONNX/OpenCV DNN):**
    *   *Candy:* `"make it look like candy"`, `"apply candy style transfer"`
    *   *Mosaic:* `"make it look like mosaic painting"`
*   **AI Background Removal (U2-Net):**
    *   *Remove Background:* `"remove the background"`, `"remove bg"`, `"isolate the subject"`
