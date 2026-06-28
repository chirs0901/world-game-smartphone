/** Brand color configuration for each company. */

export interface BrandColors {
  primary: string;
  primaryLight: string;
  primaryDark: string;
  accent: string;
  sidebarBg: string;
  textOnPrimary: string;
}

export const BRAND_COLORS: Record<string, BrandColors> = {
  apple: {
    primary: "#0071E3",
    primaryLight: "#5E9EFF",
    primaryDark: "#004A9F",
    accent: "#86868B",
    sidebarBg: "#1D1D1F",
    textOnPrimary: "#FFFFFF",
  },
  samsung: {
    primary: "#1428A0",
    primaryLight: "#3B5FE0",
    primaryDark: "#0A1A6E",
    accent: "#3B82F6",
    sidebarBg: "#0A1A6E",
    textOnPrimary: "#FFFFFF",
  },
  huawei: {
    primary: "#CF0A2C",
    primaryLight: "#FF3B5C",
    primaryDark: "#A00820",
    accent: "#1A1A2E",
    sidebarBg: "#1A1A2E",
    textOnPrimary: "#FFFFFF",
  },
  oppo: {
    primary: "#1EA366",
    primaryLight: "#34D399",
    primaryDark: "#065F46",
    accent: "#10B981",
    sidebarBg: "#064E3B",
    textOnPrimary: "#FFFFFF",
  },
  vivo: {
    primary: "#415FFF",
    primaryLight: "#6B8CFF",
    primaryDark: "#1E3A8A",
    accent: "#60A5FA",
    sidebarBg: "#1E3A8A",
    textOnPrimary: "#FFFFFF",
  },
  xiaomi: {
    primary: "#FF6900",
    primaryLight: "#FF9B40",
    primaryDark: "#CC5500",
    accent: "#F97316",
    sidebarBg: "#7C2D12",
    textOnPrimary: "#FFFFFF",
  },
  honor: {
    primary: "#1A73E8",
    primaryLight: "#4DA3FF",
    primaryDark: "#0D47A1",
    accent: "#4285F4",
    sidebarBg: "#0D2137",
    textOnPrimary: "#FFFFFF",
  },
  nothing: {
    primary: "#FFD700",
    primaryLight: "#FFED4A",
    primaryDark: "#B8860B",
    accent: "#FBBF24",
    sidebarBg: "#1A1A1A",
    textOnPrimary: "#1A1A1A",
  },
};
