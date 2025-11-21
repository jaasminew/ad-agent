import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatFileNameForDisplay(fileName: string, maxBaseLength = 10) {
  if (!fileName) {
    return ""
  }
  const lastDotIndex = fileName.lastIndexOf(".")
  const hasExtension = lastDotIndex > 0 && lastDotIndex < fileName.length - 1
  const extension = hasExtension ? fileName.slice(lastDotIndex) : ""
  const baseName = hasExtension ? fileName.slice(0, lastDotIndex) : fileName
  const truncatedBase =
    maxBaseLength > 0 && baseName.length > maxBaseLength ? baseName.slice(0, maxBaseLength) : baseName
  return `${truncatedBase}${extension}`
}

