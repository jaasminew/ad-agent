import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import backgroundImage from "./Images/background.png";

interface LandingPageProps {
  onEnter: () => void;
}

export function LandingPage({ onEnter }: LandingPageProps) {
  return (
    <div className="min-h-screen w-full bg-[#030303] text-white overflow-hidden relative flex flex-col font-sans selection:bg-white/20">
      {/* Background Image */}
      <div className="absolute inset-0 z-0">
        <img 
          src={backgroundImage} 
          alt="Background" 
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-black/20 pointer-events-none" /> {/* Subtle overlay to ensure text contrast if needed */}
        
        {/* Particle/Dust Effect */}
        <div className="absolute inset-0 pointer-events-none">
           {/* Creating multiple layers of particles for depth */}
           {[...Array(100)].map((_, i) => (
             <div
               key={i}
               className="absolute rounded-full bg-white/30 blur-[1px] animate-float"
               style={{
                 top: `${Math.random() * 100}%`,
                 left: `${Math.random() * 100}%`,
                 width: `${Math.random() * 3 + 1}px`,
                 height: `${Math.random() * 3 + 1}px`,
                 animationDuration: `${Math.random() * 10 + 10}s`,
                 animationDelay: `${Math.random() * 5}s`,
               }}
             />
           ))}
        </div>
      </div>

      <div className="z-10 flex flex-col items-center pt-24 px-6 text-center w-full max-w-[1400px] mx-auto">
        {/* Logo/Title */}
        <div className="relative mb-8">
             {/* Title Glow */}
             <div className="absolute inset-0 bg-white/20 blur-3xl rounded-full opacity-20 pointer-events-none" />
             
             {/* Title Particles (Dissolving Edges) */}
             <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div className="w-[120%] h-full relative">
                   {/* Creating particles concentrated around the text edges */}
                   {[...Array(40)].map((_, i) => (
                     <div
                       key={i}
                       className="absolute rounded-full bg-white/80 blur-[0.5px] animate-dissolve"
                       style={{
                         // Distribute particles mainly along the horizontal axis of the text
                         left: `${10 + Math.random() * 80}%`,
                         // Distribute vertically with some randomness to cover top/bottom edges
                         top: `${Math.random() * 100}%`,
                         width: `${Math.random() * 2 + 1}px`,
                         height: `${Math.random() * 2 + 1}px`,
                         animationDelay: `${Math.random() * 2}s`,
                       }}
                     />
                   ))}
                </div>
             </div>

             <h1 className="text-6xl md:text-8xl font-bold tracking-tighter bg-gradient-to-b from-white to-white/70 bg-clip-text text-transparent relative z-10 py-2 pb-4 blur-[0.5px]">
              AD.Agent
            </h1>
        </div>
        
        {/* Subtitle */}
        <p className="text-lg md:text-xl text-white/60 font-light max-w-2xl mb-12 leading-relaxed tracking-wide">
          全自动广告视频创作平台，帮助品牌轻松完成从想法到成片的整个流程。
        </p>

        {/* CTA Button */}
        <Button 
          size="lg" 
          onClick={onEnter}
          className="bg-white text-black hover:bg-white/90 hover:scale-105 transition-all duration-300 rounded-full px-10 h-14 text-base font-medium mb-20 shadow-[0_0_20px_-5px_rgba(255,255,255,0.3)]"
        >
          Try It Out <ArrowRight className="ml-2 h-4 w-4" />
        </Button>

        {/* App Screenshot Mockup */}
        <div 
          className="relative w-full bg-black/40 backdrop-blur-xl rounded-t-xl border border-white/10 shadow-[0_20px_50px_-12px_rgba(0,0,0,0.5),0_0_30px_-5px_rgba(100,103,240,0.15)] overflow-hidden animate-in fade-in slide-in-from-bottom-8 duration-1000 ease-out"
        >
            {/* Window Controls */}
            <div className="h-10 border-b border-white/5 bg-white/5 flex items-center px-4 justify-between">
                <div className="flex items-center gap-1.5 opacity-50">
                    <div className="text-xs text-white/40 font-medium px-2">智能体控制室</div>
                </div>
                <div className="flex gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/20" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/20" />
                </div>
            </div>
            
            {/* Mockup Body - Abstract UI Representation */}
            <div className="aspect-[16/9] w-full bg-transparent p-4 grid grid-cols-12 gap-4">
                 {/* Left Sidebar */}
                 <div className="hidden md:block col-span-3 h-full rounded-lg border border-white/5 bg-white/[0.02] p-4 space-y-4">
                    <div className="h-4 w-1/3 bg-white/10 rounded" />
                    <div className="h-8 w-full bg-white/5 rounded" />
                    <div className="h-24 w-full bg-white/5 rounded mt-4" />
                    <div className="h-24 w-full bg-white/5 rounded" />
                    <div className="flex-1" />
                    <div className="h-10 w-full bg-indigo-500/20 rounded border border-indigo-500/30" />
                 </div>
                 
                 {/* Center Panel - Node Canvas Skeleton */}
                 <div className="col-span-12 md:col-span-5 h-full rounded-lg border border-white/5 bg-white/[0.02] relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/50 pointer-events-none" />
                    
                    {/* Header */}
                    <div className="absolute top-4 left-4 right-4">
                        <div className="h-4 w-1/4 bg-white/10 rounded" />
                    </div>
                    
                    {/* Nodes Container */}
                    <div className="absolute inset-0 top-12 p-4 flex flex-col items-center gap-6">
                        {/* Connecting Line (SVG) */}
                        <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-30">
                            <line x1="50%" y1="40" x2="50%" y2="100%" stroke="white" strokeWidth="2" strokeDasharray="4 4" />
                        </svg>

                        {/* Node 1 (Active - Accent) */}
                        <div className="relative z-10 w-48 h-20 rounded-lg border border-accent/30 bg-[#0A0A0A] backdrop-blur flex flex-col justify-center px-4 gap-2 shadow-[0_0_15px_-5px_rgba(100,103,240,0.3)]">
                            <div className="flex items-center gap-2">
                                <div className="w-2.5 h-2.5 rounded-full bg-accent animate-pulse" />
                                <div className="h-2.5 w-20 bg-white/20 rounded" />
                            </div>
                            <div className="h-2 w-full bg-white/10 rounded" />
                        </div>

                        {/* Node 2 (Gray Scale) */}
                        <div className="relative z-10 w-48 h-20 rounded-lg border border-white/10 bg-[#0A0A0A] backdrop-blur flex flex-col justify-center px-4 gap-2">
                             <div className="flex items-center gap-2">
                                <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
                                <div className="h-2.5 w-24 bg-white/20 rounded" />
                             </div>
                             <div className="h-2 w-full bg-white/10 rounded" />
                             <div className="h-2 w-2/3 bg-white/10 rounded" />
                        </div>

                        {/* Node 3 (Gray Scale) */}
                        <div className="relative z-10 w-48 h-20 rounded-lg border border-white/10 bg-[#0A0A0A] backdrop-blur flex flex-col justify-center px-4 gap-2">
                             <div className="flex items-center gap-2">
                                <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
                                <div className="h-2.5 w-16 bg-white/10 rounded" />
                             </div>
                             <div className="h-2 w-3/4 bg-white/5 rounded" />
                        </div>
                    </div>
                 </div>
                 
                 {/* Right Panel */}
                 <div className="hidden md:block col-span-4 h-full rounded-lg border border-white/5 bg-white/[0.02] p-4">
                    <div className="h-4 w-1/4 bg-white/10 rounded mb-4" />
                    <div className="aspect-video w-full bg-white/5 rounded-lg border border-white/5 flex items-center justify-center">
                         <div className="w-8 h-8 rounded-full border-2 border-white/20" />
                    </div>
                    <div className="mt-4 space-y-2">
                        <div className="h-2 w-full bg-white/10 rounded" />
                        <div className="h-2 w-full bg-white/10 rounded" />
                        <div className="h-2 w-2/3 bg-white/10 rounded" />
                    </div>
                 </div>
            </div>
        </div>
      </div>
    </div>
  );
}

