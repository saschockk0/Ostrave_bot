import { useRef } from "react";
import { useTelegram } from "./hooks/useTelegram";
import { Hero } from "./sections/Hero";
import { Facts } from "./sections/Facts";
import { Program } from "./sections/Program";
import { Venue } from "./sections/Venue";
import { Apply } from "./sections/Apply";
import { Footer } from "./sections/Footer";
import { StickyCTA } from "./components/StickyCTA";

export default function App() {
  // Инициализация Telegram WebApp (expand, цвета хедера/фона).
  useTelegram();

  const applyRef = useRef<HTMLElement>(null);
  const scrollToApply = () =>
    applyRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="grain mx-auto min-h-[100dvh] max-w-[560px] border-ink/10 sm:border-x">
      <Hero onApply={scrollToApply} />
      <Facts />
      <Program />
      <Venue />
      <Apply sectionRef={applyRef} />
      <Footer onApply={scrollToApply} />
      <StickyCTA targetRef={applyRef} onClick={scrollToApply} />
    </div>
  );
}
