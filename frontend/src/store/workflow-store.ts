import { create } from "zustand";
import * as api from "@/services/api";

type NodeStatus = "waiting" | "running" | "done" | "error";
type NodeFeedback = "up" | "down" | null;

export type InterruptionType =
  | "workflow_failed"
  | "network_error"
  | "api_error"
  | "user_cancelled"
  | "unknown";

export interface InterruptionDetails {
  type: InterruptionType;
  title: string;
  detail: string;
  stageId?: string;
}

export interface ChecklistItemBlock {
  slug: string;
  description: string;
  checked: boolean;
  optional?: boolean;
}

export interface ChecklistStats {
  totalItems: number;
  checkedItems: number;
  mandatoryItems: number;
  mandatoryChecked: number;
  progress: number;
  mandatoryComplete: boolean;
}

export interface ChecklistContentBlock {
  type: "checklist";
  items: ChecklistItemBlock[];
  summary: string;
  stats: ChecklistStats;
}

export interface TextContentBlock {
  type: "text";
  content: string;
}

export type ThoughtContentBlock = TextContentBlock | ChecklistContentBlock;

export interface TranscriptEntry {
  id: string;
  message: string;
  contentBlocks?: ThoughtContentBlock[];
  metadata?: {
    outputType?: string;
    checklistSummary?: string;
  };
}

export interface WorkflowNode {
  id: string;
  label: string;
  status: NodeStatus;
  summary: string;
  transcript: TranscriptEntry[];
  feedback: NodeFeedback;
  feedbackReason?: string;
}

export interface WorkflowResult {
  id: string;
  title: string;
  script: string;
  videoUrl: string;
  createdAt: string;
  preset?: string;
}

export interface WorkflowFormPayload {
  productName: string;
  brandIdentity: string;
  productImage?: File | null;
  mustHaveShots: string[];
  numberOfShots: number;
  videoFormats: string[];
}

interface WorkflowState {
  nodes: WorkflowNode[];
  isRunning: boolean;
  interrupted: boolean;
  interruptionDetails?: InterruptionDetails;
  runVersion: number;
  finalResult?: WorkflowResult;
  history: WorkflowResult[];
  currentForm?: WorkflowFormPayload;
  currentTaskId?: string;
  startWorkflow: (payload: WorkflowFormPayload) => Promise<number>;
  restartWorkflowFromStage: (stage: api.WorkflowStage) => Promise<void>;
  interruptWorkflow: () => Promise<void>;
  setNodeStatus: (id: string, status: NodeStatus) => void;
  appendNodeTranscript: (id: string, entry: TranscriptEntry) => void;
  overwriteNodeTranscript: (id: string, entries: TranscriptEntry[]) => void;
  setNodeSummary: (id: string, summary: string) => void;
  toggleNodeFeedback: (
    id: string,
    feedback: NodeFeedback,
    reason?: string,
  ) => void;
  completeWorkflow: (result: WorkflowResult) => void;
  resetFinalResult: () => void;
}

const baseNodes: Array<Pick<WorkflowNode, "id" | "label" | "summary">> = [
  {
    id: "script_gen_agent",
    label: "Scripter",
    summary: "Waiting for the story script.",
  },
  {
    id: "storyboard_gen_agent",
    label: "Storyboard Images",
    summary: "Waiting for storyboard drafts.",
  },
  {
    id: "video_generator",
    label: "Video Generation",
    summary: "Waiting to render the footage.",
  },
  {
    id: "video_concatenater",
    label: "Video Concatenation",
    summary: "Waiting to stitch clips together.",
  },
  {
    id: "bgm_generator",
    label: "BGM",
    summary: "Waiting to compose background music.",
  },
];

// Stage mapping: backend stage -> frontend node id
const stageToNodeId: Record<string, string> = {
  script_gen_agent: "script_gen_agent",
  storyboard_gen_agent: "storyboard_gen_agent",
  video_generator: "video_generator",
  video_concatenater: "video_concatenater",
  bgm_generator: "bgm_generator",
};

const nodeDisplayNames = baseNodes.reduce<Record<string, string>>(
  (acc, node) => {
    acc[node.id] = node.label;
    return acc;
  },
  {},
);

const MAX_ALERT_TITLE_LENGTH = 80;
const FALLBACK_ERROR_MESSAGE = "Workflow failed mid-run";
const UNKNOWN_INTERRUPTION_MESSAGE = "Workflow paused unexpectedly";

