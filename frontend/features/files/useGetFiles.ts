"use client";

import { useEffect, useRef, useState } from "react";
import { getFiles } from "./server-actions";
import { ProjectFile } from "./types";

const POLL_INTERVAL = 3000;
const MAX_POLLS = 100; // about five minutes
const MAX_CONSECUTIVE_FAILURES = 3;

export default function useGetFiles(projectId: number) {
  const oldProjectId = useRef<null | number>(null);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [pollingStopped, setPollingStopped] = useState(false);

  useEffect(() => {
    if (oldProjectId.current !== projectId) {
      setFiles([]);
      setPollingStopped(false);
      oldProjectId.current = projectId;
    }

    async function fetchFiles(): Promise<ProjectFile[] | null> {
      setIsLoading(true);

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
        if (failures >= MAX_CONSECUTIVE_FAILURES) {
          setError("Sorry, could not get files...");
          return;
        }
        // Back off before retrying a failed request.
        timeoutId = setTimeout(pollFiles, POLL_INTERVAL * 2 ** failures);
        return;
      }

      failures = 0;
      setError("");

      const hasUnfinishedFiles = result.some(
        (file) => file.status === "pending" || file.status === "processing",
      );

      if (!hasUnfinishedFiles) return;

      if (polls >= MAX_POLLS) {
        setPollingStopped(true);
        return;
      }
      timeoutId = setTimeout(pollFiles, POLL_INTERVAL);
    }

    pollFiles();

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [projectId]);

  return { files, isLoading, error, pollingStopped };
}
