import { create } from 'zustand';
import { PageData, Detection, DocLayClass } from '../types';

interface PipelineLog {
  step: string;
  page?: number;
  model?: string;
  message: string;
  percent: number;
}

interface AnnotationState {
  // Session details
  sessionId: string | null;
  status: 'idle' | 'processing' | 'results';
  modelsFound: string[];
  pages: PageData[];
  currentPageIndex: number;
  activeModelTab: 'ADE' | 'DL' | 'NM' | 'GT';
  workingDetections: Detection[];
  hoveredDetectionIndex: number | null;
  
  // Pipeline status
  isUploading: boolean;
  uploadPercent: number;
  pipelineStep: number; // 1: Upload, 2: Extract, 3: YOLO, 4: Nemotron, 5: ADE
  pipelineLogs: string[];
  
  // Intake configuration
  pdfFile: File | null;
  selectedPageRange: string;
  uploadedPdfName: string;
  pdfPageCount: number | null;
  
  // Toast notifications & Undo
  undoStack: { detection: Detection; index: number }[];
  showUndoToast: boolean;
  toastMessage: string;
  
  // Actions
  setPdfFile: (file: File) => void;
  setSelectedPageRange: (range: string) => void;
  startPipeline: () => Promise<void>;
  connectSSE: (sessionId: string) => void;
  loadSessionData: (sessionId: string) => Promise<void>;
  changePage: (index: number) => void;
  setActiveModelTab: (tab: 'ADE' | 'DL' | 'NM' | 'GT') => void;
  setHoveredDetectionIndex: (idx: number | null) => void;
  initWorkingDetections: (base: 'ADE' | 'DL' | 'NM' | 'blank') => void;
  updateDetection: (idx: number, patch: Partial<Detection>) => void;
  deleteDetection: (idx: number) => void;
  addDetection: (type: DocLayClass, bbox: [number, number, number, number]) => void;
  confirmPage: () => Promise<void>;
  clearPage: () => Promise<void>;
  triggerUndo: () => void;
  dismissToast: () => void;
  importJsonData: (jsonText: string) => string | null;
  exportGroundTruth: () => void;
  resetAllData: () => Promise<void>;
}

const BACKEND_URL = 'http://127.0.0.1:8000';