const formatAlertTitle = (text: string): string => {
  if (!text) return "Workflow stopped";
  const cleaned = text.trim().replace(/\s+/g, " ");
  if (cleaned.length <= MAX_ALERT_TITLE_LENGTH) {
    return cleaned.replace(/[.。!！?？]+$/, "");
  }
  return `${cleaned.slice(0, MAX_ALERT_TITLE_LENGTH - 1)}…`;
};

const extractErrorMessage = (error: unknown): string => {
  if (!error) return "";
  if (error instanceof api.APIError) {
    const detail = error.details;
    if (detail) {
      if (typeof detail.detail === "string" && detail.detail.trim().length) {
        return detail.detail.trim();
      }
      if (typeof detail.message === "string" && detail.message.trim().length) {
        return detail.message.trim();
      }
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  return "";
};

const friendlyStageFailureMessage = (stage?: string): string | undefined => {
  if (!stage || stage === "completed") {
    return undefined;
  }
  const display = nodeDisplayNames[stage] ?? stage;
  return `${display} failed`;
};

const buildDetailsFromMessage = (
  type: InterruptionType,
  message?: string,
  fallback = FALLBACK_ERROR_MESSAGE,
  stageId?: string,
): InterruptionDetails => {
  const usableMessage = message?.trim().length ? message.trim() : fallback;
  return {
    type,
    title: formatAlertTitle(usableMessage),
    detail: usableMessage,
    stageId,
  };
};

const buildDetailsFromError = (
  type: InterruptionType,
  error: unknown,
  fallback?: string,
  stageId?: string,
): InterruptionDetails =>
  buildDetailsFromMessage(type, extractErrorMessage(error), fallback, stageId);

const fetchFailureDetails = async (
  taskId: string,
): Promise<InterruptionDetails> => {
  try {
    const taskData = await api.queryTask(taskId);
    const messageFromBackend =
      typeof taskData.error_message === "string"
        ? taskData.error_message
        : undefined;
    const fallbackMessage =
      friendlyStageFailureMessage(taskData.stage) ?? FALLBACK_ERROR_MESSAGE;
    const stageId =
      taskData.stage && taskData.stage !== "completed" ? taskData.stage : undefined;
    return buildDetailsFromMessage(
      "workflow_failed",
      messageFromBackend,
      fallbackMessage,
      stageId,
    );
  } catch (error) {
    return buildDetailsFromError(
      "workflow_failed",
      error,
      FALLBACK_ERROR_MESSAGE,
    );
  }
};

const createInitialNodes = (): WorkflowNode[] =>
  baseNodes.map((node) => ({
    ...node,
    status: "waiting",
    transcript: [],
    feedback: null,
  }));

const generateTranscriptId = () => {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const CHECKLIST_CODE_BLOCK_REGEX =
  /```[\t ]*\n?[\t ]*Checklist:\s*\n[\s\S]*?```/gi;

const stripChecklistCodeBlocks = (text: string): string => {
  if (!text) return text;
  const withoutBlocks = text.replace(CHECKLIST_CODE_BLOCK_REGEX, "").trim();
  return withoutBlocks.replace(/\n{3,}/g, "\n\n").trim();
};

const normalizeChecklistStats = (
  block: Record<string, unknown>,
): ChecklistStats => ({
  totalItems: Number(block.total_items ?? block.totalItems ?? 0),
  checkedItems: Number(block.checked_items ?? block.checkedItems ?? 0),
  mandatoryItems: Number(block.mandatory_items ?? block.mandatoryItems ?? 0),
  mandatoryChecked: Number(
    block.mandatory_checked ?? block.mandatoryChecked ?? 0,
  ),
  progress: Number(block.progress ?? 0),
  mandatoryComplete: Boolean(
    block.mandatory_complete ?? block.mandatoryComplete ?? false,
  ),
});

const normalizeChecklistItem = (
  item: Record<string, unknown>,
  index: number,
): ChecklistItemBlock => ({
  slug:
    typeof item.slug === "string" && item.slug.length
      ? item.slug
      : `item_${index}`,
  description: typeof item.description === "string" ? item.description : "",
  checked: Boolean(item.checked),
  optional: Boolean(item.optional),
});

const transformContentBlock = (
  block: Record<string, unknown>,
): ThoughtContentBlock | null => {
  if (!block || typeof block !== "object") return null;

  const blockType = typeof block.type === "string" ? block.type : undefined;

  if (blockType === "text") {
    return {
      type: "text",
      content: typeof block.content === "string" ? block.content : "",
    };
  }

  if (blockType === "checklist" && Array.isArray(block.items)) {
    const items = block.items.map((item, idx) =>
      normalizeChecklistItem((item as Record<string, unknown>) ?? {}, idx),
    );

    return {
      type: "checklist",
      items,
      summary: typeof block.summary === "string" ? block.summary : "",
      stats: normalizeChecklistStats(block),
    };
  }

  return null;
};

const buildTranscriptEntry = (
  message: string,
  output?: Record<string, unknown>,
): TranscriptEntry => {
  const entry: TranscriptEntry = {
    id: generateTranscriptId(),
    message,
  };

  if (!output || typeof output !== "object") {
    return entry;
  }

  const outputType = typeof output.type === "string" ? output.type : undefined;
  const rawBlocks = Array.isArray(output.content_blocks)
    ? output.content_blocks
    : [];
  const contentBlocks = rawBlocks
    .map((block) =>
      transformContentBlock((block as Record<string, unknown>) ?? {}),
    )
    .filter((block): block is ThoughtContentBlock => Boolean(block));

  if (outputType === "thought" && contentBlocks.length) {
    entry.contentBlocks = contentBlocks;
    entry.metadata = {
      outputType,
      checklistSummary:
        typeof output.checklist_summary === "string"
          ? output.checklist_summary
          : undefined,
    };

    const cleanedMessage = stripChecklistCodeBlocks(entry.message);
    const fallback = entry.message.includes("💭")
      ? "💭 Checklist updated."
      : "Checklist updated.";
    entry.message = cleanedMessage.length ? cleanedMessage : fallback;
  }

  return entry;
};

const removeChecklistBlocksFromEntry = (
  entry: TranscriptEntry,
): TranscriptEntry => {
  if (!entry.contentBlocks || entry.contentBlocks.length === 0) {
    return entry;
  }

  const filteredBlocks = entry.contentBlocks.filter(
    (block) => block.type !== "checklist",
  );
  if (filteredBlocks.length === entry.contentBlocks.length) {
    return entry;
  }

  const nextEntry: TranscriptEntry = {
    ...entry,
    contentBlocks: filteredBlocks.length > 0 ? filteredBlocks : undefined,
  };

  if (entry.metadata) {
    const { checklistSummary, ...rest } = entry.metadata;
    void checklistSummary;
    nextEntry.metadata = Object.keys(rest).length > 0 ? rest : undefined;
  }

  return nextEntry;
};

// AbortController for SSE streaming
let streamAbortController: AbortController | null = null;

export const useWorkflowStore = create<WorkflowState>((set, get) => {
  const markRunInterrupted = (details?: InterruptionDetails) => {
    const resolvedDetails =
      details ??
      buildDetailsFromMessage(
        "unknown",
        "",
        UNKNOWN_INTERRUPTION_MESSAGE,
      );
    set({
      isRunning: false,
      interrupted: true,
      interruptionDetails: resolvedDetails,
    });
  };

  return {
    nodes: createInitialNodes(),
    isRunning: false,
    interrupted: false,
    interruptionDetails: undefined,
    runVersion: 0,
    history: [],
    currentForm: undefined,
    currentTaskId: undefined,
    finalResult: undefined,

    startWorkflow: async (payload) => {
      const nextRun = get().runVersion + 1;
      set({
        nodes: createInitialNodes(),
        isRunning: true,
        interrupted: false,
        interruptionDetails: undefined,
        runVersion: nextRun,
        currentForm: payload,
        currentTaskId: undefined,
        finalResult: undefined,
      });

      try {
        let productImageUrl = "";
        if (payload.productImage) {
          try {
            productImageUrl = await api.uploadProductImage(
              payload.productImage,
            );
          } catch (error) {
            console.error("Failed to upload product image:", error);
          }
        }

        const shotsValue =
          payload.mustHaveShots.length > 0
            ? payload.mustHaveShots.join(", ")
            : undefined;

        const createRequest: api.CreateTaskRequest = {
          product_name: payload.productName,
          brand_identity: payload.brandIdentity,
          product_images: productImageUrl,
          video_format: payload.videoFormats.join(", "),
          max_shots: payload.numberOfShots,
        };
        if (shotsValue) {
          createRequest.must_have_shots = shotsValue;
        }

        const { task_id } = await api.createTask(createRequest);
        set({ currentTaskId: task_id });

        streamAbortController = new AbortController();

        try {
          for await (const event of api.streamTaskUpdates(
            task_id,
            streamAbortController.signal,
          )) {
            if ("status" in event) {
              const completeEvent = event as api.SSECompleteEvent;
              if (completeEvent.status === "completed") {
                const taskData = await api.queryTask(task_id);
                const finalVideoUrl =
                  taskData.final_video_with_bgm_url ||
                  taskData.final_video_url ||
                  "";

                const result: WorkflowResult = {
                  id: task_id,
                  title: taskData.product_name,
                  script: taskData.final_script || "",
                  videoUrl: finalVideoUrl,
                  createdAt: taskData.created_at,
                };
                get().completeWorkflow(result);
              } else if (completeEvent.status === "failed") {
                const runningNode = get().nodes.find(
                  (node) => node.status === "running",
                );
                if (runningNode) {
                  get().setNodeStatus(runningNode.id, "error");
                }
                const failureDetails = await fetchFailureDetails(task_id);
                markRunInterrupted(failureDetails);
              } else if (completeEvent.status === "cancelled") {
              markRunInterrupted(
                buildDetailsFromMessage(
                  "user_cancelled",
                  "Workflow cancelled",
                  "Workflow cancelled",
                ),
              );
              }
              break;
            } else {
              const contentEvent = event as api.SSEContentEvent;
              const { data } = contentEvent;

              if (contentEvent.type === "llm_output") {
                const llmData = data as api.LLMOutputData;
                const nodeId = stageToNodeId[llmData.stage];
                if (nodeId) {
                  get().setNodeStatus(nodeId, "running");
                  get().appendNodeTranscript(
                    nodeId,
                    buildTranscriptEntry(llmData.message, llmData.output),
                  );
                  if (llmData.reasoning) {
                    get().appendNodeTranscript(
                      nodeId,
                      buildTranscriptEntry(`Reasoning: ${llmData.reasoning}`),
                    );
                  }
                }
              } else if (contentEvent.type === "tool_calling") {
                const toolData = data as api.ToolCallingData;
                const nodeId = stageToNodeId[toolData.stage];
                if (nodeId) {
                  get().appendNodeTranscript(
                    nodeId,
                    buildTranscriptEntry(
                      `🔧 ${toolData.tool_name}: ${toolData.success ? "✓" : "✗"}`,
                    ),
                  );
                  if (toolData.error) {
                    get().appendNodeTranscript(
                      nodeId,
                      buildTranscriptEntry(`Error: ${toolData.error}`),
                    );
                  }
                  if (!toolData.success) {
                    get().setNodeStatus(nodeId, "error");
                  }
                }
              }
            }
          }
        } catch (error) {
          if (!(error instanceof Error && error.name === "AbortError")) {
            console.error("Streaming error:", error);
            markRunInterrupted(
              buildDetailsFromError(
                "network_error",
                error,
                "Connection to the agent dropped",
              ),
            );
          }
        }
      } catch (error) {
        console.error("Failed to start workflow:", error);
        markRunInterrupted(
          buildDetailsFromError("api_error", error, "Failed to start workflow"),
        );
      }

      return nextRun;
    },

    restartWorkflowFromStage: async (stage) => {
      const { currentTaskId, isRunning } = get();

      if (!currentTaskId) {
        throw new Error("No current task to restart");
      }

      if (isRunning) {
        throw new Error(
          "Cannot restart while workflow is running. Please cancel first.",
        );
      }

      const stageOrder = [
        "script_gen_agent",
        "storyboard_gen_agent",
        "video_generator",
        "video_concatenater",
        "bgm_generator",
      ];
      const startIndex = stageOrder.indexOf(stage);

      set((state) => ({
        isRunning: true,
        interrupted: false,
        interruptionDetails: undefined,
        finalResult: undefined,
        nodes: state.nodes.map((node, idx) => {
          if (idx >= startIndex) {
            return {
              ...node,
              status: "waiting" as NodeStatus,
              transcript: [],
            };
          }
          return node;
        }),
      }));

      try {
        await api.restartTask(currentTaskId, { stage });
        streamAbortController = new AbortController();

        try {
          for await (const event of api.streamTaskUpdates(
            currentTaskId,
            streamAbortController.signal,
          )) {
            if ("status" in event) {
              const completeEvent = event as api.SSECompleteEvent;
              if (completeEvent.status === "completed") {
                const taskData = await api.queryTask(currentTaskId);
                const finalVideoUrl =
                  taskData.final_video_with_bgm_url ||
                  taskData.final_video_url ||
                  "";

                const result: WorkflowResult = {
                  id: currentTaskId,
                  title: taskData.product_name,
                  script: taskData.final_script || "",
                  videoUrl: finalVideoUrl,
                  createdAt: taskData.created_at,
                };
                get().completeWorkflow(result);
              } else if (completeEvent.status === "failed") {
                const runningNode = get().nodes.find(
                  (node) => node.status === "running",
                );
                if (runningNode) {
                  get().setNodeStatus(runningNode.id, "error");
                }
                const failureDetails = await fetchFailureDetails(currentTaskId);
                markRunInterrupted(failureDetails);
              } else if (completeEvent.status === "cancelled") {
              markRunInterrupted(
                buildDetailsFromMessage(
                  "user_cancelled",
                  "Workflow cancelled",
                  "Workflow cancelled",
                ),
              );
              }
              break;
            } else {
              const contentEvent = event as api.SSEContentEvent;
              const { data } = contentEvent;

              if (contentEvent.type === "llm_output") {
                const llmData = data as api.LLMOutputData;
                const nodeId = stageToNodeId[llmData.stage];
                if (nodeId) {
                  get().setNodeStatus(nodeId, "running");
                  get().appendNodeTranscript(
                    nodeId,
                    buildTranscriptEntry(llmData.message, llmData.output),
                  );
                  if (llmData.reasoning) {
                    get().appendNodeTranscript(
                      nodeId,
                      buildTranscriptEntry(`Reasoning: ${llmData.reasoning}`),
                    );
                  }
                }
              } else if (contentEvent.type === "tool_calling") {
                const toolData = data as api.ToolCallingData;
                const nodeId = stageToNodeId[toolData.stage];
                if (nodeId) {
                  get().appendNodeTranscript(
                    nodeId,
                    buildTranscriptEntry(
                      `🔧 ${toolData.tool_name}: ${toolData.success ? "✓" : "✗"}`,
                    ),
                  );
                  if (toolData.error) {
                    get().appendNodeTranscript(
                      nodeId,
                      buildTranscriptEntry(`Error: ${toolData.error}`),
                    );
                  }
                  if (!toolData.success) {
                    get().setNodeStatus(nodeId, "error");
                  }
                }
              }
            }
          }
        } catch (error) {
          if (!(error instanceof Error && error.name === "AbortError")) {
            console.error("Streaming error:", error);
            markRunInterrupted(
              buildDetailsFromError(
                "network_error",
                error,
                "Connection to the agent dropped",
              ),
            );
          }
        }
      } catch (error) {
        console.error("Failed to restart workflow:", error);
        markRunInterrupted(
          buildDetailsFromError(
            "api_error",
            error,
            "Failed to restart workflow",
          ),
        );

        if (error instanceof api.APIError) {
          throw error;
        }
        throw new Error(
          error instanceof Error ? error.message : "Unknown error",
        );
      }
    },

    interruptWorkflow: async () => {
      const { currentTaskId, isRunning } = get();
      if (!isRunning || !currentTaskId) return;

      // Cancel streaming
      if (streamAbortController) {
        streamAbortController.abort();
        streamAbortController = null;
      }

      // Cancel backend task
      try {
        await api.cancelTask(currentTaskId);
      } catch (error) {
        console.error("Failed to cancel task:", error);
      }

      markRunInterrupted(
        buildDetailsFromMessage(
          "user_cancelled",
          "Workflow cancelled",
          "Workflow cancelled",
        ),
      );
    },
    setNodeStatus: (id, status) =>
      set((state) => {
        const nodes = state.nodes.map<WorkflowNode>((node) => {
          if (node.id === id) {
            return {
              ...node,
              status,
            };
          }

          if (status === "running" && node.status === "running") {
            return {
              ...node,
              status: "done",
            };
          }

          return node;
        });

        return { nodes };
      }),
    appendNodeTranscript: (id, entry) =>
      set((state) => ({
        nodes: state.nodes.map((node) => {
          if (node.id !== id) {
            return node;
          }

          const entryHasChecklist =
            entry.contentBlocks?.some((block) => block.type === "checklist") ??
            false;

          const sanitizedTranscript = entryHasChecklist
            ? node.transcript.map((existingEntry) =>
                removeChecklistBlocksFromEntry(existingEntry),
              )
            : node.transcript;

          return {
            ...node,
            transcript: [...sanitizedTranscript, entry],
          };
        }),
      })),
    overwriteNodeTranscript: (id, entries) =>
      set((state) => ({
        nodes: state.nodes.map((node) =>
          node.id === id
            ? {
                ...node,
                transcript: entries,
              }
            : node,
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
            : node,
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
            : node,
        ),
      })),
    completeWorkflow: (result) =>
      set((state) => ({
        isRunning: false,
        interrupted: false,
        interruptionDetails: undefined,
        finalResult: result,
        history: [result, ...state.history],
        nodes: state.nodes.map((node) =>
          node.status === "running" ? { ...node, status: "done" } : node,
        ),
      })),
    resetFinalResult: () =>
      set(() => ({
        finalResult: undefined,
      })),
  };
});

export const selectNodeById = (id: string) => (state: WorkflowState) =>
  state.nodes.find((node) => node.id === id);
