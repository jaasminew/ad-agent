/**
 * AD Agent Backend API Service
 * Handles all communication with the FastAPI backend
 */

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// API Types
export interface CreateTaskRequest {
  product_name: string
  brand_identity: string
  must_have_shots?: string  // comma-separated (optional)
  product_images: string
  video_format: string
  max_shots: number
}

export interface CreateTaskResponse {
  task_id: string
}

export interface CancelTaskResponse {
  success: boolean
  message: string
}

export type TaskStatus = 'created' | 'processing' | 'completed' | 'failed' | 'cancelled'
export type WorkflowStage = 'script_gen_agent' | 'storyboard_gen_agent' | 'video_generator' | 'video_concatenater' | 'bgm_generator' | 'completed'
export type ContentType = 'llm_output' | 'tool_calling'

export interface LLMOutputData {
  stage: string
  message: string
  reasoning?: string
  output: Record<string, any>
}

export interface ToolCallingData {
  tool_name: string
  stage: string
  input: Record<string, any>
  output: Record<string, any>
  success: boolean
  error?: string
}

export interface ContentBlock {
  type: ContentType
  timestamp: string
  data: LLMOutputData | ToolCallingData
}

export interface TaskQueryResponse {
  task_id: string
  status: TaskStatus
  stage: WorkflowStage
  product_name: string
  created_at: string
  contents: ContentBlock[]
  final_video_url?: string
  final_video_with_bgm_url?: string
  final_script?: string
  error_message?: string
}

export interface SSEContentEvent {
  type: ContentType
  timestamp: string
  data: LLMOutputData | ToolCallingData
}

export interface SSECompleteEvent {
  task_id: string
  status: TaskStatus
}

// API Error
export class APIError extends Error {
  status?: number
  details?: any
  
  constructor(
    message: string,
    status?: number,
    details?: any
  ) {
    super(message)
    this.name = 'APIError'
    this.status = status
    this.details = details
  }
}

/**
 * Create a new task
 */
export async function createTask(request: CreateTaskRequest): Promise<CreateTaskResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new APIError(
        error.detail || 'Failed to create task',
        response.status,
        error
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof APIError) throw error
    throw new APIError(`Network error: ${error instanceof Error ? error.message : 'Unknown'}`)
  }
}

/**
 * Cancel a running task
 */
export async function cancelTask(taskId: string): Promise<CancelTaskResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/tasks/${taskId}/cancel`, {
      method: 'POST',
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new APIError(
        error.detail || 'Failed to cancel task',
        response.status,
        error
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof APIError) throw error
    throw new APIError(`Network error: ${error instanceof Error ? error.message : 'Unknown'}`)
  }
}

/**
 * Restart a task from a specific stage
 */
export interface RestartTaskRequest {
  stage: string
}

export interface RestartTaskResponse {
  success: boolean
  message: string
}

export async function restartTask(
  taskId: string,
  request: RestartTaskRequest
): Promise<RestartTaskResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/tasks/${taskId}/restart`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new APIError(
        error.detail || 'Failed to restart task',
        response.status,
        error
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof APIError) throw error
    throw new APIError(`Network error: ${error instanceof Error ? error.message : 'Unknown'}`)
  }
}

/**
 * Query task status (non-streaming)
 */
export async function queryTask(taskId: string): Promise<TaskQueryResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/tasks/${taskId}`)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new APIError(
        error.detail || 'Failed to query task',
        response.status,
        error
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof APIError) throw error
    throw new APIError(`Network error: ${error instanceof Error ? error.message : 'Unknown'}`)
  }
}

/**
 * Stream task updates using Server-Sent Events
 * Returns an async generator that yields updates
 */
export async function* streamTaskUpdates(
  taskId: string,
  signal?: AbortSignal
): AsyncGenerator<SSEContentEvent | SSECompleteEvent, void, unknown> {
  const response = await fetch(`${API_BASE_URL}/v1/tasks/${taskId}?stream=true`, {
    signal,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new APIError(
      error.detail || 'Failed to stream task updates',
      response.status,
      error
    )
  }

  if (!response.body) {
    throw new APIError('Response body is null')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.trim() || line.startsWith(':')) continue

        // Parse event type
        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim()
          continue
        }

        // Parse data
        if (line.startsWith('data:')) {
          const data = line.slice(5).trim()
          if (!data) continue

          try {
            const parsed = JSON.parse(data)
            
            // Add event type to parsed data for content events
            if (currentEvent === 'content' && parsed.type) {
              yield parsed as SSEContentEvent
            } else if (currentEvent === 'complete' && parsed.status) {
              yield parsed as SSECompleteEvent
            }
            
            // Reset event type after processing
            currentEvent = ''
          } catch (e) {
            console.error('Failed to parse SSE data:', e, data)
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

/**
 * Upload product image and get URL
 */
export async function uploadProductImage(file: File): Promise<string> {
  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE_URL}/v1/upload/image`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
      throw new APIError(
        error.detail || 'Failed to upload image',
        response.status,
        error
      )
    }

    const result = await response.json()
    
    // Log fallback warning if COS upload failed
    if (result.fallback) {
      console.warn('Image upload: Using Data URL fallback -', result.message)
    }
    
    return result.url
  } catch (error) {
    if (error instanceof APIError) throw error
    throw new APIError(`Upload failed: ${error instanceof Error ? error.message : 'Unknown'}`)
  }
}

