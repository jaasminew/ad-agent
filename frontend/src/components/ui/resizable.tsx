import * as React from "react"
import {
  PanelGroup,
  type PanelGroupProps,
  Panel,
  type PanelProps,
  PanelResizeHandle,
  type PanelResizeHandleProps,
} from "react-resizable-panels"

import { cn } from "@/lib/utils"

const ResizablePanelGroup = ({
  className,
  ...props
}: PanelGroupProps & { className?: string }) => {
  return (
    <PanelGroup
      className={cn(
        "flex h-full w-full items-stretch gap-px text-sm data-[panel-group-direction=vertical]:flex-col",
        className
      )}
      {...props}
    />
  )
}

const ResizablePanel = ({ className, ...props }: PanelProps) => (
  <Panel className={cn("flex flex-col", className)} {...props} />
)

const ResizableHandle = ({
  className,
  hitAreaMargins = { coarse: 12, fine: 6 },
  ...props
}: PanelResizeHandleProps & React.HTMLAttributes<HTMLDivElement>) => (
  <PanelResizeHandle
    hitAreaMargins={hitAreaMargins}
    className={cn(
      "relative flex items-center justify-center",
      "cursor-col-resize data-[panel-group-direction=vertical]:cursor-row-resize",
      "data-[panel-group-direction=horizontal]:h-full data-[panel-group-direction=horizontal]:w-px",
      "data-[panel-group-direction=vertical]:w-full data-[panel-group-direction=vertical]:h-px",
      "touch-none select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
      className
    )}
    {...props}
  />
)

export { ResizableHandle, ResizablePanel, ResizablePanelGroup }

