/** Zustand game session store. */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { GameSession, TurnPhase, TurnSummary } from "@/lib/types/game";
import type { WorldState } from "@/lib/types/world";
import { gameApi } from "@/lib/api/client";

interface GameState {
  // Session
  session: GameSession | null;
  worldState: WorldState | null;
  phase: TurnPhase;
  lastSummary: TurnSummary | null;
  loading: boolean;
  error: string | null;

  // Auto-play
  autoMode: boolean;
  autoSpeed: 2 | 3 | 4;

  // Actions
  createGame: (config?: Record<string, unknown>) => Promise<void>;
  loadGame: (gameId: string) => Promise<void>;
  setPhase: (phase: TurnPhase) => void;
  fetchWorldState: () => Promise<void>;
  advanceTurn: () => Promise<void>;
  setAutoMode: (enabled: boolean) => void;
  setAutoSpeed: (speed: 2 | 3 | 4) => void;
  reset: () => void;
}

export const useGameStore = create<GameState>()(
  persist(
    (set, get) => ({
      session: null,
      worldState: null,
      phase: "observe",
      lastSummary: null,
      loading: false,
      error: null,
      autoMode: false,
      autoSpeed: 2,

      createGame: async (config) => {
        set({ loading: true, error: null });
        try {
          const session = await gameApi.create(config);
          const worldState = await gameApi.getWorldState(session.id);
          set({
            session,
            worldState,
            phase: "observe",
            lastSummary: null,
            loading: false,
          });
        } catch (e) {
          set({ error: (e as Error).message, loading: false });
        }
      },

      loadGame: async (gameId) => {
        set({ loading: true, error: null });
        try {
          const session = await gameApi.get(gameId);
          const worldState = await gameApi.getWorldState(gameId);
          set({ session, worldState, loading: false });
        } catch (e) {
          set({ error: (e as Error).message, loading: false });
        }
      },

      setPhase: (phase) => set({ phase }),

      fetchWorldState: async () => {
        const { session } = get();
        if (!session) return;
        try {
          const worldState = await gameApi.getWorldState(session.id);
          set({ worldState });
        } catch (e) {
          set({ error: (e as Error).message });
        }
      },

      advanceTurn: async () => {
        const { session } = get();
        if (!session) return;
        set({ loading: true, error: null });
        try {
          const summary = await gameApi.nextTurn(session.id);
          const worldState = await gameApi.getWorldState(session.id);
          const updatedSession = await gameApi.get(session.id);
          set({
            session: updatedSession,
            worldState,
            lastSummary: summary,
            phase: "observe",
            loading: false,
          });
        } catch (e) {
          set({ error: (e as Error).message, loading: false });
        }
      },

      setAutoMode: (enabled) => set({ autoMode: enabled }),

      setAutoSpeed: (speed) => set({ autoSpeed: speed }),

      reset: () =>
        set({
          session: null,
          worldState: null,
          phase: "observe",
          lastSummary: null,
          loading: false,
          error: null,
          autoMode: false,
          autoSpeed: 2,
        }),
    }),
    {
      name: "world-game-store",
      partialize: (state) => ({
        session: state.session,
        phase: state.phase,
      }),
      // Add hydration options to prevent flash and timeout issues
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.error("Failed to rehydrate store:", error);
        } else if (state?.session) {
          console.log("Store rehydrated with session:", state.session.id);
        }
      },
      skipHydration: false,
      // Only persist session and phase, not worldState to avoid stale data
      merge: (persistedState, currentState) => {
        return {
          ...currentState,
          ...(persistedState as Partial<GameState>),
          // Always reset worldState on load to force refetch
          worldState: null,
          lastSummary: null,
          loading: false,
          error: null,
        };
      },
    }
  )
);
