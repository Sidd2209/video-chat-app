import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { useEffect } from "react";

const Index = () => {
  useEffect(() => {
    document.title = "Video Chat with a Stranger";
  }, []);

  return (
    <main className="min-h-screen grid place-items-center bg-background">
      <section className="container max-w-3xl text-center p-8 animate-enter">
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4">Video Chat with a Stranger</h1>
        <p className="text-lg md:text-xl text-muted-foreground mb-8">Connect instantly with random people via video chat.</p>
        <div className="flex items-center justify-center">
          <Button asChild size="lg" variant="hero">
            <Link to="/video" aria-label="Start a video chat">Start Video Chat</Link>
          </Button>
        </div>
      </section>
    </main>
  );
};

export default Index;
