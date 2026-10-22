"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun, Laptop } from "lucide-react";
import { Button } from "@/components/ui/button";

type Theme = "light" | "dark" | "system";

const listeners = new Set<() => void>();

function readTheme(): Theme {
  const saved = localStorage.getItem("theme");
  return saved === "light" || saved === "dark" ? saved : "system";
}

function subscribeToTheme(onChange: () => void) {
  listeners.add(onChange);
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

function applyTheme(theme: Theme) {
  const root = window.document.documentElement;

  root.classList.remove("light", "dark");

  if (theme === "system") {
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)")
      .matches
      ? "dark"
      : "light";
    root.classList.add(systemTheme);
  } else {
    root.classList.add(theme);
  }
}

function saveTheme(theme: Theme) {
  localStorage.setItem("theme", theme);
  applyTheme(theme);
  listeners.forEach((listener) => listener());
}

const subscribeNever = () => () => {};

export function ThemeToggle() {
  const theme = useSyncExternalStore(
    subscribeToTheme,
    readTheme,
    () => "system" as Theme,
  );
  const mounted = useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false,
  );
  const handleThemeChange = saveTheme;

  // Prevent hydration mismatch
  if (!mounted) {
    return (
      <div className="h-10 w-full max-w-[400px] animate-pulse bg-muted rounded-md" />
    );
  }

  return (
    <div className="flex gap-2 flex-wrap">
      <Button
        variant={theme === "light" ? "default" : "outline"}
        onClick={() => handleThemeChange("light")}
        className="flex-1 min-w-[100px]"
      >
        <Sun className="mr-2 h-4 w-4" />
        Light
      </Button>
      <Button
        variant={theme === "dark" ? "default" : "outline"}
        onClick={() => handleThemeChange("dark")}
        className="flex-1 min-w-[100px]"
      >
        <Moon className="mr-2 h-4 w-4" />
        Dark
      </Button>
      <Button
        variant={theme === "system" ? "default" : "outline"}
        onClick={() => handleThemeChange("system")}
        className="flex-1 min-w-[100px]"
      >
        <Laptop className="mr-2 h-4 w-4" />
        System
      </Button>
    </div>
  );
}
