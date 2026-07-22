import { useRef } from "react";
import { useTelegram } from "./hooks/useTelegram";
import { Hero } from "./sections/Hero";
import { Facts } from "./sections/Facts";
import { Program } from "./sections/Program";
import { Prices } from "./sections/Prices";
import { Venue } from "./sections/Venue";
import { Faq } from "./sections/Faq";
import { Apply } from "./sections/Apply";
import { Footer } from "./sections/Footer";
import { StickyCTA } from "./components/StickyCTA";

export default function App() {
  // Инициализация Telegram WebApp (expand, цвета хедера/фона).
  useTelegram();

  const applyRef = useRef<HTMLElement>(null);
  const heroRef = useRef<HTMLElement>(null);
  const scrollToApply = () =>
    applyRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="mx-auto min-h-[100dvh] max-w-[560px] border-foam/10 sm:border-x">
      <Hero sectionRef={heroRef} onApply={scrollToApply} />
      <Facts />
      <Program />
      <Prices />
      <Venue />
      <Faq />
      <Apply sectionRef={applyRef} />
      <Footer onApply={scrollToApply} />
      <StickyCTA targetRef={applyRef} heroRef={heroRef} onClick={scrollToApply} />
    </div>
  );
}
