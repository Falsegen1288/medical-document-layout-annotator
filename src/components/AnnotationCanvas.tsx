import React, { useRef, useEffect, useState } from 'react';
import { Detection, CLASS_COLORS, CLASS_LABELS, DocLayClass } from '../types';
import { useAnnotation } from '../context/AnnotationContext';
import { Maximize, Minimize, RotateCcw, Move, PenTool, Check } from 'lucide-react';

interface AnnotationCanvasProps {
  detections: Detection[];
  imagePath: string;
}

export const AnnotationCanvas: React.FC<AnnotationCanvasProps> = ({ detections, imagePath }) => {
  const { hoveredDetectionIndex, setHoveredDetectionIndex, addDetection, activeModelTab } = useAnnotation();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Mode: 'pan' or 'draw'
  const [canvasMode, setCanvasMode] = useState<'pan' | 'draw'>('pan');
  const [selectedDrawClass, setSelectedDrawClass] = useState<DocLayClass>('text');

  // Zoom and Pan States
  const [scale, setScale] = useState<number>(1);
  const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Drawing States
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawingBbox, setDrawingBbox] = useState<[number, number, number, number] | null>(null);

  // Load Image
  useEffect(() => {
    setLoading(true);
    const img = new Image();
    img.src = imagePath;
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      setImage(img);
      setLoading(false);
      resetZoom(img);
    };
    img.onerror = () => {
      console.error('Failed to load canvas image');
      setLoading(false);
    };
  }, [imagePath]);

  // Handle ResizeObserver
  const [resizedDimensions, setResizedDimensions] = useState({ width: 600, height: 750 });
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setResizedDimensions({
          width: Math.floor(entry.contentRect.width),
          height: Math.floor(containerRef.current?.clientHeight || 650)
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const resetZoom = (loadedImg?: HTMLImageElement) => {
    const activeImage = loadedImg || image;
    if (!activeImage || !containerRef.current) return;

    const w = containerRef.current.clientWidth || 600;
    const h = containerRef.current.clientHeight || 750;

    const scaleX = (w - 60) / activeImage.width;
    const scaleY = (h - 60) / activeImage.height;
    const fitScale = Math.min(scaleX, scaleY, 1);

    setScale(fitScale);
    setOffset({
      x: (w - activeImage.width * fitScale) / 2,
      y: (h - activeImage.height * fitScale) / 2
    });
  };

  // Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !image) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear background
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    // Apply zoom and pan transformations
    ctx.translate(offset.x, offset.y);
    ctx.scale(scale, scale);

    // 1. Draw PDF page document
    ctx.drawImage(image, 0, 0);

    // 2. Draw existing bboxes
    detections.forEach((det, idx) => {
      const [x0, y0, x1, y1] = det.bbox;
      const w = x1 - x0;
      const h = y1 - y0;
      const color = CLASS_COLORS[det.type] || '#46f1c5';
      const isHovered = hoveredDetectionIndex === idx;

      const alpha = isHovered ? 0.35 : 0.15;
      ctx.fillStyle = hexToRgba(color, alpha);
      ctx.fillRect(x0, y0, w, h);

      ctx.lineWidth = isHovered ? 3 : 1.5;
      ctx.strokeStyle = color;
      ctx.strokeRect(x0, y0, w, h);

      if (w > 30 || isHovered) {
        ctx.fillStyle = color;
        const fontHeight = Math.max(10, Math.floor(11 / scale));
        ctx.font = `bold ${fontHeight}px JetBrains Mono, monospace`;
        const textStr = `${CLASS_LABELS[det.type] || det.type.toUpperCase()} [${idx}]`;
        const textWidth = ctx.measureText(textStr).width;

        const labelHeight = fontHeight + 4;
        ctx.fillRect(x0 - 0.75, y0 - labelHeight, textWidth + 8, labelHeight);

        ctx.fillStyle = '#ffffff';
        ctx.fillText(textStr, x0 + 3, y0 - 3);
      }
    });

    // 3. Draw active drawing dashed rectangle
    if (drawingBbox) {
      const [x0, y0, x1, y1] = drawingBbox;
      const drawColor = CLASS_COLORS[selectedDrawClass] || '#46f1c5';
      ctx.fillStyle = hexToRgba(drawColor, 0.25);
      ctx.fillRect(x0, y0, x1 - x0, y1 - y0);

      ctx.lineWidth = 2;
      ctx.strokeStyle = drawColor;
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
      ctx.setLineDash([]); // reset

      // floating cursor tooltip values
      ctx.fillStyle = drawColor;
      const drawFontHeight = Math.max(10, Math.floor(11 / scale));
      ctx.font = `bold ${drawFontHeight}px JetBrains Mono, monospace`;
      const sizeTag = `${CLASS_LABELS[selectedDrawClass].toUpperCase()} (${Math.round(x1 - x0)}x${Math.round(y1 - y0)})`;
      const sizeTagWidth = ctx.measureText(sizeTag).width;
      ctx.fillRect(x0, y0 - drawFontHeight - 4, sizeTagWidth + 8, drawFontHeight + 4);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(sizeTag, x0 + 4, y0 - 4);
    }

    ctx.restore();
  }, [image, detections, scale, offset, hoveredDetectionIndex, resizedDimensions, drawingBbox, selectedDrawClass]);

  const hexToRgba = (hex: string, alpha: number) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const getCanvasCoords = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current || !image) return null;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const imgX = (x - offset.x) / scale;
    const imgY = (y - offset.y) / scale;

    return { x: imgX, y: imgY };
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (canvasMode === 'pan') {
      if (isPanning) {
        const dx = e.clientX - panStart.x;
        const dy = e.clientY - panStart.y;
        setOffset({ x: offset.x + dx, y: offset.y + dy });
        setPanStart({ x: e.clientX, y: e.clientY });
        return;
      }

      const coords = getCanvasCoords(e);
      if (!coords) return;

      let foundIdx: number | null = null;
      for (let i = detections.length - 1; i >= 0; i--) {
        const [x0, y0, x1, y1] = detections[i].bbox;
        if (coords.x >= x0 && coords.x <= x1 && coords.y >= y0 && coords.y <= y1) {
          foundIdx = i;
          break;
        }
      }

      if (foundIdx !== hoveredDetectionIndex) {
        setHoveredDetectionIndex(foundIdx);
      }
    } else if (canvasMode === 'draw') {
      if (isDrawing && drawStart) {
        const currentCoords = getCanvasCoords(e);
        if (currentCoords) {
          setDrawingBbox([
            Math.min(drawStart.x, currentCoords.x),
            Math.min(drawStart.y, currentCoords.y),
            Math.max(drawStart.x, currentCoords.x),
            Math.max(drawStart.y, currentCoords.y)
          ]);
        }
      }
    }
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (canvasMode === 'pan') {
      if (e.button === 0 && hoveredDetectionIndex === null) {
        setIsPanning(true);
        setPanStart({ x: e.clientX, y: e.clientY });
      }
    } else if (canvasMode === 'draw') {
      if (activeModelTab !== 'GT') {
        alert('You must be on the "Current GT (Working)" tab to draw boxes.');
        return;
      }
      if (e.button === 0) {
        const coords = getCanvasCoords(e);
        if (coords) {
          setIsDrawing(true);
          setDrawStart(coords);
          setDrawingBbox([coords.x, coords.y, coords.x, coords.y]);
        }
      }
    }
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (canvasMode === 'pan') {
      setIsPanning(false);
    } else if (canvasMode === 'draw') {
      if (isDrawing && drawingBbox) {
        const [x0, y0, x1, y1] = drawingBbox;
        const w = x1 - x0;
        const h = y1 - y0;

        // Verify minimum drag threshold
        if (w > 6 && h > 6) {
          addDetection(selectedDrawClass, [x0, y0, x1, y1]);
        }
      }
      setIsDrawing(false);
      setDrawStart(null);
      setDrawingBbox(null);
    }
  };

  const handleMouseLeave = () => {
    setIsPanning(false);
    setIsDrawing(false);
    setDrawStart(null);
    setDrawingBbox(null);
    setHoveredDetectionIndex(null);
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomIntensity = 0.08;
    const rect = canvasRef.current!.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const imgX = (mouseX - offset.x) / scale;
    const imgY = (mouseY - offset.y) / scale;

    const zoomFactor = e.deltaY < 0 ? (1 + zoomIntensity) : (1 - zoomIntensity);
    const nextScale = Math.max(0.12, Math.min(6, scale * zoomFactor));

    setOffset({
      x: mouseX - imgX * nextScale,
      y: mouseY - imgY * nextScale
    });
    setScale(nextScale);
  };

  const zoomIn = () => {
    setScale(prev => {
      const nextScale = Math.min(6, prev + 0.15);
      if (containerRef.current) {
        const w = containerRef.current.clientWidth / 2;
        const h = containerRef.current.clientHeight / 2;
        const imgX = (w - offset.x) / prev;
        const imgY = (h - offset.y) / prev;
        setOffset({
          x: w - imgX * nextScale,
          y: h - imgY * nextScale
        });
      }
      return nextScale;
    });
  };

  const zoomOut = () => {
    setScale(prev => {
      const nextScale = Math.max(0.12, prev - 0.15);
      if (containerRef.current) {
        const w = containerRef.current.clientWidth / 2;
        const h = containerRef.current.clientHeight / 2;
        const imgX = (w - offset.x) / prev;
        const imgY = (h - offset.y) / prev;
        setOffset({
          x: w - imgX * nextScale,
          y: h - imgY * nextScale
        });
      }
      return nextScale;
    });
  };

  return (
    <div 
      id="canvas_container_panel"
      ref={containerRef} 
      className="flex-1 w-full bg-surface-dim border border-border relative overflow-hidden flex items-center justify-center bg-grid-subtle transition-all h-[650px]"
    >
      {loading ? (
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="font-mono text-xs text-text-muted">LOADING SOURCE DOCUMENT IMAGES...</p>
        </div>
      ) : (
        <canvas
          id="clinical_annotation_canvas"
          ref={canvasRef}
          width={resizedDimensions.width}
          height={resizedDimensions.height}
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
          onWheel={handleWheel}
          style={{ 
            cursor: canvasMode === 'draw' ? 'crosshair' : isPanning ? 'grabbing' : hoveredDetectionIndex !== null ? 'pointer' : 'grab', 
            display: 'block' 
          }}
          className="w-full h-full"
        />
      )}

      {/* Modern Canvas Interaction Modes Floating Menu */}
      <div className="absolute top-4 left-4 flex gap-1 z-20 bg-surface/90 backdrop-blur border border-border p-1 shadow-md">
        <button
          id="pan_mode_toggle_btn"
          onClick={() => setCanvasMode('pan')}
          className={`flex items-center gap-1.5 px-3 py-1.5 font-mono text-xs cursor-pointer transition-all ${
            canvasMode === 'pan' ? 'bg-primary text-on-primary font-bold' : 'text-on-surface hover:bg-surface-container'
          }`}
        >
          <Move className="w-3.5 h-3.5" />
          PAN / ZOOM
        </button>
        <button
          id="draw_mode_toggle_btn"
          onClick={() => {
            if (activeModelTab !== 'GT') {
              alert('Please switch the active model layer to "Current GT (Working)" to draw new bboxes.');
              return;
            }
            setCanvasMode('draw');
          }}
          className={`flex items-center gap-1.5 px-3 py-1.5 font-mono text-xs cursor-pointer transition-all ${
            canvasMode === 'draw' ? 'bg-primary text-on-primary font-bold' : 'text-on-surface hover:bg-surface-container'
          }`}
        >
          <PenTool className="w-3.5 h-3.5" />
          DRAW BOX MODE
        </button>
      </div>

      {/* Draw Category Selector Tooltip */}
      {canvasMode === 'draw' && (
        <div className="absolute top-16 left-4 bg-surface-container-high/95 backdrop-blur border border-border p-2.5 shadow-xl max-w-sm flex flex-col gap-2 z-20">
          <span className="font-mono text-[9px] text-text-muted uppercase tracking-wider block font-bold">Category for drawn box:</span>
          <div className="grid grid-cols-2 gap-1 max-h-36 overflow-y-auto pr-1">
            {(['title', 'section_header', 'text', 'list_item', 'table', 'picture', 'caption', 'footnote', 'formula', 'page_header', 'page_footer'] as DocLayClass[]).map((cls) => (
              <button
                key={cls}
                onClick={() => setSelectedDrawClass(cls)}
                className={`flex items-center gap-1.5 px-2 py-1 border text-left font-mono text-[10px] cursor-pointer transition-all rounded-xs ${
                  selectedDrawClass === cls 
                    ? 'border-primary bg-primary/10 text-primary font-bold shadow-sm' 
                    : 'border-border/60 hover:border-primary text-on-surface'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-sm shrink-0" style={{ backgroundColor: CLASS_COLORS[cls] }} />
                <span className="truncate">{CLASS_LABELS[cls]}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Floating Zoom & Frame Reset Utilities Overlay */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2 z-20">
        <button 
          id="zoom_in_btn"
          onClick={zoomIn}
          title="Zoom In"
          className="w-10 h-10 bg-surface-container-high hover:bg-surface-bright text-on-surface border border-border rounded flex items-center justify-center transition-colors shadow-lg cursor-pointer"
        >
          <Maximize className="w-4 h-4 text-primary" />
        </button>
        <button 
          id="zoom_out_btn"
          onClick={zoomOut}
          title="Zoom Out"
          className="w-10 h-10 bg-surface-container-high hover:bg-surface-bright text-on-surface border border-border rounded flex items-center justify-center transition-colors shadow-lg cursor-pointer"
        >
          <Minimize className="w-4 h-4 text-primary" />
        </button>
        <button 
          id="zoom_reset_btn"
          onClick={() => resetZoom()}
          title="Reset Frame Fit"
          className="w-10 h-10 bg-surface-container-high hover:bg-surface-bright text-on-surface border border-border rounded flex items-center justify-center transition-colors shadow-lg cursor-pointer"
        >
          <RotateCcw className="w-4 h-4 text-primary" />
        </button>
      </div>

      {loading ? null : (
        <div className="absolute top-4 right-4 bg-surface-container-high/90 backdrop-blur border border-border py-1 px-3 text-[10px] font-mono text-text-muted rounded shadow-md pointer-events-none hidden md:block">
          {canvasMode === 'pan' ? 'PAN: DRAG BACKGROUND | ZOOM: SCROLL' : 'DRAW: DRAG TO DEFINE COMPONENT BOUNDS'}
        </div>
      )}
    </div>
  );
};
