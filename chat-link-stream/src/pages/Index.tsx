import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { useEffect } from "react";

const Index = () => {
  useEffect(() => {
    document.title = "Chat with a Stranger — Video & Text Chat";
  }, []);

  return (
    <main className="min-h-screen grid place-items-center bg-background">
      <section className="container max-w-3xl text-center p-8 animate-enter">
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4">Chat with a Stranger</h1>
        <p className="text-lg md:text-xl text-muted-foreground mb-8">Choose how you want to connect.</p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button asChild size="lg" variant="hero">
            <Link to="/video" aria-label="Start a video chat">Video Chat</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link to="/text" aria-label="Start a text chat">Text Chat</Link>
          </Button>
        </div>
      </section>
    </main>
  );
};

export default Index;
