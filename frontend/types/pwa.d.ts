/** PWA install prompt event - supported in Chromium browsers */
interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
  prompt(): Promise<void>;
}

interface WindowEventMap {
  beforeinstallprompt: BeforeInstallPromptEvent;
  appinstalled: Event;
}
