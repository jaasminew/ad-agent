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
  RotateCcw,
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { Skeleton } from "@/components/ui/skeleton"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Toaster } from "@/components/ui/sonner"
import { Dropzone, DropzoneContent, DropzoneEmptyState } from "@/components/ui/dropzone"
import { Checkbox } from "@/components/ui/checkbox"
import { cn, formatFileNameForDisplay } from "@/lib/utils"
import {
  useWorkflowStore,
  type WorkflowNode,
  type WorkflowResult,
  type WorkflowFormPayload,
  type TranscriptEntry,
  type ThoughtContentBlock,
  type ChecklistContentBlock,
  type ChecklistItemBlock,
} from "@/store/workflow-store"
import { translations, type AppCopy, type Language } from "@/locales"
import { toast } from "sonner"
import { LandingPage } from "./landing/LandingPage"

const LANGUAGE_STORAGE_KEY = "language"
const INPUT_PANEL_FIELD_CLASS = "input-panel-field"

const shotListFromText = (value: string) =>
  value
    .split(/[\n,|]/)
    .map((shot) => shot.trim())
    .filter(Boolean)

function FieldLabel({ text, required }: { text: string; required?: boolean }) {
  return (
    <label className="text-xs font-semibold uppercase text-muted-foreground">
      {text}
      {required ? (
        <>
          <span className="text-destructive" aria-hidden="true">
            {" "}
            *
          </span>
          <span className="sr-only">required</span>
        </>
      ) : null}
    </label>
  )
}

