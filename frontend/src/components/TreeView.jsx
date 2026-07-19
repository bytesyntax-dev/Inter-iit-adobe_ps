import React, { useMemo } from 'react';
import { RefreshCw } from 'lucide-react';

/**
 * Renders an interactive SVG-based branching edit history tree.
 * Allows users to see all edit branches, see the active node,
 * and click any historical node to branch/view it.
 */
export default function TreeView({ treeData, onSelectNode }) {
  const { nodes, rootId, activeId } = treeData;

  // 1. Calculate positions for each node using a recursive layout algorithm
  const layout = useMemo(() => {
    const positions = {};
    if (!rootId || !nodes || !nodes[rootId]) return { positions, maxDepth: 0, width: 300 };

    // Step 1.1: Calculate leaf count for each subtree to allocate X coordinates proportionally
    const leafCount = {};
    function countLeaves(nodeId) {
      const node = nodes[nodeId];
      if (!node) return 0;
      if (!node.children || node.children.length === 0) {
        leafCount[nodeId] = 1;
        return 1;
      }
      let count = 0;
      for (const childId of node.children) {
        count += countLeaves(childId);
      }
      leafCount[nodeId] = count;
      return count;
    }
    countLeaves(rootId);

    // Step 1.2: Recursively assign coordinates
    let maxDepth = 0;
    const canvasWidth = 280; // Fixed width matching the sidebar viewport width
    
    function assignCoords(nodeId, xStart, xEnd, yLevel) {
      const node = nodes[nodeId];
      if (!node) return;
      
      if (yLevel > maxDepth) maxDepth = yLevel;

      // Place the node in the center of its allocated horizontal space
      const x = (xStart + xEnd) / 2;
      const y = yLevel * 90 + 50; // 90px vertical spacing, offset by 50px at top
      
      positions[nodeId] = { x, y, depth: yLevel };

      if (!node.children || node.children.length === 0) return;

      let currentXStart = xStart;
      const totalLeaves = leafCount[nodeId];
      const widthRange = xEnd - xStart;

      for (const childId of node.children) {
        const childLeaves = leafCount[childId] || 1;
        const childWidth = (childLeaves / totalLeaves) * widthRange;
        assignCoords(childId, currentXStart, currentXStart + childWidth, yLevel + 1);
        currentXStart += childWidth;
      }
    }

    // Allocate horizontal space from X=30 to X=250
    assignCoords(rootId, 30, canvasWidth - 30, 0);
    return { positions, maxDepth, width: canvasWidth };
  }, [nodes, rootId]);

  const { positions, maxDepth } = layout;

  // 2. Generate connection paths between parent and child nodes
  const paths = useMemo(() => {
    const lines = [];
    if (!positions || !nodes) return lines;

    Object.keys(positions).forEach((childId) => {
      const node = nodes[childId];
      if (node && node.parentId && positions[node.parentId]) {
        const parentPos = positions[node.parentId];
        const childPos = positions[childId];
        
        // Draw a smooth S-curve (Cubic Bezier) between parent and child
        const d = `M ${parentPos.x} ${parentPos.y} 
                   C ${parentPos.x} ${(parentPos.y + childPos.y) / 2}, 
                     ${childPos.x} ${(parentPos.y + childPos.y) / 2}, 
                     ${childPos.x} ${childPos.y}`;
        
        lines.push({
          id: `line-${node.parentId}-${childId}`,
          d,
          isActiveLink: childId === activeId || node.parentId === activeId
        });
      }
    });
    return lines;
  }, [positions, nodes, activeId]);

  if (!rootId || !nodes) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
        No edit history available. Upload an image to start.
      </div>
    );
  }

  // Auto-calculate dynamic SVG height based on tree depth
  const svgHeight = Math.max(300, maxDepth * 90 + 100);

  return (
    <div style={{ width: '100%', height: '100%', overflowY: 'auto', position: 'relative' }}>
      <svg width="100%" height={svgHeight} style={{ display: 'block' }}>
        <defs>
          {/* Subtle drop shadow filter for glowing active nodes */}
          <filter id="active-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* 1. Draw connection lines */}
        {paths.map((path) => (
          <path
            key={path.id}
            d={path.d}
            fill="none"
            stroke={path.isActiveLink ? 'var(--accent-purple)' : 'rgba(255, 255, 255, 0.15)'}
            strokeWidth={path.isActiveLink ? 2.5 : 1.5}
            strokeDasharray={path.isActiveLink ? 'none' : '4 2'}
            style={{ transition: 'var(--transition-smooth)' }}
          />
        ))}

        {/* 2. Draw nodes */}
        {Object.entries(positions).map(([nodeId, pos]) => {
          const node = nodes[nodeId];
          const isActive = nodeId === activeId;
          const isRoot = node.parentId === null;
          
          // Determine styling based on type of node
          let fill = 'var(--bg-card)';
          let stroke = 'rgba(255, 255, 255, 0.25)';
          let r = 16;
          
          if (isActive) {
            fill = 'var(--accent-purple)';
            stroke = 'white';
            r = 18; // Make active node slightly larger
          } else if (isRoot) {
            stroke = 'var(--accent-blue)';
          }

          // Node text: R for root, or index number
          const nodeText = isRoot ? 'R' : node.operation.op === 'style_transfer' ? 'S' : 'T';

          return (
            <g
              key={nodeId}
              onClick={() => onSelectNode(nodeId)}
              style={{ cursor: 'pointer' }}
            >
              {/* Tooltip description (SVG Title element) */}
              <title>{`${node.explanation}\nClick to view this version`}</title>

              {/* Halo glow behind active node */}
              {isActive && (
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={r + 6}
                  fill="rgba(139, 92, 246, 0.3)"
                  filter="url(#active-glow)"
                />
              )}

              {/* Node background circle */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={r}
                fill={fill}
                stroke={stroke}
                strokeWidth={isActive ? 2.5 : 1.5}
                style={{ transition: 'var(--transition-smooth)' }}
              />

              {/* Inner symbol text */}
              <text
                x={pos.x}
                y={pos.y + 4}
                textAnchor="middle"
                fill={isActive ? 'white' : 'var(--text-primary)'}
                fontSize={isActive ? '11px' : '10px'}
                fontWeight="700"
                style={{ userSelect: 'none' }}
              >
                {nodeText}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
