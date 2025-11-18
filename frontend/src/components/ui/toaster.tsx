"use client"

import { Toast, ToastViewport } from "@/components/ui/toast"
import { ToastProvider } from "@/components/ui/toast"
import { useToast } from "@/components/ui/use-toast"

export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider>
      {toasts.map(function ({ id, ...props }) {
        return <Toast key={id} {...props} />
      })}
      <ToastViewport className="right-4 top-6 md:right-1/2 md:top-8 md:translate-x-1/2 md:w-[380px]" />
    </ToastProvider>
  )
}

