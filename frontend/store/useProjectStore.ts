"use client";

import { create } from "zustand";
import { builder } from "@/api_requests/builder";

const DEFAULT_APP = `export default function App() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <h1 className="text-3xl  font-[600] text-gray-800">
        Describe your website to get started
      </h1>
    </div>
  );
}`;

const DEFAULT_FILES: Record<string, string> = {
  "/App.tsx": DEFAULT_APP,
};

type Message = { role: string; content: string };

let syncTimer: ReturnType<typeof setTimeout> | null = null;

function debouncedSync() {
  if (syncTimer) clearTimeout(syncTimer);
  syncTimer = setTimeout(() => {
    const { projectId, files, messages } = useProjectStore.getState();
    if (!projectId) return;
    builder.update(projectId, { files, messages }).catch((err) => {
      console.error("Failed to sync builder project:", err);
    });
  }, 1000);
}

const initialProjectState = {
  activePackId: null as string | null,
  projectId: null as string | null,
  files: { ...DEFAULT_FILES },
  messages: [] as Message[],
  isGenerating: false,
  selectedStyle: null as string | null,
  liveUrl: null as string | null,
  fileHistory: [] as Array<Record<string, string>>,
};

type ProjectState = typeof initialProjectState & {
  setActivePack: (packId: string) => void;
  setProjectId: (id: string) => void;
  setSelectedStyle: (style: string) => void;
  setLiveUrl: (url: string | null) => void;
  hydrate: (data: {
    files: Record<string, string>;
    messages: Message[];
    projectId: string;
    liveUrl?: string | null;
  }) => void;
  updateFiles: (newFiles: Record<string, string>) => void;
  setMessages: (messages: Message[]) => void;
  setIsGenerating: (v: boolean) => void;
  syncToBackend: () => void;
  pushToHistory: () => void;
  undoLastChange: () => void;
  reset: () => void;
};

export const useProjectStore = create<ProjectState>((set, get) => ({
  ...initialProjectState,

  setActivePack: (packId) => {
    if (get().activePackId === packId) return;
    set({
      activePackId: packId,
      projectId: null,
      files: { ...DEFAULT_FILES },
      messages: [],
      isGenerating: false,
      selectedStyle: null,
      liveUrl: null,
      fileHistory: [],
    });
  },

  setProjectId: (id) => set({ projectId: id }),

  setSelectedStyle: (style) => set({ selectedStyle: style }),

  setLiveUrl: (url) => set({ liveUrl: url }),

  hydrate: ({ files, messages, projectId, liveUrl }) => {
    const hasFiles = files && Object.keys(files).length > 0;
    set({
      projectId,
      files: hasFiles ? files : { ...DEFAULT_FILES },
      messages: messages ?? [],
      liveUrl: liveUrl ?? null,
    });
  },

  updateFiles: (newFiles) => {
    set((state) => ({
      files: { ...state.files, ...newFiles },
    }));
    debouncedSync();
  },

  setMessages: (messages) => {
    set({ messages });
    debouncedSync();
  },

  setIsGenerating: (v) => set({ isGenerating: v }),

  syncToBackend: () => debouncedSync(),

  pushToHistory: () => {
    const { files, fileHistory } = get();
    const snapshot = { ...files };
    set({ fileHistory: [snapshot, ...fileHistory].slice(0, 10) });
  },

  undoLastChange: () => {
    const { fileHistory } = get();
    if (fileHistory.length === 0) return;
    const [prev, ...rest] = fileHistory;
    set({ files: prev, fileHistory: rest });
    debouncedSync();
  },

  reset: () => {
    if (syncTimer) clearTimeout(syncTimer);
    set({ ...initialProjectState, files: { ...DEFAULT_FILES } });
  },
}));
