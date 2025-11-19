"use client"

import {
  CircleCheck,
  Info,
  Loader2,
  OctagonX,
  TriangleAlert,
} from "lucide-react"
import { Toaster as SonnerToaster, type ToasterProps } from "sonner"

const iconClassName = "h-4 w-4"

const baseToastClass =
  "group rounded-xl border border-border/60 bg-background/95 text-foreground shadow-xl backdrop-blur supports-[backdrop-filter]:backdrop-blur-md"

const titleClass = "text-sm font-semibold leading-tight"
const descriptionClass = "text-xs text-muted-foreground"

const actionButtonClass =
  "rounded-full bg-primary/90 px-3 py-1 text-xs font-medium text-primary-foreground transition hover:bg-primary"
const cancelButtonClass =
  "rounded-full bg-muted/70 px-3 py-1 text-xs font-medium text-foreground transition hover:bg-muted"

const icons = {
  success: <CircleCheck className={iconClassName} />,
  info: <Info className={iconClassName} />,
  warning: <TriangleAlert className={iconClassName} />,
  error: <OctagonX className={iconClassName} />,
  loading: <Loader2 className={`${iconClassName} animate-spin`} />,
}

const toastOptions: ToasterProps["toastOptions"] = {
  className: baseToastClass,
  classNames: {
    title: titleClass,
    description: descriptionClass,
    actionButton: actionButtonClass,
    cancelButton: cancelButtonClass,
  },
}

type Props = ToasterProps

export function Toaster(props: Props) {
  return (
    <SonnerToaster
      icons={icons}
      toastOptions={toastOptions}
      closeButton
      richColors
      expand
      {...props}
    />
  )
}

