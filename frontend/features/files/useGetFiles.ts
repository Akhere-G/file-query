"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getFiles } from "./server-actions";
import { ProjectFile } from "./types";

const POLL_INTERVAL = 3000;
const MAX_POLLS = 100;
const MAX_FAILURES = 3;

export default function useGetFiles(projectId: number) {
  const oldProjectId = useRef<null | number>(null);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const isNewProject = oldProjectId.current !== projectId;
    if (isNewProject) {
      setFiles([]);
      oldProjectId.current = projectId;
    }
    async function fetchFiles() {
      if (isNewProject && polls === 1) setIsLoading(true);

      try {
        if (projectId <= 0) return [];
        const res = await getFiles(projectId);

        if (!res.success) return null;

        setFiles(res.data);
        return res.data;
      } catch {
        return null;
      } finally {
        setIsLoading(false);
      }
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout>;
    let polls = 0;
    let failures = 0;

    async function pollFiles() {
      polls++;
      const result = await fetchFiles();

      if (cancelled) return;

      if (result === null) {
        failures++;
        if (failures >= MAX_FAILURES) {
          setError("Sorry, could not get files...");
          return;
        }
        timeoutId = setTimeout(pollFiles, POLL_INTERVAL);
        return;
      }

      failures = 0;
      setError("");

      const hasUnfinishedFiles = result.some(
        (file) => file.status === "pending" || file.status === "processing",
      );

      if (hasUnfinishedFiles && polls < MAX_POLLS) {
        timeoutId = setTimeout(pollFiles, POLL_INTERVAL);
      }
    }

    pollFiles();

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [projectId, refreshKey]);

  const refetch = useCallback(() => setRefreshKey((key) => key + 1), []);

  return { files, isLoading, error, refetch };
}
