import { Link } from "react-router-dom"

export default function SampleGalleryPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-background px-6 py-16 text-center text-foreground">
      <div className="max-w-2xl space-y-6">
        <p className="text-sm uppercase tracking-widest text-muted-foreground">Coming Soon</p>
        <h1 className="text-3xl font-semibold">Generated Video Gallery</h1>
        <p className="text-base text-muted-foreground">
          We&apos;re preparing a curated set of sample videos. Check back soon to explore what the agent can create.
        </p>
        <Link
          to="/"
          className="inline-flex items-center justify-center rounded-full border border-foreground/20 px-4 py-2 text-sm font-semibold text-accent hover:border-accent hover:text-accent"
        >
          ← Back to workspace
        </Link>
      </div>
    </main>
  )
}

