import React from "react"
import { createPortal } from "react-dom"
import {
  AlertTriangle,
  BadgeCheck,
  History,
  LoaderCircle,
  Maximize2,
  Minimize2,
  Moon,
  PauseOctagon,
  PlayCircle,
  Sparkles,
  Sun,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { ScrollArea } from "@/components/ui/scroll-area"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { Skeleton } from "@/components/ui/skeleton"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Toaster } from "@/components/ui/toaster"
import { useToast } from "@/components/ui/use-toast"
import { Dropzone, DropzoneContent, DropzoneEmptyState } from "@/components/ui/dropzone"
import { cn } from "@/lib/utils"
import {
  useWorkflowStore,
  type WorkflowNode,
  type WorkflowResult,
  type WorkflowFormPayload,
} from "@/store/workflow-store"
import { translations, type AppCopy, type Language } from "@/locales"

const SAMPLE_VIDEO_URL =
  "https://storage.googleapis.com/coverr-main/mp4/Mt_Baker.mp4"
const LANGUAGE_STORAGE_KEY = "language"

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const shotListFromText = (value: string) =>
  value
    .split(/[\n,|]/)
    .map((shot) => shot.trim())
    .filter(Boolean)

function App() {
  const {
    nodes,
    isRunning,
    interrupted,
    startWorkflow,
    setNodeStatus,
    appendNodeTranscript,
    setNodeSummary,
    completeWorkflow,
    toggleNodeFeedback,
    finalResult,
    resetFinalResult,
    history,
    interruptWorkflow,
  } = useWorkflowStore()

  const { toast } = useToast()

  const [productName, setProductName] = React.useState("Product teaser for NOVA earbuds")
  const [brandIdentity, setBrandIdentity] = React.useState(
    "Highlight hybrid noise-canceling, adaptive EQ, and 36h battery. Set mood: futuristic studio with neon rim light."
  )
  const [productImage, setProductImage] = React.useState<File | null>(null)
  const [mustHaveShotsText, setMustHaveShotsText] = React.useState("")
  const [numberOfShots, setNumberOfShots] = React.useState("6")
  const [videoFormats, setVideoFormats] = React.useState<string[]>(["16:9 Landscape"])
  const [lightboxOpen, setLightboxOpen] = React.useState(false)
  const [feedbackDraft, setFeedbackDraft] = React.useState<Record<string, string>>(
    {}
  )
  const [isRegenerating, setIsRegenerating] = React.useState(false)
  const [theme, setTheme] = React.useState<"dark" | "light">("dark")
  const [language, setLanguage] = React.useState<Language>(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
      if (stored === "en" || stored === "zh") {
        return stored as Language
      }
    }
    return "en"
  })

  const controllerRef = React.useRef<{ cancelled: boolean; run: number } | null>(
    null
  )
  const copy = translations[language]
  const streamingScripts = copy.workflow.streamingScripts

  const handleGenerate = React.useCallback(async () => {
    if (isRunning) return
    const trimmedProductName = productName.trim()
    const trimmedBrandIdentity = brandIdentity.trim()
    const parsedShots = shotListFromText(mustHaveShotsText)
    const parsedNumberOfShots = Number.parseInt(numberOfShots, 10)

    if (!trimmedProductName) {
      toast({
        variant: "destructive",
        title: copy.validation.missingProductName.title,
        description: copy.validation.missingProductName.description,
      })
      return
    }

    if (!trimmedBrandIdentity) {
      toast({
        variant: "destructive",
        title: copy.validation.missingBrandIdentity.title,
        description: copy.validation.missingBrandIdentity.description,
      })
      return
    }

    if (!parsedShots.length) {
      toast({
        variant: "destructive",
        title: copy.validation.missingShots.title,
        description: copy.validation.missingShots.description,
      })
      return
    }

    if (!Number.isFinite(parsedNumberOfShots) || parsedNumberOfShots <= 0) {
      toast({
        variant: "destructive",
        title: copy.validation.invalidShotCount.title,
        description: copy.validation.invalidShotCount.description,
      })
      return
    }

    if (!videoFormats.length) {
      toast({
        variant: "destructive",
        title: copy.validation.missingVideoFormat.title,
        description: copy.validation.missingVideoFormat.description,
      })
      return
    }

    const payload: WorkflowFormPayload = {
      productName: trimmedProductName,
      brandIdentity: trimmedBrandIdentity,
      productImage,
      mustHaveShots: parsedShots,
      numberOfShots: parsedNumberOfShots,
      videoFormats,
    }

    const run = startWorkflow(payload)
    controllerRef.current = { cancelled: false, run }

    const order = ["script", "storyboard", "video-gen", "concat", "bgm"]

    for (const nodeId of order) {
      if (controllerRef.current?.cancelled) break
      setNodeStatus(nodeId, "running")
      const messages = streamingScripts[nodeId] ?? [copy.workflow.processingFallback]
      for (const line of messages) {
        if (controllerRef.current?.cancelled) break
        appendNodeTranscript(nodeId, line)
        await sleep(700)
      }
      if (controllerRef.current?.cancelled) break
      const doneSummary = copy.nodes[nodeId]?.doneSummary
      if (doneSummary) {
        setNodeSummary(nodeId, doneSummary)
      }
      setNodeStatus(nodeId, "done")
    }

    if (controllerRef.current?.cancelled) {
      controllerRef.current = null
      toast({
        variant: "destructive",
        title: copy.toasts.workflowInterrupted.title,
        description: copy.toasts.workflowInterrupted.description,
      })
      return
    }

    const compiledScript = Object.values(streamingScripts)
      .flat()
      .join("\n")

    const result: WorkflowResult = {
      id: `run-${run}-${Date.now()}`,
      title: payload.productName,
      script: compiledScript,
      videoUrl: SAMPLE_VIDEO_URL,
      createdAt: new Date().toISOString(),
    }

    completeWorkflow(result)
    controllerRef.current = null
    toast({
      variant: "success",
      title: copy.toasts.workflowFinished.title,
      description: copy.toasts.workflowFinished.description,
    })
  }, [
    appendNodeTranscript,
    brandIdentity,
    completeWorkflow,
    copy,
    isRunning,
    mustHaveShotsText,
    numberOfShots,
    productImage,
    productName,
    setNodeStatus,
    setNodeSummary,
    startWorkflow,
    streamingScripts,
    toast,
    videoFormats,
  ])

  const handleInterrupt = React.useCallback(() => {
    if (!controllerRef.current) return
    controllerRef.current.cancelled = true
    interruptWorkflow()
    toast({
      variant: "destructive",
      title: copy.toasts.interruptSent.title,
      description: copy.toasts.interruptSent.description,
    })
  }, [copy, interruptWorkflow, toast])

  const handleRegenerate = React.useCallback(async () => {
    if (!finalResult || isRegenerating) return
    setIsRegenerating(true)
    resetFinalResult()
    setNodeStatus("video-gen", "running")
    await sleep(1500)
    setNodeStatus("video-gen", "done")
    const refreshed: WorkflowResult = {
      ...finalResult,
      id: `${finalResult.id}-regen-${Date.now()}`,
      createdAt: new Date().toISOString(),
    }
    completeWorkflow(refreshed)
    setIsRegenerating(false)
    toast({
      variant: "success",
      title: copy.toasts.finalRenderRefreshed.title,
      description: copy.toasts.finalRenderRefreshed.description,
    })
  }, [
    completeWorkflow,
    copy,
    finalResult,
    isRegenerating,
    resetFinalResult,
    setNodeStatus,
    toast,
  ])

  const timelineDisabled = isRunning

  const statusMessage = isRunning
    ? copy.statusMessages.running
    : interrupted
      ? copy.statusMessages.interrupted
      : copy.statusMessages.idle

  const toggleVideoFormat = React.useCallback((format: string) => {
    setVideoFormats((prev) =>
      prev.includes(format) ? prev.filter((item) => item !== format) : [...prev, format]
    )
  }, [])

  React.useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
    }
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("lang", language === "zh" ? "zh-CN" : "en")
    }
  }, [language])

  React.useEffect(() => {
    if (typeof window === "undefined") return
    const storedTheme = window.localStorage.getItem("theme")
    if (storedTheme === "light" || storedTheme === "dark") {
      setTheme(storedTheme)
    }
  }, [])

  React.useEffect(() => {
    if (typeof document === "undefined") return
    if (theme === "dark") {
      document.documentElement.removeAttribute("data-theme")
    } else {
      document.documentElement.setAttribute("data-theme", "light")
    }
    if (typeof window !== "undefined") {
      window.localStorage.setItem("theme", theme)
    }
  }, [theme])

  const toggleTheme = React.useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"))
  }, [])

  const toggleLanguage = React.useCallback(() => {
    setLanguage((prev) => (prev === "en" ? "zh" : "en"))
  }, [])

  return (
    <div className="min-h-screen bg-background">
      <div className="fixed right-6 top-6 z-50 flex gap-2">
        <Button
          size="icon"
          variant="outline"
          className="h-10 w-10 rounded-full bg-background/80 shadow-sm backdrop-blur"
          onClick={toggleLanguage}
          aria-label={language === "en" ? copy.languageToggle.toChinese : copy.languageToggle.toEnglish}
        >
          <span className="text-xs font-semibold">
            {language === "en" ? "中" : "EN"}
          </span>
        </Button>
        <Button
          size="icon"
          variant="outline"
          className="h-10 w-10 rounded-full bg-background/80 shadow-sm backdrop-blur"
          onClick={toggleTheme}
          aria-label={theme === "dark" ? copy.themeToggle.toLight : copy.themeToggle.toDark}
        >
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
      </div>
      <div className="mx-auto flex max-w-[1600px] flex-col gap-6 px-6 pt-8 pb-4">
        <header className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-[0.4em] text-muted-foreground">
            {copy.header.eyebrow}
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold">
              {copy.header.title}
            </h1>
            <Badge className="gap-1 bg-accent/20 text-accent">
              <BadgeCheck className="h-3.5 w-3.5" />
              {copy.header.badge}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            {copy.header.description}
          </p>
        </header>

        <main
          className="hidden md:block"
          style={{ height: "calc(100vh - 180px)" }}
        >
          <ResizablePanelGroup direction="horizontal" className="h-full">
            <ResizablePanel minSize={20} defaultSize={20}>
              <InputPanel
                copy={copy}
                formState={{
                  productName,
                  brandIdentity,
                  productImage,
                  mustHaveShotsText,
                  numberOfShots,
                  videoFormats,
                }}
                onChange={{
                  productName: setProductName,
                  brandIdentity: setBrandIdentity,
                  productImage: setProductImage,
                  mustHaveShotsText: setMustHaveShotsText,
                  numberOfShots: setNumberOfShots,
                }}
                onToggleVideoFormat={toggleVideoFormat}
                disabled={isRunning}
                onGenerate={handleGenerate}
                onInterrupt={handleInterrupt}
                isRunning={isRunning}
              />
            </ResizablePanel>
            <ResizableHandle />
            <ResizablePanel defaultSize={45} minSize={35}>
              <TimelinePanel
                copy={copy}
                nodes={nodes}
                disabled={timelineDisabled}
                isRunning={isRunning}
                interrupted={interrupted}
                onFeedback={(node, sentiment, reason) => {
                  toggleNodeFeedback(node.id, sentiment, reason)
                }}
                feedbackDraft={feedbackDraft}
                setFeedbackDraft={setFeedbackDraft}
              />
            </ResizablePanel>
            <ResizableHandle />
            <ResizablePanel minSize={25} defaultSize={35}>
              <FinalOutputPanel
                copy={copy}
                result={finalResult}
                history={history.slice(1)}
                onRegenerate={handleRegenerate}
                isRegenerating={isRegenerating}
                lightboxOpen={lightboxOpen}
                setLightboxOpen={setLightboxOpen}
                status={statusMessage}
              />
            </ResizablePanel>
          </ResizablePanelGroup>
        </main>

        <section className="md:hidden">
          <StackedFallback
            copy={copy}
            nodes={nodes}
            finalResult={finalResult}
            isRunning={isRunning}
            onGenerate={handleGenerate}
            onInterrupt={handleInterrupt}
          />
        </section>
      </div>
      <Toaster />
      {lightboxOpen && finalResult
        ? createPortal(
            <Lightbox
              copy={copy.lightbox}
              videoUrl={finalResult.videoUrl}
              onClose={() => setLightboxOpen(false)}
            />,
            document.body
          )
        : null}
    </div>
  )
}