export const useAnnotationStore = create<AnnotationState>((set, get) => {
  let sseSource: EventSource | null = null;
  
  return {
    // Initial State
    sessionId: null,
    status: 'idle',
    modelsFound: [],
    pages: [],
    currentPageIndex: 0,
    activeModelTab: 'GT',
    workingDetections: [],
    hoveredDetectionIndex: null,
    
    isUploading: false,
    uploadPercent: 0,
    pipelineStep: 0,
    pipelineLogs: [],
    
    pdfFile: null,
    selectedPageRange: '',
    uploadedPdfName: '',
    pdfPageCount: null,
    
    undoStack: [],
    showUndoToast: false,
    toastMessage: '',
    
    // Setters
    setPdfFile: (file: File) => {
      set({
        pdfFile: file,
        uploadedPdfName: file.name,
        // Mock page count detection from size / name or default (e.g. 30)
        pdfPageCount: 30 
      });
    },
    

    
    setSelectedPageRange: (range: string) => {
      set({ selectedPageRange: range });
    },
    
    // Session pipeline triggers
    startPipeline: async () => {
      const { pdfFile, selectedPageRange } = get();
      if (!pdfFile || !selectedPageRange) return;
      
      set({ 
        isUploading: true, 
        uploadPercent: 0,
        pipelineStep: 1, 
        pipelineLogs: ['[SYSTEM] Initiating file uploads...'] 
      });
      
      // Simulate frontend upload percentage animation
      let progress = 0;
      const uploadTimer = setInterval(() => {
        progress += Math.floor(Math.random() * 15) + 5;
        if (progress >= 100) {
          progress = 100;
          clearInterval(uploadTimer);
          set({ uploadPercent: 100 });
        } else {
          set({ uploadPercent: progress });
        }
      }, 100);
      
      try {
        const formData = new FormData();
        formData.append('pdf', pdfFile);
        formData.append('pages', selectedPageRange);
        
        const response = await fetch(`${BACKEND_URL}/api/session/start`, {
          method: 'POST',
          body: formData,
        });
        
        if (!response.ok) {
          throw new Error('Failed to start session pipeline.');
        }
        
        const data = await response.json();
        clearInterval(uploadTimer);
        
        set({
          sessionId: data.session_id,
          modelsFound: data.models_found,
          status: 'processing',
          isUploading: false,
          uploadPercent: 100,
          pipelineStep: 2,
          pipelineLogs: [
            ...get().pipelineLogs,
            `[SYSTEM] Session started: ${data.session_id}`,
            `[SYSTEM] Models detected: ${data.models_found.join(', ')}`,
            `[SYSTEM] Launching sequential evaluation pipeline...`
          ]
        });
        
        // Connect to SSE for status updates
        get().connectSSE(data.session_id);
        
      } catch (err: any) {
        clearInterval(uploadTimer);
        set({
          isUploading: false,
          pipelineLogs: [...get().pipelineLogs, `[ERROR] Failed to start session: ${err.message}`]
        });
      }
    },
    
    connectSSE: (sessionId: string) => {
      if (sseSource) {
        sseSource.close();
      }
      
      sseSource = new EventSource(`${BACKEND_URL}/api/session/${sessionId}/status`);
      
      sseSource.onmessage = (event) => {
        try {
          const logData = JSON.parse(event.data) as PipelineLog;
          
          let stepNum = get().pipelineStep;
          if (logData.step.includes('model_a')) stepNum = 3;
          else if (logData.step.includes('model_b')) stepNum = 4;
          else if (logData.step.includes('model_c')) stepNum = 5;
          
          set((state) => ({
            pipelineStep: stepNum,
            pipelineLogs: [...state.pipelineLogs, logData.message]
          }));
          if (logData.step === 'complete') {
            if (sseSource) sseSource.close();
            set({ status: 'results' });
            get().loadSessionData(sessionId);
          } else if (logData.step === 'error') {
            if (sseSource) sseSource.close();
            set({ status: 'idle' });
            alert(`Pipeline failed: ${logData.message}`);
          }
        } catch (e) {
          console.error('Failed to parse SSE data', e);
        }
      };
      
      sseSource.onerror = (e) => {
        console.error('SSE Connection error', e);
        if (sseSource) sseSource.close();
        const { status, pipelineLogs } = get();
        if (status === 'processing') {
          set({
            status: 'idle',
            pipelineLogs: [...pipelineLogs, '[ERROR] SSE connection lost. The backend server might be unresponsive or has encountered an error.']
          });
          alert('Backend connection error: The annotation pipeline failed or disconnected. Please check the backend console.');
        }
      };
    },
    
    loadSessionData: async (sessionId: string) => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/session/${sessionId}/data`);
        if (!response.ok) {
          throw new Error('Failed to load session details.');
        }
        
        const data = await response.json();
        // data matches Record<string, PageData>
        const pagesList = Object.values(data) as PageData[];
        
        set({
          pages: pagesList,
          currentPageIndex: 0,
          status: 'results',
          activeModelTab: 'GT'
        });
        
        // Populate first page detections
        if (pagesList.length > 0) {
          const firstPage = pagesList[0];
          set({
            workingDetections: firstPage.ground_truth !== null 
              ? firstPage.ground_truth 
              : firstPage.model_c.detections
          });
        }
      } catch (err: any) {
        console.error(err);
        alert(`Failed to load session results: ${err.message}`);
      }
    },
    
    changePage: (index: number) => {
      const { pages } = get();
      if (index >= 0 && index < pages.length) {
        const targetPage = pages[index];
        set({
          currentPageIndex: index,
          workingDetections: targetPage.ground_truth !== null 
            ? targetPage.ground_truth 
            : targetPage.model_c.detections,
          hoveredDetectionIndex: null,
          undoStack: []
        });
      }
    },
    
    setActiveModelTab: (tab: 'ADE' | 'DL' | 'NM' | 'GT') => {
      set({ activeModelTab: tab });
    },
    
    setHoveredDetectionIndex: (idx: number | null) => {
      set({ hoveredDetectionIndex: idx });
    },
    
    initWorkingDetections: (base: 'ADE' | 'DL' | 'NM' | 'blank') => {
      const { pages, currentPageIndex } = get();
      const currentPage = pages[currentPageIndex];
      if (!currentPage) return;
      
      let nextDetections: Detection[] = [];
      if (base === 'ADE') {
        nextDetections = currentPage.model_c.detections.map(d => ({ ...d, model: 'ADE-DPT2' }));
      } else if (base === 'DL') {
        nextDetections = currentPage.model_a.detections.map(d => ({ ...d, model: 'DocLayoutYOLO' }));
      } else if (base === 'NM') {
        nextDetections = currentPage.model_b.detections.map(d => ({ ...d, model: 'Nemotron-Parse-v1.1' }));
      } else {
        nextDetections = [];
      }
      
      set({
        workingDetections: nextDetections,
        activeModelTab: 'GT', // automatically return focus to GT editing
        toastMessage: `Initialized workspace from ${base === 'blank' ? 'blank slate' : base}`,
        showUndoToast: true
      });
      
      setTimeout(() => {
        if (get().toastMessage.includes(`Initialized workspace`)) {
          set({ showUndoToast: false });
        }
      }, 4000);
    },
    
    updateDetection: (idx: number, patch: Partial<Detection>) => {
      set((state) => {
        const updated = [...state.workingDetections];
        updated[idx] = {
          ...updated[idx],
          ...patch,
          model: 'human' // Mark as human curated
        };
        return { workingDetections: updated };
      });
    },
    
    deleteDetection: (idx: number) => {
      const { workingDetections } = get();
      const target = workingDetections[idx];
      if (!target) return;
      
      set((state) => ({
        undoStack: [{ detection: target, index: idx }, ...state.undoStack],
        workingDetections: state.workingDetections.filter((_, i) => i !== idx),
        toastMessage: `Removed detection #${idx + 1} (${target.type})`,
        showUndoToast: true
      }));
      
      setTimeout(() => {
        if (get().toastMessage.includes(`Removed detection`)) {
          set({ showUndoToast: false });
        }
      }, 4000);
    },
    
    addDetection: (type: DocLayClass, bbox: [number, number, number, number]) => {
      const newDet: Detection = {
        id: `${Date.now()}-${Math.random()}`,
        type,
        bbox,
        model: 'human'
      };
      
      set((state) => ({
        workingDetections: [...state.workingDetections, newDet],
        toastMessage: `Added new ${type} detection`,
        showUndoToast: true
      }));
      
      setTimeout(() => {
        if (get().toastMessage.includes(`Added new`)) {
          set({ showUndoToast: false });
        }
      }, 4000);
    },
    
    confirmPage: async () => {
      const { sessionId, pages, currentPageIndex, workingDetections } = get();
      if (!sessionId || pages.length === 0) return;
      
      const currentPage = pages[currentPageIndex];
      const pageKey = String(currentPage.page);
      
      // Update local pages state
      const updatedPages = [...pages];
      updatedPages[currentPageIndex] = {
        ...currentPage,
        ground_truth: workingDetections.map(d => ({ ...d, model: 'human' }))
      };
      
      set({ pages: updatedPages });
      
      // Post to FastAPI endpoint
      try {
        const requestData: Record<string, { ground_truth: Detection[] }> = {};
        requestData[pageKey] = {
          ground_truth: workingDetections.map(d => ({ ...d, model: 'human' }))
        };
        
        const response = await fetch(`${BACKEND_URL}/api/session/${sessionId}/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pages_data: requestData })
        });
        
        if (!response.ok) {
          throw new Error('Failed to save to backend disk.');
        }
        
        set({
          toastMessage: `Confirmed page ${currentPage.page} ground truth! Saved to disk.`,
          showUndoToast: true
        });
        
        setTimeout(() => {
          if (get().toastMessage.includes(`Confirmed page`)) {
            set({ showUndoToast: false });
          }
        }, 4000);
      } catch (err: any) {
        alert(`Save failed: ${err.message}`);
      }
    },
    
    clearPage: async () => {
      const { sessionId, pages, currentPageIndex } = get();
      if (!sessionId || pages.length === 0) return;
      
      const currentPage = pages[currentPageIndex];
      const pageKey = String(currentPage.page);
      
      const updatedPages = [...pages];
      updatedPages[currentPageIndex] = {
        ...currentPage,
        ground_truth: null
      };
      
      set({
        pages: updatedPages,
        workingDetections: [],
      });
      
      try {
        const requestData: Record<string, { ground_truth: null }> = {};
        requestData[pageKey] = { ground_truth: null };
        
        await fetch(`${BACKEND_URL}/api/session/${sessionId}/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pages_data: requestData })
        });
        
        set({
          toastMessage: `Unconfirmed page ${currentPage.page} and cleared workspace.`,
          showUndoToast: true
        });
        
        setTimeout(() => {
          if (get().toastMessage.includes(`Unconfirmed page`)) {
            set({ showUndoToast: false });
          }
        }, 4000);
      } catch (err: any) {
        console.error(err);
      }
    },
    
    triggerUndo: () => {
      const { undoStack } = get();
      if (undoStack.length === 0) return;
      
      const [lastItem, ...remainingStack] = undoStack;
      
      set((state) => {
        const restored = [...state.workingDetections];
        restored.splice(lastItem.index, 0, lastItem.detection);
        return {
          undoStack: remainingStack,
          workingDetections: restored,
          showUndoToast: false,
          toastMessage: `Restored detection: ${lastItem.detection.type}`
        };
      });
    },
    
    dismissToast: () => {
      set({ showUndoToast: false });
    },
    
    importJsonData: (jsonText: string): string | null => {
      try {
        const parsed = JSON.parse(jsonText);
        if (typeof parsed !== 'object' || parsed === null) {
          return 'Invalid JSON format: root must be an object.';
        }
        
        // Map simple export back to our store pages
        set((state) => {
          const updatedPages = state.pages.map((p) => {
            const pageKey = String(p.page);
            if (pageKey in parsed) {
              return {
                ...p,
                ground_truth: parsed[pageKey]
              };
            }
            return p;
          });
          
          // Refresh working detections if current page updated
          const currentPage = updatedPages[state.currentPageIndex];
          const nextWorking = currentPage.ground_truth !== null 
            ? currentPage.ground_truth 
            : currentPage.model_c.detections;
            
          return {
            pages: updatedPages,
            workingDetections: nextWorking
          };
        });
        
        return null;
      } catch (e: any) {
        return `Failed to parse JSON: ${e.message || e}`;
      }
    },
    
    exportGroundTruth: () => {
      const { sessionId } = get();
      if (!sessionId) return;
      
      // Request download from backend export route
      const link = document.createElement('a');
      link.href = `${BACKEND_URL}/api/session/${sessionId}/export`;
      link.download = 'ground_truth.json';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
    
    resetAllData: async () => {
      const { sessionId } = get();
      if (sessionId) {
        try {
          await fetch(`${BACKEND_URL}/api/session/${sessionId}`, { method: 'DELETE' });
        } catch (e) {
          console.error('Failed to clear session on backend', e);
        }
      }
      
      if (sseSource) {
        sseSource.close();
        sseSource = null;
      }
      
      set({
        sessionId: null,
        status: 'idle',
        modelsFound: [],
        pages: [],
        currentPageIndex: 0,
        activeModelTab: 'GT',
        workingDetections: [],
        hoveredDetectionIndex: null,
        
        isUploading: false,
        uploadPercent: 0,
        pipelineStep: 0,
        pipelineLogs: [],
        
        pdfFile: null,
        selectedPageRange: '',
        uploadedPdfName: '',
        pdfPageCount: null,
        
        undoStack: [],
        showUndoToast: false,
        toastMessage: ''
      });
    }
  };
});