function App() {
  const {
    nodes,
    isRunning,
    interrupted,
    startWorkflow,
    toggleNodeFeedback,
    finalResult,
    history,
    interruptWorkflow,
    restartWorkflowFromStage,
  } = useWorkflowStore()

  const [productName, setProductName] = React.useState("")
  const [brandIdentity, setBrandIdentity] = React.useState("")
  const [productImage, setProductImage] = React.useState<File | null>(null)
  const [mustHaveShotsText, setMustHaveShotsText] = React.useState("")
  const [numberOfShots, setNumberOfShots] = React.useState("")
  const [videoFormats, setVideoFormats] = React.useState<string[]>(["16:9 Landscape"])
  const [lightboxOpen, setLightboxOpen] = React.useState(false)
  const [feedbackDraft, setFeedbackDraft] = React.useState<Record<string, string>>(
    {}
  )
  const [isRegenerating, setIsRegenerating] = React.useState(false)
  const [theme, setTheme] = React.useState<"dark" | "light">("dark")
  const [interruptDialogOpen, setInterruptDialogOpen] = React.useState(false)
  const [isInterrupting, setIsInterrupting] = React.useState(false)
  const [restartDialogOpen, setRestartDialogOpen] = React.useState(false)
  const [restartStage, setRestartStage] = React.useState<string | null>(null)
  const [isRestarting, setIsRestarting] = React.useState(false)
  const [language, setLanguage] = React.useState<Language>(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
      if (stored === "en" || stored === "zh") {
        return stored as Language
      }
    }
    return "en"
  })

  const [hasStarted, setHasStarted] = React.useState(false)

  const copy = translations[language]

  const handleGenerate = React.useCallback(async () => {
    if (isRunning) return
    const trimmedProductName = productName.trim()
    const trimmedBrandIdentity = brandIdentity.trim()
    const parsedShots = shotListFromText(mustHaveShotsText)
    const parsedNumberOfShots = Number.parseInt(numberOfShots, 10)

    if (!trimmedProductName) {
      toast.error(copy.validation.missingProductName.title, {
        description: copy.validation.missingProductName.description,
      })
      return
    }

    if (!trimmedBrandIdentity) {
      toast.error(copy.validation.missingBrandIdentity.title, {
        description: copy.validation.missingBrandIdentity.description,
      })
      return
    }

    if (!productImage) {
      toast.error(copy.validation.missingProductImage.title, {
        description: copy.validation.missingProductImage.description,
      })
      return
    }

    if (!Number.isFinite(parsedNumberOfShots) || parsedNumberOfShots <= 0) {
      toast.error(copy.validation.invalidShotCount.title, {
        description: copy.validation.invalidShotCount.description,
      })
      return
    }

    if (!videoFormats.length) {
      toast.error(copy.validation.missingVideoFormat.title, {
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

    try {
      await startWorkflow(payload)
    } catch (error) {
      console.error("Failed to start workflow:", error)
      toast.error("Failed to start workflow", {
        description: error instanceof Error ? error.message : "Unknown error",
      })
    }
  }, [
    brandIdentity,
    copy,
    isRunning,
    mustHaveShotsText,
    numberOfShots,
    productImage,
    productName,
    startWorkflow,
    videoFormats,
  ])

  const handleInterruptRequest = React.useCallback(() => {
    if (!isRunning) return
    setInterruptDialogOpen(true)
  }, [isRunning])

  const handleConfirmInterrupt = React.useCallback(
    async (event?: React.MouseEvent<HTMLButtonElement>) => {
      event?.preventDefault()
      setIsInterrupting(true)
      try {
        await interruptWorkflow()
        setInterruptDialogOpen(false)
      } catch (error) {
        console.error("Failed to interrupt workflow:", error)
        toast.error(copy.interruptDialog.errorTitle, {
          description: copy.interruptDialog.errorDescription,
        })
      } finally {
        setIsInterrupting(false)
      }
    },
    [
      copy.interruptDialog.errorDescription,
      copy.interruptDialog.errorTitle,
      interruptWorkflow,
    ]
  )

  const handleRestartRequest = React.useCallback((nodeId: string) => {
    if (isRunning) {
      toast.error(copy.restartDialog.cannotRestartWhileRunning || "Cannot restart while running", {
        description: copy.restartDialog.cannotRestartWhileRunningDescription || "Please wait for current task to complete",
      })
      return
    }
    setRestartStage(nodeId)
    setRestartDialogOpen(true)
  }, [copy, isRunning])

  const handleConfirmRestart = React.useCallback(
    async (event?: React.MouseEvent<HTMLButtonElement>) => {
      event?.preventDefault()
      if (!restartStage) return
      
      setIsRestarting(true)
      try {
        await restartWorkflowFromStage(restartStage as any)
        toast.success(copy.restartDialog?.successTitle || "Workflow restarted", {
          description: (copy.restartDialog?.successDescription || "Restarted from stage: {stage}").replace("{stage}", restartStage),
        })
        setRestartDialogOpen(false)
      } catch (error) {
        console.error("Failed to restart workflow:", error)
        toast.error(copy.restartDialog?.errorTitle || "Restart failed", {
          description: error instanceof Error ? error.message : (copy.restartDialog?.errorDescription || "Failed to restart workflow"),
        })
      } finally {
        setIsRestarting(false)
      }
    },
    [copy, restartStage, restartWorkflowFromStage]
  )

  const handleRegenerate = React.useCallback(async () => {
    if (!finalResult || isRegenerating) return
    setIsRegenerating(true)
    
    // TODO: Implement actual regeneration logic with backend API
    // For now, just show a message
    toast(copy.toasts.finalRenderRefreshed.title, {
      description: copy.toasts.finalRenderRefreshed.description,
    })
    
    setIsRegenerating(false)
  }, [
    copy,
    finalResult,
    isRegenerating,
  ])

  const timelineDisabled = isRunning

  const statusMessage = isRunning
    ? copy.statusMessages.running
    : interrupted
      ? copy.statusMessages.interrupted
      : copy.statusMessages.idle

  const totalNodes = nodes.length
  const completedNodes = nodes.filter((node) => node.status === "done").length
  const runningNodes = nodes.filter((node) => node.status === "running").length
  const hasActiveNodes = completedNodes + runningNodes > 0
  const baseProgress =
    totalNodes > 0 ? (completedNodes + runningNodes * 0.6) / totalNodes : 0
  const statusProgress = Math.min(
    1,
    Math.max(baseProgress, isRunning && !hasActiveNodes ? 0.05 : 0)
  )

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

  if (!hasStarted) {
    return <LandingPage onEnter={() => setHasStarted(true)} />
  }

  return (
    <div className="h-screen max-h-screen w-screen overflow-hidden bg-background flex flex-col">
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
      <div className="mx-auto flex h-full w-full flex-col gap-6 px-6 pt-8 pb-4">
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

        <main className="hidden flex-1 min-h-0 md:block">
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
                onInterrupt={handleInterruptRequest}
                isRunning={isRunning}
                isInterrupting={isInterrupting}
              />
            </ResizablePanel>
            <ResizableHandle />
            <ResizablePanel defaultSize={55} minSize={35}>
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
                onRestart={handleRestartRequest}
              />
            </ResizablePanel>
            <ResizableHandle />
            <ResizablePanel minSize={25} defaultSize={25}>
              <FinalOutputPanel
                copy={copy}
                result={finalResult}
                history={history.slice(1)}
                onRegenerate={handleRegenerate}
                isRegenerating={isRegenerating}
                lightboxOpen={lightboxOpen}
                setLightboxOpen={setLightboxOpen}
                status={statusMessage}
                statusProgress={statusProgress}
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
            onInterrupt={handleInterruptRequest}
            isInterrupting={isInterrupting}
          />
        </section>
      </div>
      <AlertDialog
        open={interruptDialogOpen}
        onOpenChange={(open: boolean) => {
          if (isInterrupting) return
          setInterruptDialogOpen(open)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{copy.interruptDialog.title}</AlertDialogTitle>
            <AlertDialogDescription>
              {copy.interruptDialog.description}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isInterrupting}>
              {copy.interruptDialog.cancel}
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmInterrupt} disabled={isInterrupting}>
              {isInterrupting ? (
                <>
                  <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                  {copy.interruptDialog.confirming}
                </>
              ) : (
                <>
                  <PauseOctagon className="mr-2 h-4 w-4" />
                  {copy.interruptDialog.confirm}
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Restart Confirmation Dialog */}
      <AlertDialog
        open={restartDialogOpen}
        onOpenChange={(open: boolean) => {
          if (isRestarting) return
          setRestartDialogOpen(open)
        }}
      >
        <AlertDialogContent className="rounded-2xl">
          <AlertDialogHeader>
            <AlertDialogTitle>{copy.restartDialog?.title || "Restart Workflow"}</AlertDialogTitle>
            <AlertDialogDescription>
              {copy.restartDialog?.description?.replace("{stage}", restartStage || "") || 
                `Are you sure you want to restart from ${restartStage}? This will re-execute this stage and all subsequent stages.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isRestarting}>
              {copy.restartDialog?.cancel || "Cancel"}
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmRestart} disabled={isRestarting}>
              {isRestarting ? (
                <>
                  <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                  {copy.restartDialog?.confirming || "Restarting..."}
                </>
              ) : (
                <>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  {copy.restartDialog?.confirm || "Restart"}
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Toaster theme={theme} />
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
  isInterrupting: boolean
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
  isInterrupting,
}: InputPanelProps) {
  const inputCopy = copy.inputPanel

  return (
    <div className="h-full px-1">
      <Card className="column-panel flex h-full flex-col overflow-hidden">
        <CardHeader className="space-y-1 px-4 pb-4">
          <CardTitle className="text-lg">{inputCopy.title}</CardTitle>
          <p className="text-sm text-muted-foreground">
            {inputCopy.description}
          </p>
        </CardHeader>
        <CardContent className="scroll-area flex flex-1 flex-col gap-4 overflow-y-auto px-4">
          <div className="space-y-2">
            <FieldLabel text={inputCopy.fields.productName.label} required />
            <Input
              value={formState.productName}
              onChange={(e) => onChange.productName(e.target.value)}
              placeholder={inputCopy.fields.productName.placeholder}
              className={INPUT_PANEL_FIELD_CLASS}
              disabled={disabled}
              required
              aria-required="true"
            />
          </div>
          <div className="space-y-2">
            <FieldLabel text={inputCopy.fields.brandIdentity.label} required />
            <Textarea
              value={formState.brandIdentity}
              onChange={(e) => onChange.brandIdentity(e.target.value)}
              placeholder={inputCopy.fields.brandIdentity.placeholder}
              className={cn(INPUT_PANEL_FIELD_CLASS, "min-h-[120px] resize-none")}
              disabled={disabled}
              required
              aria-required="true"
            />
          </div>
          <div className="space-y-2">
            <FieldLabel text={inputCopy.fields.productImage.label} required />
            <div role="group" aria-label={inputCopy.fields.productImage.label} aria-required="true">
              <Dropzone
                accept={{ "image/*": [] }}
                maxFiles={1}
                onDrop={(files) => onChange.productImage(files[0] ?? null)}
                src={formState.productImage ? [formState.productImage] : undefined}
                disabled={disabled}
                className={INPUT_PANEL_FIELD_CLASS}
                required
              >
                <DropzoneEmptyState uploadHint={inputCopy.dropzone.uploadHint} />
                <DropzoneContent replaceHint={inputCopy.dropzone.replaceHint} />
              </Dropzone>
            </div>
            <p className="text-xs text-muted-foreground">
              {formState.productImage
                ? `${inputCopy.dropzone.selectedPrefix} ${formatFileNameForDisplay(formState.productImage.name)}`
                : inputCopy.dropzone.helperText}
            </p>
          </div>
          <div className="space-y-2">
            <FieldLabel text={inputCopy.fields.mustHaveShots.label} />
            <Textarea
              value={formState.mustHaveShotsText}
              onChange={(e) => onChange.mustHaveShotsText(e.target.value)}
              placeholder={inputCopy.fields.mustHaveShots.placeholder}
              className={cn(INPUT_PANEL_FIELD_CLASS, "min-h-[110px] resize-none")}
              disabled={disabled}
            />
          </div>
          <div className="space-y-2">
            <FieldLabel text={inputCopy.fields.numberOfShots.label} required />
            <Input
              type="number"
              min={1}
              inputMode="numeric"
              value={formState.numberOfShots}
              onChange={(e) => onChange.numberOfShots(e.target.value)}
              placeholder={inputCopy.fields.numberOfShots.placeholder}
              className={INPUT_PANEL_FIELD_CLASS}
              disabled={disabled}
              required
              aria-required="true"
            />
          </div>
          <div className="space-y-2">
            <FieldLabel text={inputCopy.fields.videoFormat.label} required />
            <div
              className="flex flex-wrap gap-2"
              role="group"
              aria-label={inputCopy.fields.videoFormat.label}
              aria-required="true"
            >
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
            variant="destructive"
            disabled={!isRunning || isInterrupting}
            onClick={onInterrupt}
            aria-busy={isInterrupting}
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
  onRestart?: (nodeId: string) => void
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
  onRestart,
}: TimelinePanelProps) {
  const timelineCopy = copy.timeline
  const firstNodeId = nodes[0]?.id
  const nodeHasActivity = (node: WorkflowNode) =>
    node.status !== "waiting" ||
    node.transcript.length > 0 ||
    (isRunning && node.id === firstNodeId)

  const nodesWithActivity = nodes.filter(nodeHasActivity)
  const shouldShowNodes = nodesWithActivity.length > 0
  const nodesToRender = nodesWithActivity

  return (
    <div className="h-full px-1">
      <Card
        className={cn(
          "column-panel flex h-full flex-col border-2",
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
        <CardContent className="flex h-full flex-col gap-3 overflow-hidden">
          {interrupted ? (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>{timelineCopy.alertTitle}</AlertTitle>
              <AlertDescription>{timelineCopy.alertDescription}</AlertDescription>
            </Alert>
          ) : null}
          {shouldShowNodes ? (
            <ScrollArea className="node-canvas grow rounded-lg bg-dot-pattern">
              <div
                className={cn(
                  "w-full space-y-4 px-6 py-4 transition",
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
                    isWorkflowRunning={isRunning}
                    onFeedback={onFeedback}
                    feedbackDraft={feedbackDraft}
                    setFeedbackDraft={setFeedbackDraft}
                    onRestart={onRestart}
                  />
                ))}
              </div>
            </ScrollArea>
          ) : (
            <div className="flex grow items-center justify-center rounded-lg border border-dashed border-muted text-center text-sm text-muted-foreground">
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
  isWorkflowRunning: boolean
  onFeedback: (
    node: WorkflowNode,
    sentiment: WorkflowNode["feedback"],
    reason?: string
  ) => void
  feedbackDraft: Record<string, string>
  setFeedbackDraft: React.Dispatch<React.SetStateAction<Record<string, string>>>
  onRestart?: (nodeId: string) => void
}

function NodeCard({
  copy,
  node,
  disabled,
  isWorkflowRunning,
  onFeedback,
  feedbackDraft,
  setFeedbackDraft,
  onRestart,
}: NodeCardProps) {
  const nodeCopy = copy.nodes[node.id as keyof typeof copy.nodes]
  const label = nodeCopy?.label ?? node.label
  const summaryText =
    node.status === "done" && node.summary
      ? node.summary
      : nodeCopy?.waitingSummary ?? node.summary
  const statusBadge =
    node.status === "running"
      ? { label: copy.nodeCard.statusBadges.running, variant: "outline" as const }
      : node.status === "done"
        ? { label: copy.nodeCard.statusBadges.done, variant: "success" as const }
        : node.status === "error"
          ? { label: copy.nodeCard.statusBadges.error, variant: "destructive" as const }
          : { label: copy.nodeCard.statusBadges.waiting, variant: "secondary" as const }

  const locked = disabled && node.status !== "done"
  const isRunningNode = isWorkflowRunning && node.status === "running"
  
  // Ref for auto-scrolling within this node's transcript
  const transcriptContainerRef = React.useRef<HTMLDivElement>(null)
  
  // Auto-scroll to bottom when transcript updates (only scroll within the container)
  React.useEffect(() => {
    if (node.status === "running" && transcriptContainerRef.current) {
      // Use requestAnimationFrame to ensure DOM has updated
      requestAnimationFrame(() => {
        if (transcriptContainerRef.current) {
          // Scroll the container to the bottom without affecting the page scroll
          transcriptContainerRef.current.scrollTop = transcriptContainerRef.current.scrollHeight
        }
      })
    }
  }, [node.transcript, node.status])

  return (
    <div
      className={cn(
        "relative box-border max-h-[30vh] w-full max-w-full overflow-hidden rounded-2xl border bg-card/95 shadow-sm backdrop-blur transition",
        locked && "opacity-75",
        isRunningNode && "node-card-running"
      )}
    >
      <div className="flex items-start justify-between gap-2 border-b px-4 py-3">
        <div>
          <p className="text-sm font-semibold">{label}</p>
          <p className="text-xs text-muted-foreground">{summaryText}</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Restart button - only show if node is done and workflow is not running */}
          {node.status === "done" && !isWorkflowRunning && onRestart && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onRestart(node.id)}
              aria-label={copy.restartButtonAria || "Restart from this stage"}
              title={copy.restartButtonAria || "Restart from this stage"}
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          )}
          <Badge
            variant={statusBadge.variant}
            className="flex items-center justify-center gap-1"
            title={statusBadge.label}
          >
            {node.status === "error" ? (
              <>
                <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                <span className="sr-only">{statusBadge.label}</span>
              </>
            ) : (
              statusBadge.label
            )}
          </Badge>
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
      <div 
        ref={transcriptContainerRef}
        className="scroll-area flex max-h-[22vh] flex-col gap-2 overflow-y-auto px-4 py-3 text-sm font-mono"
      >
        {node.transcript.length ? (
          <>
            {node.transcript.map((entry) => (
              <TranscriptLine key={entry.id} entry={entry} />
            ))}
          </>
        ) : (
          <p className="text-muted-foreground">{copy.nodeCard.waitingMessage}</p>
        )}
      </div>
    </div>
  )
}

interface TranscriptLineProps {
  entry: TranscriptEntry
}

function TranscriptLine({ entry }: TranscriptLineProps) {
  const line = entry.message
  // Detect line type and apply styling
  const isThought = line.includes("🤔") || line.startsWith("Thought:")
  const isAction = line.includes("🔧") || line.startsWith("Action:")
  const isObservation = line.includes("📊") || line.startsWith("Observation:")
  const isSuccess = line.includes("✅") || line.includes("✓")
  const isError = line.includes("❌") || line.includes("✗") || line.startsWith("Error:")
  const isProgress = line.includes("🎬") || line.includes("🎥") || line.includes("📝")
  
  // Extract URLs (images and videos)
  const urlRegex = /(https?:\/\/[^\s]+\.(?:jpg|jpeg|png|gif|webp|mp4|mov|avi))/gi
  const urls = line.match(urlRegex) || []
  
  // Determine font weight (no colors)
  const fontWeight = isThought
    ? "font-normal"
    : isAction || isProgress
      ? "font-semibold"
      : isObservation
        ? "font-medium"
        : isSuccess
          ? "font-medium"
          : isError
            ? "font-semibold"
            : "font-normal"
  
  return (
    <div className="space-y-3">
      <p className={cn(fontWeight, "text-foreground/80")}>{line}</p>
      {urls.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {urls.map((url, idx) => (
            <MediaPreview key={idx} url={url} />
          ))}
        </div>
      )}
      {entry.contentBlocks && entry.contentBlocks.length > 0 ? (
        <div className="space-y-3">
          {entry.contentBlocks.map((block, index) => (
            <TranscriptContentBlock key={`${entry.id}-block-${index}`} block={block} />
          ))}
        </div>
      ) : null}
    </div>
  )
}

function TranscriptContentBlock({ block }: { block: ThoughtContentBlock }) {
  if (block.type === "text") {
    return (
      <div className="rounded-lg border border-dashed border-muted/50 bg-background/80 px-3 py-2 text-xs text-muted-foreground">
        {block.content}
      </div>
    )
  }
  
  if (block.type === "checklist") {
    return <ChecklistBlock block={block} />
  }
  
  return null
}

function ChecklistBlock({ block }: { block: ChecklistContentBlock }) {
  const { stats } = block
  const progressPercent = Math.round(stats.progress * 100)
  
  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm shadow-sm">
      <div className="mb-3 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <span>Checklist</span>
        <span>
          {stats.checkedItems}/{stats.totalItems} · {progressPercent}%
        </span>
      </div>
      <div className="space-y-2">
        {block.items.map((item) => (
          <ChecklistItemRow key={item.slug} item={item} />
        ))}
      </div>
      {block.summary ? (
        <p className="mt-3 text-xs text-muted-foreground">{block.summary}</p>
      ) : null}
    </div>
  )
}

function ChecklistItemRow({ item }: { item: ChecklistItemBlock }) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border border-transparent bg-background/80 p-2 transition",
        item.checked ? "border-primary/60" : "border-muted/50",
        "hover:border-primary/70"
      )}
    >
      <Checkbox
        checked={item.checked}
        aria-readonly="true"
        tabIndex={-1}
        className={cn(
          "pointer-events-none border-2",
          "data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground"
        )}
      />
      <div className="flex-1 space-y-1">
        <p className={cn("text-sm leading-tight", item.checked ? "text-foreground" : "text-muted-foreground")}>
          {item.description}
        </p>
        <p className="text-xs uppercase tracking-wide text-muted-foreground">
          {item.slug}
          {item.optional ? " · Optional" : ""}
        </p>
      </div>
    </div>
  )
}

interface MediaPreviewProps {
  url: string
}

function MediaPreview({ url }: MediaPreviewProps) {
  const isVideo = /\.(mp4|mov|avi)$/i.test(url)
  const [isExpanded, setIsExpanded] = React.useState(false)
  
  if (isVideo) {
    return (
      <div className="relative">
        {isExpanded ? (
          <div className="relative w-full max-w-md">
            <video
              src={url}
              controls
              className="w-full rounded-lg border"
            />
            <Button
              size="sm"
              variant="ghost"
              className="absolute right-2 top-2 bg-black/50 text-white"
              onClick={() => setIsExpanded(false)}
            >
              Collapse
            </Button>
          </div>
        ) : (
          <Button
            size="sm"
            variant="outline"
            className="text-xs"
            onClick={() => setIsExpanded(true)}
          >
            🎬 Preview Video
          </Button>
        )}
      </div>
    )
  }
  
  // Image preview
  return (
    <div className="relative">
      {isExpanded ? (
        <div className="relative">
          <img
            src={url}
            alt="Preview"
            className="max-h-48 w-auto rounded-lg border"
          />
          <Button
            size="sm"
            variant="ghost"
            className="absolute right-2 top-2 bg-black/50 text-white"
            onClick={() => setIsExpanded(false)}
          >
            ×
          </Button>
        </div>
      ) : (
        <img
          src={url}
          alt="Preview"
          className="h-16 w-16 cursor-pointer rounded-lg border object-cover hover:opacity-80"
          onClick={() => setIsExpanded(true)}
        />
      )}
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
  statusProgress: number
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
  statusProgress,
}: FinalOutputPanelProps) {
  const finalCopy = copy.finalOutput
  const progressPercent = Math.round(statusProgress * 100)
  return (
    <div className="h-full px-1">
      <Card className="column-panel flex h-full flex-col">
        <CardHeader className="flex-row items-center justify-between pb-4">
          <div>
            <CardTitle className="text-lg">{finalCopy.title}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {finalCopy.description}
            </p>
          </div>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-4 overflow-hidden">
          <Card className="border-accent/20 bg-accent/5 shadow-none">
            <CardHeader className="space-y-1 pb-2">
              <CardTitle className="text-sm font-semibold text-accent">
                {finalCopy.statusLabel}
              </CardTitle>
              <p className="text-sm text-muted-foreground">{status}</p>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="h-2 w-full rounded-full bg-accent/20">
                <div
                  className="h-full rounded-full bg-accent transition-[width] duration-500 ease-out"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <div className="mt-2 text-right text-xs font-medium text-muted-foreground">
                {progressPercent}%
              </div>
            </CardContent>
          </Card>
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
  isInterrupting: boolean
}

function StackedFallback({
  copy,
  nodes,
  finalResult,
  isRunning,
  onGenerate,
  onInterrupt,
  isInterrupting,
}: StackedFallbackProps) {
  const fallbackCopy = copy.stackedFallback
  const firstNodeId = nodes[0]?.id
  const nodeHasActivity = (node: WorkflowNode) =>
    node.status !== "waiting" ||
    node.transcript.length > 0 ||
    (isRunning && node.id === firstNodeId)

  const nodesWithActivity = nodes.filter(nodeHasActivity)
  const shouldShowNodes = nodesWithActivity.length > 0
  const nodesToRender = nodesWithActivity

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
            variant="destructive"
            className="flex-1"
            disabled={!isRunning || isInterrupting}
            onClick={onInterrupt}
            aria-busy={isInterrupting}
          >
            <PauseOctagon className="mr-2 h-4 w-4" />
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
                    {copy.nodes[node.id as keyof typeof copy.nodes]?.label ?? node.label}
                  </p>
                  <Badge variant="secondary">
                    {copy.nodeCard.statusBadges[node.status] ?? node.status}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  {node.status === "done" && node.summary
                    ? node.summary
                    : copy.nodes[node.id as keyof typeof copy.nodes]?.waitingSummary ?? node.summary}
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
