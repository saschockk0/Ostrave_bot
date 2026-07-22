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
  // Подписанная строка запуска: ею бот проверяет, что заявка пришла от
  // настоящего пользователя Telegram (см. services/webapi.py).
  initData?: string;
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
      tg.setHeaderColor?.("#0b2431");
      tg.setBackgroundColor?.("#0b2431");
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

  return { tg, ready, haptic, user: tg?.initDataUnsafe?.user, initData: tg?.initData };
}
