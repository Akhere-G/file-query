"use client";

import { useEffect, useState } from "react";
import { Moon, Sun, Laptop } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark" | "system">("system");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const savedTheme = localStorage.getItem("theme") as "light" | "dark" | "system" | null;
    if (savedTheme) {
      setTheme(savedTheme);
      applyTheme(savedTheme);
    } else {
      applyTheme("system");
    }
  }, []);

  const applyTheme = (newTheme: "light" | "dark" | "system") => {
    const root = window.document.documentElement;
    
    root.classList.remove("light", "dark");
    
    if (newTheme === "system") {
      const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      root.classList.add(systemTheme);
    } else {
      root.classList.add(newTheme);
    }
  };

  const handleThemeChange = (newTheme: "light" | "dark" | "system") => {
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    applyTheme(newTheme);
  };

  // Prevent hydration mismatch
  if (!mounted) {
    return <div className="h-10 w-full max-w-[400px] animate-pulse bg-muted rounded-md" />;
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