interface InputPanelProps {
  copy: AppCopy
  formState: {
    productName: string
    brandIdentity: string
    productImage: File | null
    mustHaveShotsText: string
    numberOfShots: string
    videoFormats: string[]
  }
  onChange: {
    productName: (value: string) => void
    brandIdentity: (value: string) => void
    productImage: (file: File | null) => void
    mustHaveShotsText: (value: string) => void
    numberOfShots: (value: string) => void
  }
  onToggleVideoFormat: (format: string) => void
  disabled: boolean
  onGenerate: () => void
  onInterrupt: () => void
  isRunning: boolean
}

function InputPanel({
  copy,
  formState,
  onChange,
  onToggleVideoFormat,
  disabled,
  onGenerate,
  onInterrupt,
  isRunning,
}: InputPanelProps) {
  const inputCopy = copy.inputPanel
  const showShotHelper = !formState.mustHaveShotsText.trim().length
  const shotHelperText = inputCopy.shotHelperSuggestions.join("\n")

  return (
    <div className="h-full px-1">
      <Card className="flex h-full flex-col overflow-hidden">
        <CardHeader className="space-y-1 px-4 pb-4">
          <CardTitle className="text-lg">{inputCopy.title}</CardTitle>
          <p className="text-sm text-muted-foreground">
            {inputCopy.description}
          </p>
        </CardHeader>
        <CardContent className="scroll-area flex flex-1 flex-col gap-4 overflow-y-auto px-4">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-muted-foreground">
              {inputCopy.fields.productName.label}
            </label>
            <Input
              value={formState.productName}
              onChange={(e) => onChange.productName(e.target.value)}
              placeholder={inputCopy.fields.productName.placeholder}
              disabled={disabled}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-muted-foreground">
              {inputCopy.fields.brandIdentity.label}
            </label>
            <Textarea
              value={formState.brandIdentity}
              onChange={(e) => onChange.brandIdentity(e.target.value)}
              placeholder={inputCopy.fields.brandIdentity.placeholder}
              className="min-h-[120px] resize-none"
              disabled={disabled}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-muted-foreground">
              {inputCopy.fields.productImage.label}
            </label>
            <Dropzone
              accept={{ "image/*": [] }}
              maxFiles={1}
              onDrop={(files) => onChange.productImage(files[0] ?? null)}
              src={formState.productImage ? [formState.productImage] : undefined}
              disabled={disabled}
            >
              <DropzoneEmptyState />
              <DropzoneContent />
            </Dropzone>
            <p className="text-xs text-muted-foreground">
              {formState.productImage
                ? `${inputCopy.dropzone.selectedPrefix} ${formState.productImage.name}`
                : inputCopy.dropzone.helperText}
            </p>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-muted-foreground">
              {inputCopy.fields.mustHaveShots.label}
            </label>
            <div className="relative">
              {showShotHelper ? (
                <p className="pointer-events-none absolute left-4 right-4 top-3 whitespace-pre-line text-sm text-muted-foreground/80">
                  {shotHelperText}
                </p>
              ) : null}
              <Textarea
                value={formState.mustHaveShotsText}
                onChange={(e) => onChange.mustHaveShotsText(e.target.value)}
                className="min-h-[110px] resize-none"
                disabled={disabled}
              />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-muted-foreground">
              {inputCopy.fields.numberOfShots.label}
            </label>
            <Input
              type="number"
              min={1}
              inputMode="numeric"
              value={formState.numberOfShots}
              onChange={(e) => onChange.numberOfShots(e.target.value)}
              disabled={disabled}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-muted-foreground">
              {inputCopy.fields.videoFormat.label}
            </label>
            <div className="flex flex-wrap gap-2">
              {inputCopy.videoFormatOptions.map((format) => {
                const isSelected = formState.videoFormats.includes(format)
                return (
                  <Button
                    key={format}
                    type="button"
                    size="sm"
                    variant={isSelected ? "default" : "outline"}
                    className="rounded-full"
                    onClick={() => onToggleVideoFormat(format)}
                    disabled={disabled}
                  >
                    {format}
                  </Button>
                )
              })}
            </div>
          </div>
        </CardContent>
        <CardFooter className="flex gap-3 px-4">
          <Button
            className="flex-1"
            onClick={onGenerate}
            disabled={isRunning}
            aria-busy={isRunning}
          >
            {isRunning ? (
              <>
                <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                {inputCopy.actions.generating}
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                {inputCopy.actions.generate}
              </>
            )}
          </Button>
          <Button
            className="flex-1"
            variant="secondary"
            disabled={!isRunning}
            onClick={onInterrupt}
          >
            <PauseOctagon className="mr-2 h-4 w-4" />
            {inputCopy.actions.interrupt}
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}

interface TimelinePanelProps {
  copy: AppCopy
  nodes: WorkflowNode[]
  disabled: boolean
  isRunning: boolean
  interrupted: boolean
  onFeedback: (
    node: WorkflowNode,
    feedback: WorkflowNode["feedback"],
    reason?: string
  ) => void
  feedbackDraft: Record<string, string>
  setFeedbackDraft: React.Dispatch<React.SetStateAction<Record<string, string>>>
}

function TimelinePanel({
  copy,
  nodes,
  disabled,
  isRunning,
  interrupted,
  onFeedback,
  feedbackDraft,
  setFeedbackDraft,
}: TimelinePanelProps) {
  const timelineCopy = copy.timeline
  const nodeHasActivity = (node: WorkflowNode) =>
    node.status !== "waiting" || node.transcript.length > 0

  const nodesWithActivity = nodes.filter(nodeHasActivity)
  const shouldShowNodes = isRunning || nodesWithActivity.length > 0
  const nodesToRender = isRunning ? nodes : nodesWithActivity

  return (
    <div className="h-full px-1">
      <Card
        className={cn(
          "flex h-full flex-col border-2",
          isRunning ? "border-accent shadow-panel-glow" : "border-border"
        )}
      >
        <CardHeader className="flex-row items-center justify-between pb-4">
          <div>
            <CardTitle className="text-lg">{timelineCopy.title}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {timelineCopy.description}
            </p>
          </div>
          <Badge
            variant={isRunning ? "outline" : "secondary"}
            className={cn(isRunning && "border-accent text-accent")}
          >
            {isRunning
              ? timelineCopy.statusBadge.running
              : interrupted
                ? timelineCopy.statusBadge.interrupted
                : timelineCopy.statusBadge.idle}
          </Badge>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden">
          {interrupted ? (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>{timelineCopy.alertTitle}</AlertTitle>
              <AlertDescription>{timelineCopy.alertDescription}</AlertDescription>
            </Alert>
          ) : null}
          {shouldShowNodes ? (
            <ScrollArea className="h-full rounded-lg bg-dot-pattern">
              <div
                className={cn(
                  "space-y-4 p-4 transition",
                  disabled && "cursor-not-allowed"
                )}
                aria-disabled={disabled}
              >
                {nodesToRender.map((node) => (
                  <NodeCard
                    key={node.id}
                    copy={copy}
                    node={node}
                    disabled={disabled}
                    onFeedback={onFeedback}
                    feedbackDraft={feedbackDraft}
                    setFeedbackDraft={setFeedbackDraft}
                  />
                ))}
              </div>
            </ScrollArea>
          ) : (
            <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-muted text-center text-sm text-muted-foreground">
              {timelineCopy.emptyState}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

interface NodeCardProps {
  copy: AppCopy
  node: WorkflowNode
  disabled: boolean
  onFeedback: (
    node: WorkflowNode,
    sentiment: WorkflowNode["feedback"],
    reason?: string
  ) => void
  feedbackDraft: Record<string, string>
  setFeedbackDraft: React.Dispatch<React.SetStateAction<Record<string, string>>>
}

function NodeCard({
  copy,
  node,
  disabled,
  onFeedback,
  feedbackDraft,
  setFeedbackDraft,
}: NodeCardProps) {
  const nodeCopy = copy.nodes[node.id]
  const label = nodeCopy?.label ?? node.label
  const summaryText =
    node.status === "done" && node.summary
      ? node.summary
      : nodeCopy?.waitingSummary ?? node.summary
  const statusBadge =
    node.status === "running"
      ? { label: copy.nodeCard.statusBadges.running, variant: "outline" as const }
      : node.status === "done"
        ? { label: copy.nodeCard.statusBadges.done, variant: "default" as const }
        : node.status === "error"
          ? { label: copy.nodeCard.statusBadges.error, variant: "destructive" as const }
          : { label: copy.nodeCard.statusBadges.waiting, variant: "secondary" as const }

  const locked = disabled && node.status !== "done"

  return (
    <div
      className={cn(
        "relative max-h-[30vh] max-w-[80%] rounded-2xl border bg-card/95 shadow-sm backdrop-blur transition",
        locked && "opacity-75"
      )}
    >
      <div className="flex items-start justify-between gap-2 border-b px-4 py-3">
        <div>
          <p className="text-sm font-semibold">{label}</p>
          <p className="text-xs text-muted-foreground">{summaryText}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={statusBadge.variant}>{statusBadge.label}</Badge>
          <div className="flex items-center gap-1 text-muted-foreground">
            <Button
              variant={node.feedback === "up" ? "default" : "ghost"}
              size="icon"
              className="h-8 w-8"
              onClick={() =>
                onFeedback(node, node.feedback === "up" ? null : "up")
              }
              disabled={locked}
              aria-label={copy.nodeCard.thumbsUpAria}
            >
              <ThumbsUp className="h-4 w-4" />
            </Button>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant={node.feedback === "down" ? "destructive" : "ghost"}
                  size="icon"
                  className="h-8 w-8"
                  disabled={locked}
                  aria-label={copy.nodeCard.thumbsDownAria}
                >
                  <ThumbsDown className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="space-y-3">
                <p className="text-sm font-semibold">{copy.nodeCard.feedbackPrompt}</p>
                <Textarea
                  value={feedbackDraft[node.id] ?? ""}
                  onChange={(event) =>
                    setFeedbackDraft((prev) => ({
                      ...prev,
                      [node.id]: event.target.value,
                    }))
                  }
                  placeholder={copy.nodeCard.feedbackPlaceholder}
                />
                <Button
                  size="sm"
                  onClick={() => {
                    const nextFeedback = node.feedback === "down" ? null : "down"
                    onFeedback(
                      node,
                      nextFeedback,
                      nextFeedback === "down" ? feedbackDraft[node.id] : undefined
                    )
                    if (nextFeedback === null) {
                      setFeedbackDraft((prev) => {
                        const clone = { ...prev }
                        delete clone[node.id]
                        return clone
                      })
                    }
                  }}
                >
                  {copy.nodeCard.feedbackSubmit}
                </Button>
              </PopoverContent>
            </Popover>
          </div>
        </div>
      </div>
      <div className="scroll-area flex max-h-[22vh] flex-col gap-2 overflow-y-auto px-4 py-3 text-sm font-mono">
        {node.transcript.length ? (
          node.transcript.map((line, index) => (
            <p key={`${node.id}-${index}`} className="text-foreground/80">
              {line}
            </p>
          ))
        ) : (
          <p className="text-muted-foreground">{copy.nodeCard.waitingMessage}</p>
        )}
      </div>
    </div>
  )
}

interface FinalOutputPanelProps {
  copy: AppCopy
  result?: WorkflowResult
  history: WorkflowResult[]
  onRegenerate: () => void
  isRegenerating: boolean
  lightboxOpen: boolean
  setLightboxOpen: (value: boolean) => void
  status: string
}

function FinalOutputPanel({
  copy,
  result,
  history,
  onRegenerate,
  isRegenerating,
  lightboxOpen,
  setLightboxOpen,
  status,
}: FinalOutputPanelProps) {
  const finalCopy = copy.finalOutput
  return (
    <div className="h-full px-1">
      <Card className="flex h-full flex-col">
        <CardHeader className="flex-row items-center justify-between pb-4">
          <div>
            <CardTitle className="text-lg">{finalCopy.title}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {finalCopy.description}
            </p>
          </div>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-4 overflow-hidden">
          <Alert className="border-none bg-accent/10 text-accent">
            <AlertTitle>{finalCopy.statusLabel}</AlertTitle>
            <AlertDescription>{status}</AlertDescription>
          </Alert>
          {!result ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center text-muted-foreground">
              <Skeleton className="h-48 w-full rounded-xl" />
              <p className="text-sm">
                {finalCopy.emptyMessage}
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold">{result.title}</h2>
                  <Badge variant="outline" className="text-xs uppercase tracking-wide">
                    {finalCopy.readyBadge}
                  </Badge>
                </div>
                <AspectRatio ratio={16 / 9}>
                  <div className="group relative h-full w-full overflow-hidden rounded-xl border bg-black">
                    <video
                      src={result.videoUrl}
                      controls
                      className="h-full w-full object-cover"
                    />
                    <Button
                      size="icon"
                      variant="ghost"
                      className="absolute right-3 top-3 bg-black/50 text-white opacity-0 transition group-hover:opacity-100"
                      onClick={() => setLightboxOpen(!lightboxOpen)}
                      aria-label={
                        lightboxOpen ? finalCopy.videoButton.collapse : finalCopy.videoButton.expand
                      }
                    >
                      {lightboxOpen ? (
                        <Minimize2 className="h-4 w-4" />
                      ) : (
                        <Maximize2 className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </AspectRatio>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold">{finalCopy.scriptLabel}</p>
                  <span className="text-xs text-muted-foreground">
                    {new Date(result.createdAt).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <ScrollArea className="h-40 rounded-lg border px-4 py-3 text-sm">
                  <pre className="whitespace-pre-wrap font-mono text-foreground/80">
                    {result.script}
                  </pre>
                </ScrollArea>
              </div>

              {history.length ? (
                <div className="space-y-2">
                  <details className="rounded-lg border p-3">
                    <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold">
                      <History className="h-4 w-4" />
                      {finalCopy.historyTitle}
                    </summary>
                    <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                      {history.slice(0, 3).map((entry) => (
                        <div
                          key={entry.id}
                          className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2"
                        >
                          <span>{entry.title}</span>
                          <span className="text-xs">
                            {new Date(entry.createdAt).toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              ) : null}
            </>
          )}
        </CardContent>
        <CardFooter className="flex gap-3">
          <Button
            variant="secondary"
            className="flex-1"
            onClick={onRegenerate}
            disabled={!result || isRegenerating}
          >
            {isRegenerating ? (
              <>
                <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                {finalCopy.regenerating}
              </>
            ) : (
              <>
                <PlayCircle className="mr-2 h-4 w-4" />
                {finalCopy.regenerate}
              </>
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}

interface LightboxProps {
  copy: AppCopy["lightbox"]
  videoUrl: string
  onClose: () => void
}

function Lightbox({ copy, videoUrl, onClose }: LightboxProps) {
  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 p-6">
      <div className="w-full max-w-4xl rounded-2xl bg-black shadow-2xl ring-2 ring-white/10">
        <div className="flex justify-end p-3">
          <Button variant="ghost" className="text-white" onClick={onClose}>
            {copy.close}
          </Button>
        </div>
        <AspectRatio ratio={16 / 9}>
          <video
            src={videoUrl}
            controls
            autoPlay
            className="h-full w-full rounded-b-2xl object-cover"
          />
        </AspectRatio>
      </div>
    </div>
  )
}

interface StackedFallbackProps {
  copy: AppCopy
  nodes: WorkflowNode[]
  finalResult?: WorkflowResult
  isRunning: boolean
  onGenerate: () => void
  onInterrupt: () => void
}

function StackedFallback({
  copy,
  nodes,
  finalResult,
  isRunning,
  onGenerate,
  onInterrupt,
}: StackedFallbackProps) {
  const fallbackCopy = copy.stackedFallback
  const nodeHasActivity = (node: WorkflowNode) =>
    node.status !== "waiting" || node.transcript.length > 0

  const nodesWithActivity = nodes.filter(nodeHasActivity)
  const shouldShowNodes = isRunning || nodesWithActivity.length > 0
  const nodesToRender = isRunning ? nodes : nodesWithActivity

  return (
    <div className="space-y-4">
      <Alert>
        <AlertTitle>{fallbackCopy.desktopTitle}</AlertTitle>
        <AlertDescription>{fallbackCopy.desktopDescription}</AlertDescription>
      </Alert>
      <Card>
        <CardHeader>
          <CardTitle>{fallbackCopy.userInputTitle}</CardTitle>
        </CardHeader>
        <CardFooter className="flex gap-3">
          <Button className="flex-1" onClick={onGenerate} disabled={isRunning}>
            {copy.inputPanel.actions.generate}
          </Button>
          <Button
            variant="secondary"
            className="flex-1"
            disabled={!isRunning}
            onClick={onInterrupt}
          >
            {copy.inputPanel.actions.interrupt}
          </Button>
        </CardFooter>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{fallbackCopy.nodeTimelineTitle}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {shouldShowNodes ? (
            nodesToRender.map((node) => (
              <div key={node.id} className="rounded-lg border px-4 py-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold">
                    {copy.nodes[node.id]?.label ?? node.label}
                  </p>
                  <Badge variant="secondary">
                    {copy.nodeCard.statusBadges[node.status] ?? node.status}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  {node.status === "done" && node.summary
                    ? node.summary
                    : copy.nodes[node.id]?.waitingSummary ?? node.summary}
                </p>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">
              {fallbackCopy.nodesAppear}
            </p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{fallbackCopy.finalOutputTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          {finalResult ? (
            <>
              <AspectRatio ratio={16 / 9}>
                <video
                  src={finalResult.videoUrl}
                  controls
                  className="h-full w-full rounded-lg object-cover"
                />
              </AspectRatio>
              <p className="mt-3 text-sm text-muted-foreground">
                {finalResult.title}
      </p>
    </>
          ) : (
            <Skeleton className="h-48 w-full rounded-lg" />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default App
