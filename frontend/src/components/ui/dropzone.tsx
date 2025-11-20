import * as React from "react"
import { UploadIcon } from "lucide-react"
import {
  useDropzone,
  type DropEvent,
  type DropzoneOptions,
  type FileRejection,
} from "react-dropzone"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type DropzoneContextType = {
  src?: File[]
  accept?: DropzoneOptions["accept"]
  maxSize?: DropzoneOptions["maxSize"]
  minSize?: DropzoneOptions["minSize"]
  maxFiles?: DropzoneOptions["maxFiles"]
}

const DropzoneContext = React.createContext<DropzoneContextType | undefined>(undefined)

const formatBytes = (bytes: number) => {
  const units = ["B", "KB", "MB", "GB", "TB", "PB"]
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)}${units[unitIndex]}`
}

export type DropzoneProps = Omit<DropzoneOptions, "onDrop"> & {
  className?: string
  src?: File[]
  children?: React.ReactNode
  onDrop?: (acceptedFiles: File[], fileRejections: FileRejection[], event: DropEvent) => void
  onError?: (error: Error) => void
  required?: boolean
}

const Dropzone = ({
  className,
  src,
  accept,
  maxFiles = 1,
  maxSize,
  minSize,
  onDrop,
  onError,
  disabled,
  children,
  required = false,
  ...props
}: DropzoneProps) => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept,
    maxFiles,
    maxSize,
    minSize,
    disabled,
    onDrop: (acceptedFiles, fileRejections, event) => {
      if (fileRejections.length > 0) {
        const message = fileRejections.at(0)?.errors.at(0)?.message
        if (message) {
          onError?.(new Error(message))
        }
      } else {
        onDrop?.(acceptedFiles, fileRejections, event)
      }
    },
    ...props,
  })
  const rootProps = getRootProps()
  const inputProps = getInputProps({ required })

  return (
    <DropzoneContext.Provider
      key={JSON.stringify(src)}
      value={{ src, accept, maxSize, minSize, maxFiles }}
    >
      <Button
        type="button"
        variant="outline"
        className={cn(
          "relative flex w-full min-h-[140px] flex-col items-center justify-center gap-4 overflow-hidden rounded-lg border-dashed p-6 text-center",
          isDragActive && "ring-2 ring-accent ring-offset-2",
          className
        )}
        disabled={disabled}
        {...rootProps}
      >
        <input {...inputProps} disabled={disabled} aria-required={required || undefined} />
        {children}
      </Button>
    </DropzoneContext.Provider>
  )
}

type WithChildren = {
  children?: React.ReactNode
  className?: string
}

const useDropzoneContext = () => {
  const context = React.useContext(DropzoneContext)
  if (!context) throw new Error("Dropzone components must be used within <Dropzone>")
  return context
}

const maxItems = 3

const DropzoneContent = ({ children, className }: WithChildren) => {
  const { src } = useDropzoneContext()
  if (!src?.length) return null
  if (children) return <div className={className}>{children}</div>

  const label =
    src.length > maxItems
      ? `${new Intl.ListFormat("en").format(src.slice(0, maxItems).map((file) => file.name))} and ${
          src.length - maxItems
        } more`
      : new Intl.ListFormat("en").format(src.map((file) => file.name))

  return (
    <div className={cn("flex w-full flex-col items-center gap-2", className)}>
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <UploadIcon className="h-5 w-5" />
      </div>
      <p className="text-sm font-medium text-foreground">{label}</p>
      <p className="text-xs text-muted-foreground">Drag & drop or click to replace</p>
    </div>
  )
}

const DropzoneEmptyState = ({ children, className }: WithChildren) => {
  const { src, accept, maxFiles, minSize, maxSize } = useDropzoneContext()
  if (src?.length) return null
  if (children) return <div className={className}>{children}</div>

  let caption = ""
  if (accept) {
    caption += `Accepts ${new Intl.ListFormat("en").format(Object.keys(accept))}`
  }
  if (minSize && maxSize) {
    caption += ` between ${formatBytes(minSize)} and ${formatBytes(maxSize)}`
  } else if (minSize) {
    caption += ` at least ${formatBytes(minSize)}`
  } else if (maxSize) {
    caption += ` less than ${formatBytes(maxSize)}`
  }

  return (
    <div className={cn("flex w-full flex-col items-center gap-2", className)}>
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <UploadIcon className="h-5 w-5" />
      </div>
      <p className="text-sm font-medium text-foreground">
        Upload {maxFiles === 1 ? "a file" : "files"}
      </p>
      <p className="text-xs text-muted-foreground">Drag & drop or click to upload</p>
      {caption ? <p className="text-xs text-muted-foreground">{caption}.</p> : null}
    </div>
  )
}

export { Dropzone, DropzoneContent, DropzoneEmptyState }


