import { useEffect, useState } from "react";
import { getHealth } from "../api/settings";
import { HealthResponse } from "../types";

const RESOURCE_POLL_INTERVAL_MS = 20_000;

type PerformanceMemory = {
  usedJSHeapSize: number;
};

type ExtendedPerformance = Performance & {
  memory?: PerformanceMemory;
};

export type ResourceUsage = {
  backendCpuPercent: number | null;
  backendMemoryMb: number | null;
  frontendMemoryMb: number | null;
  health: HealthResponse | null;
};

const readFrontendMemoryMb = (): number | null => {
  const perf = performance as ExtendedPerformance;
  if (!perf.memory) {
    return null;
  }
  return Math.round(perf.memory.usedJSHeapSize / (1024 * 1024));
};

export const useResourceUsage = () => {
  const [resources, setResources] = useState<ResourceUsage>({
    backendCpuPercent: null,
    backendMemoryMb: null,
    frontendMemoryMb: readFrontendMemoryMb(),
    health: null,
  });

  useEffect(() => {
    const fetchResources = async () => {
      try {
        const health = await getHealth();
        setResources({
          backendCpuPercent: health.backend_cpu_percent ?? null,
          backendMemoryMb: health.backend_memory_mb ?? null,
          frontendMemoryMb: readFrontendMemoryMb(),
          health,
        });
      } catch {
        setResources((prev) => ({
          ...prev,
          frontendMemoryMb: readFrontendMemoryMb(),
          health: null,
        }));
      }
    };

    fetchResources();
    const interval = window.setInterval(fetchResources, RESOURCE_POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, []);

  return resources;
};
