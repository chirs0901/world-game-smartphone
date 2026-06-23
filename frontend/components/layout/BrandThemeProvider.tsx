"use client";

import { useEffect } from "react";
import { useGameStore } from "@/lib/store/gameStore";
import { BRAND_COLORS } from "@/lib/config/brandColors";

export default function BrandThemeProvider({ children }: { children: React.ReactNode }) {
  const session = useGameStore((s) => s.session);

  useEffect(() => {
    const companyId = session?.config.company_id;
    const colors = companyId ? BRAND_COLORS[companyId] : null;

    const root = document.documentElement;
    if (colors) {
      root.style.setProperty("--brand-primary", colors.primary);
      root.style.setProperty("--brand-primary-light", colors.primaryLight);
      root.style.setProperty("--brand-primary-dark", colors.primaryDark);
      root.style.setProperty("--brand-accent", colors.accent);
      root.style.setProperty("--brand-sidebar-bg", colors.sidebarBg);
      root.style.setProperty("--brand-text-on-primary", colors.textOnPrimary);
    } else {
      // Default blue theme
      root.style.setProperty("--brand-primary", "#3B82F6");
      root.style.setProperty("--brand-primary-light", "#60A5FA");
      root.style.setProperty("--brand-primary-dark", "#1D4ED8");
      root.style.setProperty("--brand-accent", "#3B82F6");
      root.style.setProperty("--brand-sidebar-bg", "#0F172A");
      root.style.setProperty("--brand-text-on-primary", "#FFFFFF");
    }
  }, [session?.config.company_id]);

  return <>{children}</>;
}
