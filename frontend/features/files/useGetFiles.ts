"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getFiles } from "./server-actions";
import { ProjectFile } from "./types";

const POLL_INTERVAL = 3000;

export default function useGetFiles(projectId: number) {
  const oldProjectId = useRef<null | number>(null);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (oldProjectId.current !== projectId) {
      setFiles([]);
      oldProjectId.current = projectId;
    }
    async function fetchFiles() {
      setIsLoading(true);
      setError("");

      try {
        if (projectId <= 0) return;
        const res = await getFiles(projectId);

        if (!res.success) {
          setError("Sorry, could not get files...");
          return null;
        }

        setFiles(res.data);
        return res.data;
      } catch {
        setError("Sorry, could not get files...");
        return null;
      } finally {
        setIsLoading(false);
      }
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout>;

    async function pollFiles() {
      const result = await fetchFiles();

      if (cancelled || result === null) return;

      const hasUnfinishedFiles = result?.some(
        (file) => file.status === "pending" || file.status === "processing",
      );

      if (hasUnfinishedFiles) {
        timeoutId = setTimeout(pollFiles, POLL_INTERVAL);
      }
    }

    pollFiles();

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [projectId]);

  return { files, isLoading, error };
}
