import React, { useState, useEffect, useRef } from 'react';
import { Upload, Send, Sparkles, RefreshCw, Eye, GitBranch, AlertCircle, Image as ImageIcon, Plus, Trash2, MessageSquare } from 'lucide-react';
import TreeView from './components/TreeView';

const API_BASE_URL = 'http://localhost:5000';

export default function App() {
  const [tree, setTree] = useState({ nodes: {}, rootId: null, activeId: null });
  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'bot',
      text: 'Hello! I am your AI Image Editor. Please upload an image to begin. Once uploaded, you can describe edits using natural language (e.g., "make it 30% brighter", "add mosaic style", "apply sepia tone").',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [userInput, setUserInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  // Auto-scroll chat to the latest message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Fetch current tree state and all sessions on mount
  useEffect(() => {
    fetchSession();
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  };

  const fetchSession = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/session`);
      if (res.ok) {
        const data = await res.json();
        if (data.rootId) {
          setTree(data);
          // Add a recovery message to the chat
          setMessages(prev => [
            ...prev,
            {
              id: `recovery-${Date.now()}`,
              sender: 'bot',
              text: 'Recovered existing editing session from the server.',
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }
          ]);
        }
      }
    } catch (err) {
      console.warn('Backend server not running yet or unreachable. Start the backend to test.', err);
    }
  };

  const handleSelectSession = async (rootId) => {
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rootId })
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to switch session');
      }
      const data = await res.json();
      setTree(data.tree);
      
      const activeNode = data.tree.nodes[data.tree.activeId];
      setMessages([
        {
          id: 'welcome',
          sender: 'bot',
          text: 'Hello! I am your AI Image Editor. Please upload an image to begin. Once uploaded, you can describe edits using natural language (e.g., "make it 30% brighter", "add mosaic style", "apply sepia tone").',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        },
        {
          id: `switch-${Date.now()}`,
          sender: 'bot',
          text: `Switched to editing session. This session has ${Object.keys(data.tree.nodes).length} versions. Current active version: "${activeNode ? activeNode.explanation : 'Original'}"`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 1. Upload base image
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('image', file);

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to upload image');
      }

      const data = await res.json();
      setTree(data.tree);
      fetchSessions();
      
      setMessages([
        {
          id: `upload-${Date.now()}`,
          sender: 'bot',
          text: 'Great! Image uploaded successfully. You are now viewing the original canvas. Tell me what changes you would like to make!',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } catch (err) {
      setError(err.message);
      setMessages(prev => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: 'bot',
          text: `Upload failed: ${err.message}`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // 2. Send conversational edit request
  const handleSend = async (e) => {
    e.preventDefault();
    if (!userInput.trim() || loading || !tree.rootId) return;

    const prompt = userInput;
    setUserInput('');
    setLoading(true);
    setError(null);

    // Add user prompt to chat
    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: prompt,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const res = await fetch(`${API_BASE_URL}/api/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instruction: prompt,
          parentId: tree.activeId // Branch from the current active canvas state
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to process editing request');
      }

      const data = await res.json();
      setTree(data.tree);
      fetchSessions();

      // Add bot explanation response to chat
      const botMessage = {
        id: `bot-${Date.now()}`,
        sender: 'bot',
        text: data.explanation,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      setError(err.message);
      setMessages(prev => [
        ...prev,
        {
          id: `bot-err-${Date.now()}`,
          sender: 'bot',
          text: `Processing error: ${err.message}`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // 3. Select node from the visual TreeView
  const handleSelectNode = async (nodeId) => {
    if (nodeId === tree.activeId || loading) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodeId })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to select node');
      }

      const data = await res.json();
      setTree(data.tree);

      // Log action in the chat
      const node = data.tree.nodes[nodeId];
      setMessages(prev => [
        ...prev,
        {
          id: `select-${Date.now()}`,
          sender: 'bot',
          text: `Canvas restored to version: "${node.explanation}". Any new edits you type will branch from this historical point.`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Helper properties
  const activeNode = tree.nodes[tree.activeId];
  const activeImageUrl = activeNode ? `${API_BASE_URL}/${activeNode.imagePath}` : '';
  const isBranchingPoint = activeNode && activeNode.children.length > 0;

  return (
    <div className="app-container" style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Application Header */}
      <header className="app-header">
        <div className="logo-container" style={{ cursor: 'pointer' }} onClick={() => setTree({ nodes: {}, rootId: null, activeId: null })}>
          <div className="logo-icon">Ad</div>
          <div>
            <h1 className="logo-text">Adobe</h1>
            <div className="tagline">Conversational Image Workspace</div>
          </div>
        </div>
        
        {tree.rootId && (
          <button 
            className="control-item" 
            onClick={() => handleSelectNode(tree.rootId)}
            style={{ 
              background: 'transparent', 
              border: '1px solid var(--border)', 
              color: 'var(--text-secondary)',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '12px'
            }}
          >
            <RefreshCw size={14} /> Start Over
          </button>
        )}
      </header>

      <div className="workspace-layout">
        {/* Gemini-Style Left History Sidebar */}
        <aside className="history-sidebar">
          <div className="new-chat-container">
            <button 
              className="new-chat-btn"
              onClick={() => {
                setTree({ nodes: {}, rootId: null, activeId: null });
                setMessages([
                  {
                    id: 'welcome',
                    sender: 'bot',
                    text: 'Hello! I am your AI Image Editor. Please upload an image to begin. Once uploaded, you can describe edits using natural language.',
                    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  }
                ]);
              }}
            >
              <Plus size={16} />
              <span>New Session</span>
            </button>
          </div>
          
          <div className="sessions-list-container">
            {sessions.length === 0 ? (
              <div style={{ padding: '20px 10px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                No active sessions
              </div>
            ) : (
              sessions.map((s) => (
                <div 
                  key={s.rootId}
                  className={`session-list-item ${tree.rootId === s.rootId ? 'active' : ''}`}
                  onClick={() => handleSelectSession(s.rootId)}
                >
                  <div className="session-item-content">
                    <div className="session-item-thumbnail">
                      <img src={`${API_BASE_URL}/${s.activeImage}`} alt="Session active state preview" />
                    </div>
                    <div className="session-item-info">
                      <div className="session-item-title">{s.activeExplanation}</div>
                      <div className="session-item-meta">{s.nodeCount} edits</div>
                    </div>
                  </div>
                  <button 
                    className="delete-session-btn" 
                    onClick={(e) => handleDeleteSession(e, s.rootId)}
                    title="Delete session"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* Main Workspace (depends on active tree) */}
        {!tree.rootId ? (
          // 1. Initial State: Screen to upload image
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-dark)', padding: '20px', gap: '20px' }}>
            <div className="upload-placeholder" onClick={handleUploadClick}>
              <div className="upload-icon-container">
                <Upload size={32} />
              </div>
              <h2 style={{ fontSize: '18px', fontWeight: 600, fontFamily: 'Outfit' }}>Upload base image to start</h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', textAlign: 'center', maxWidth: '320px', lineHeight: 1.5 }}>
                Drag and drop an image or click to browse. We support PNG, JPG, JPEG, and WEBP.
              </p>
              {error && (
                <div style={{ display: 'flex', gap: '8px', color: '#EF4444', fontSize: '13px', alignItems: 'center', marginTop: '8px' }}>
                  <AlertCircle size={16} /> {error}
                </div>
              )}
            </div>
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              accept="image/*" 
              className="hidden-file-input"
            />
          </div>
        ) : (
          // 2. Interactive Editing Dashboard
          <main className="dashboard" style={{ flex: 1 }}>
            
            {/* LEFT: Conversation Chat Panel */}
            <section className="chat-panel">
              <div className="panel-header">
                <Sparkles size={18} style={{ color: 'var(--accent-purple)' }} />
                <h2 className="panel-title">Conversation</h2>
              </div>
              
              <div className="chat-history">
                {messages.map((msg) => (
                  <div key={msg.id} className={`chat-message ${msg.sender}`}>
                    <div>{msg.text}</div>
                    <div className="message-time">{msg.time}</div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              <div className="chat-input-area">
                <form onSubmit={handleSend} className="chat-form">
                  <input
                    type="text"
                    placeholder="Describe your edits..."
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    className="chat-input"
                    disabled={loading}
                  />
                  <button type="submit" className="send-button" disabled={loading || !userInput.trim()}>
                    <Send size={16} />
                  </button>
                </form>
              </div>
            </section>

            {/* CENTER: Working Image Canvas */}
            <section className="canvas-panel">
              {loading && (
                <div className="loading-overlay">
                  <div className="spinner"></div>
                  <div style={{ fontSize: '14px', fontWeight: 500 }}>AI is processing your image...</div>
                </div>
              )}
              
              <div className="canvas-container">
                <div className="canvas-image-wrapper">
                  <img
                    src={activeImageUrl}
                    alt="Active Working Canvas"
                    className="canvas-image"
                  />
                </div>
              </div>

              <div className="canvas-controls">
                <div className="control-item">
                  <Eye size={16} />
                  <span>Viewing Active Version</span>
                </div>
                
                {isBranchingPoint && (
                  <div className="control-item" style={{ color: 'var(--accent-pink)' }}>
                    <GitBranch size={16} />
                    <span>Sub-branches exist here</span>
                  </div>
                )}
              </div>
            </section>

            {/* RIGHT: Branching History Tree Sidebar */}
            <section className="tree-panel">
              <div className="panel-header">
                <GitBranch size={18} style={{ color: 'var(--accent-blue)' }} />
                <h2 className="panel-title">Version History</h2>
              </div>
              
              <div className="tree-hint">
                <AlertCircle size={14} />
                <span>Click nodes to restore that history state.</span>
              </div>

              <div className="tree-canvas-container">
                <TreeView 
                  treeData={tree} 
                  onSelectNode={handleSelectNode} 
                />
              </div>

              {activeNode && (
                <div className="node-details">
                  {isBranchingPoint ? (
                    <span className="branch-badge">Branch point</span>
                  ) : (
                    <span className="active-badge">Active node</span>
                  )}
                  <h3 className="node-details-title">Selected State details</h3>
                  <p className="node-details-desc">{activeNode.explanation}</p>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
                    ID: {activeNode.id} • Created: {new Date(activeNode.timestamp * 1000).toLocaleTimeString()}
                  </div>
                </div>
              )}
            </section>

            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              accept="image/*" 
              className="hidden-file-input"
            />
          </main>
        )}
      </div>
    </div>
  );
}
