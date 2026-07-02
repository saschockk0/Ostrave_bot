import { useEffect, useMemo, useState } from "react";

type HapticStyle = "light" | "medium" | "heavy" | "rigid" | "soft";

export type TgWebApp = {
  ready: () => void;
  expand: () => void;
  close: () => void;
  sendData: (data: string) => void;
  openLink: (url: string) => void;
  setHeaderColor?: (color: string) => void;
  setBackgroundColor?: (color: string) => void;
  HapticFeedback?: {
    impactOccurred: (style: HapticStyle) => void;
    notificationOccurred: (type: "error" | "success" | "warning") => void;
    selectionChanged: () => void;
  };
  initDataUnsafe?: {
    user?: { id: number; username?: string; first_name?: string };
  };
  colorScheme?: string;
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TgWebApp };
  }
}

export function useTelegram() {
  const tg = useMemo(
    () => (typeof window !== "undefined" ? window.Telegram?.WebApp : undefined),
    [],
  );
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!tg) {
      setReady(true);
      return;
    }
    try {
      tg.ready();
      tg.expand();
      tg.setHeaderColor?.("#f5821f");
      tg.setBackgroundColor?.("#fbf7ee");
    } catch {
      /* вне Telegram просто игнорируем */
    }
    setReady(true);
  }, [tg]);

  const haptic = (style: HapticStyle = "light") => {
    try {
      tg?.HapticFeedback?.impactOccurred(style);
    } catch {
      /* no-op */
    }
  };

  return { tg, ready, haptic, user: tg?.initDataUnsafe?.user };
}
