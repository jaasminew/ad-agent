import { create } from "zustand"

type NodeStatus = "waiting" | "running" | "done" | "error"
type NodeFeedback = "up" | "down" | null

export interface WorkflowNode {
  id: string
  label: string
  status: NodeStatus
  summary: string
  transcript: string[]
  feedback: NodeFeedback
  feedbackReason?: string
}

export interface WorkflowResult {
  id: string
  title: string
  script: string
  videoUrl: string
  createdAt: string
  preset?: string
}

export interface WorkflowFormPayload {
  productName: string
  brandIdentity: string
  productImage?: File | null
  mustHaveShots: string[]
  numberOfShots: number
  videoFormats: string[]
}

interface WorkflowState {
  nodes: WorkflowNode[]
  isRunning: boolean
  interrupted: boolean
  runVersion: number
  finalResult?: WorkflowResult
  history: WorkflowResult[]
  currentForm?: WorkflowFormPayload
  startWorkflow: (payload: WorkflowFormPayload) => number
  interruptWorkflow: () => void
  setNodeStatus: (id: string, status: NodeStatus) => void
  appendNodeTranscript: (id: string, line: string) => void
  overwriteNodeTranscript: (id: string, lines: string[]) => void
  setNodeSummary: (id: string, summary: string) => void
  toggleNodeFeedback: (id: string, feedback: NodeFeedback, reason?: string) => void
  completeWorkflow: (result: WorkflowResult) => void
  resetFinalResult: () => void
}

const baseNodes: Array<Pick<WorkflowNode, "id" | "label" | "summary">> = [
  { id: "script", label: "Scripter", summary: "Waiting for the story script." },
  {
    id: "storyboard",
    label: "Storyboard Images",
    summary: "Waiting for storyboard drafts.",
  },
  {
    id: "video-gen",
    label: "Video Generation",
    summary: "Waiting to render the footage.",
  },
  {
    id: "concat",
    label: "Video Concatenation",
    summary: "Waiting to stitch clips together.",
  },
  {
    id: "bgm",
    label: "BGM",
    summary: "Waiting to compose background music.",
  },
]

const createInitialNodes = (): WorkflowNode[] =>
  baseNodes.map((node) => ({
    ...node,
    status: "waiting",
    transcript: [],
    feedback: null,
  }))

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  nodes: createInitialNodes(),
  isRunning: false,
  interrupted: false,
  runVersion: 0,
  history: [],
  currentForm: undefined,
  finalResult: undefined,
  startWorkflow: (payload) => {
    const nextRun = get().runVersion + 1
    set({
      nodes: createInitialNodes(),
      isRunning: true,
      interrupted: false,
      runVersion: nextRun,
      currentForm: payload,
    })
    return nextRun
  },
  interruptWorkflow: () => {
    if (!get().isRunning) return
    set({ isRunning: false, interrupted: true })
  },
  setNodeStatus: (id, status) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === id
          ? {
              ...node,
              status,
            }
          : node
      ),
    })),
  appendNodeTranscript: (id, line) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === id
          ? {
              ...node,
              transcript: [...node.transcript, line],
            }
          : node
      ),
    })),
  overwriteNodeTranscript: (id, lines) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === id
          ? {
              ...node,
              transcript: lines,
            }
          : node
      ),
    })),
  setNodeSummary: (id, summary) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === id
          ? {
              ...node,
              summary,
            }
          : node
      ),
    })),
  toggleNodeFeedback: (id, feedback, reason) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === id
          ? {
              ...node,
              feedback,
              feedbackReason: reason,
            }
          : node
      ),
    })),
  completeWorkflow: (result) =>
    set((state) => ({
      isRunning: false,
      interrupted: false,
      finalResult: result,
      history: [result, ...state.history],
      nodes: state.nodes.map((node) =>
        node.status === "running" ? { ...node, status: "done" } : node
      ),
    })),
  resetFinalResult: () =>
    set(() => ({
      finalResult: undefined,
    })),
}))

export const selectNodeById = (id: string) => (state: WorkflowState) =>
  state.nodes.find((node) => node.id === id)

