import React from "react"
import { useNavigate } from "react-router-dom"

import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { translations, type Language } from "@/locales"
import { WORKSPACE_STARTED_KEY } from "@/constants/workspace"

const LANGUAGE_STORAGE_KEY = "language"

const getStoredLanguage = (): Language => {
  if (typeof window === "undefined") {
    return "en"
  }
  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
  return stored === "zh" ? "zh" : "en"
}

export default function SampleGalleryPage() {
  const navigate = useNavigate()
  const [language] = React.useState<Language>(getStoredLanguage)
  const copy = translations[language]?.gallery ?? translations.en.gallery

  React.useEffect(() => {
    if (typeof document === "undefined") return
    const { style } = document.body
    const previousOverflow = style.overflow
    const previousHeight = style.height

    style.overflow = "auto"
    style.height = "auto"

    return () => {
      style.overflow = previousOverflow
      style.height = previousHeight
      window.scrollTo(0, 0)
    }
  }, [])

  const handleBackToWorkspace = React.useCallback(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(WORKSPACE_STARTED_KEY, "true")
    }
    navigate("/")
  }, [navigate])

  return (
    <main className="min-h-screen bg-background px-6 py-16 text-foreground">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-12">
        <header className="space-y-4 text-center">
          <h1 className="text-3xl font-semibold">{copy.title}</h1>
          <p className="text-base text-muted-foreground">{copy.subtitle}</p>
        </header>

        <section className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {copy.samples.map((sample) => (
            <Card key={sample.src} className="overflow-hidden border-foreground/10 shadow-sm">
              <CardContent className="p-0">
                <video
                  src={sample.src}
                  controls
                  playsInline
                  preload="metadata"
                  className="h-64 w-full bg-black object-cover"
                />
              </CardContent>
              <CardFooter className="border-t border-border/60 px-4 py-3">
                <p className="text-sm font-semibold">{sample.title}</p>
              </CardFooter>
            </Card>
          ))}
        </section>

        <div className="text-center">
          <button
            type="button"
            onClick={handleBackToWorkspace}
            className="inline-flex items-center justify-center rounded-full border border-foreground/20 px-4 py-2 text-sm font-semibold text-accent hover:border-accent hover:text-accent"
          >
            {copy.backButton}
          </button>
        </div>
      </div>
    </main>
  )
}

