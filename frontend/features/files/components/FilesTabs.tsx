"use client";

import { Input } from "@/components/ui/input";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";

import { FileWarningIcon, Info, Upload, X } from "lucide-react";
import { getFileIcon, getSizeStr } from "../utils";
import { confirmUploads, uploadFiles } from "../server-actions";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { sendFilesToS3 } from "../actions";
import {
  MAX_FILE_SIZE_MB,
  MAX_FILES_PER_UPLOAD,
  mimeTypeFor,
} from "../constants";

import FileCard from "./FileCard";
import {
  Attachment,
  AttachmentContent,
  AttachmentDescription,
  AttachmentMedia,
  AttachmentTitle,
} from "@/components/ui/attachment";
import { toast } from "@/components/ui/toast";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ProjectFile } from "../types";
import { track } from "@/lib/analytics/client";
import { failureReason, fileTypeLabel } from "@/lib/analytics/events";

interface FileTabProps {
  files: ProjectFile[];
  isLoading: boolean;
  error: string;
  isDemo?: boolean;
}
const FilesTabs = ({
  files,
  isLoading,
  error,
  isDemo = false,
}: FileTabProps) => {
  const [isPending, setIsPending] = useState(false);
  const [errorMessages, setErrorMessages] = useState<Record<string, string[]>>(
    {},
  );
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const projectId = searchParams.get("projectId");
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isDragEnter, setIsDragEnter] = useState(false);
  const dragCounter = useRef(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragCounter.current++;
    setIsDragEnter(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragCounter.current--;

    if (dragCounter.current === 0) {
      setIsDragEnter(false);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const addFiles = (selected: File[]) => {
    const unsupported = selected.filter((f) => mimeTypeFor(f.name) === null);
    if (unsupported.length > 0) {
      toast.add({
        title: `${unsupported.map((f) => f.name).join(", ")}: only PDF, DOC, DOCX, CSV, TXT and MD files are supported`,
        type: "error",
      });
    }
    const newFiles = selected.filter((f) => !unsupported.includes(f));
    const tooBig = newFiles.filter(
      (f) => f.size >= MAX_FILE_SIZE_MB * 1024 * 1024,
    );
    if (tooBig.length > 0) {
      toast.add({
        title: `${tooBig.map((f) => f.name).join(", ")} is larger than ${MAX_FILE_SIZE_MB}MB`,
        type: "error",
      });
    }
    setUploadedFiles((current) => {
      const accepted = newFiles.filter((f) => !tooBig.includes(f));
      const next = [...current, ...accepted];
      if (next.length > MAX_FILES_PER_UPLOAD) {
        toast.add({
          title: `You can upload up to ${MAX_FILES_PER_UPLOAD} files at a time`,
          type: "error",
        });
        return next.slice(0, MAX_FILES_PER_UPLOAD);
      }
      return next;
    });
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();

    dragCounter.current = 0;
    setIsDragEnter(false);

    addFiles(Array.from(e.dataTransfer.files));
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    addFiles(Array.from(e.target.files ?? []));

    e.target.value = "";
  };

  const removeFile = (index: number) => {
    setUploadedFiles((files) => files.filter((_, i) => i !== index));
  };

  async function handleUpload() {
    if (!uploadedFiles) {
      return;
    }
    setIsPending(true);

    const startedAt = Date.now();
    const uploadProps = {
      file_count: uploadedFiles.length,
      total_size_bytes: uploadedFiles.reduce((sum, f) => sum + f.size, 0),
      file_types: [...new Set(uploadedFiles.map((f) => fileTypeLabel(f.type)))],
      is_new_project: !projectId,
    };
    let stage: "presign" | "s3" | "confirm" = "presign";
    let failureTracked = false;
    track("file_upload_started", uploadProps);

    try {
      setErrorMessages({});
      const res = await uploadFiles(
        uploadedFiles,
        projectId ? Number(projectId) : undefined,
      );

      if (!res.success) {
        failureTracked = true;
        track("file_upload_failed", {
          ...uploadProps,
          stage,
          reason: failureReason(res.message ?? undefined, res.status),
        });
        setErrorMessages(
          res.details ?? { general: ["Something went wrong..."] },
        );
        throw new Error(res.message ?? "Something went wrong...");
      }

      const presignedFiles = res.data.files;
      stage = "s3";
      const s3res = await sendFilesToS3(presignedFiles, uploadedFiles);

      stage = "confirm";
      const confirmRes = await confirmUploads(s3res);

      if (s3res.some((r) => r.error)) {
        failureTracked = true;
        track("file_upload_failed", {
          ...uploadProps,
          stage: "s3",
          reason: "storage_error",
        });
      } else if (!confirmRes.success) {
        failureTracked = true;
        track("file_upload_failed", {
          ...uploadProps,
          stage,
          reason: failureReason(
            confirmRes.message ?? undefined,
            confirmRes.status,
          ),
        });
      } else {
        track("file_upload_completed", {
          ...uploadProps,
          duration_ms: Date.now() - startedAt,
        });
      }
      setUploadedFiles([]);
      if (!projectId) {
        const params = new URLSearchParams(searchParams.toString());
        params.set("projectId", String(res.data.projectId));
        const path = pathname + "?" + params.toString();
        router.push(path);
      }
    } catch (err) {
      if (!failureTracked) {
        track("file_upload_failed", {
          ...uploadProps,
          stage,
          reason: "exception",
        });
      }
      if (err instanceof Error) {
        toast.add({ title: err.message, type: "error" });
      }
    } finally {
      setIsPending(false);
    }
  }

  if (isDemo) {
    return (
      <div className="flex h-full flex-col gap-6 p-6">
        <Alert>
          <Info />
          <AlertTitle>The demo is read-only</AlertTitle>
          <AlertDescription>
            You can look at these files and ask questions about them. Register
            to upload and manage your own files.
          </AlertDescription>
        </Alert>
        <div className="space-y-2 flex flex-wrap gap-2">
          {files.map((file) => (
            <FileCard key={file.id} file={file} isDemo />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex h-full flex-col gap-6 p-6"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {files.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-medium">Your files</h2>

          <div className="space-y-2 flex flex-wrap gap-2">
            {files.map((file) => (
              <FileCard key={file.id} file={file} />
            ))}
          </div>
        </div>
      )}
      {error && (
        <Alert className="mt-4">
          <FileWarningIcon />
          <AlertTitle>Sorry, something went wrong...</AlertTitle>
          <AlertDescription>
            Please refresh the page and try again
          </AlertDescription>
        </Alert>
      )}
      <div
        className={`
          flex min-h-64 flex-col items-center justify-center rounded-xl
          border-2 border-dashed p-8 text-center transition-colors
          ${
            isDragEnter
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25 hover:border-muted-foreground/50"
          }
        `}
      >
        <div
          className={`
            mb-4 flex size-12 items-center justify-center rounded-full
            ${isDragEnter ? "bg-primary/10 text-primary" : "bg-muted"}
          `}
        >
          <Upload className="size-5" />
        </div>

        {isDragEnter ? (
          <>
            <h3 className="font-medium">Drop your files here</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Release to add them to your upload
            </p>
          </>
        ) : (
          <>
            <h3 className="font-medium">Upload your files</h3>

            <p className="mt-1 text-sm text-muted-foreground">
              Drag and drop files here, or choose files from your computer
            </p>

            <Button
              variant="outline"
              className="mt-4"
              onClick={() => inputRef.current?.click()}
            >
              Choose files
            </Button>

            <p className="mt-3 text-xs text-muted-foreground">
              PDF, DOC, DOCX, CSV, TXT, MD files up to {MAX_FILE_SIZE_MB}MB
            </p>
          </>
        )}
      </div>

      <Input
        ref={inputRef}
        className="hidden"
        type="file"
        multiple
        onChange={handleFileSelect}
      />

      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium">Files to upload</h2>

            <span className="text-xs text-muted-foreground">
              {uploadedFiles.length}{" "}
              {uploadedFiles.length === 1 ? "file" : "files"}
            </span>
          </div>
          {Object.keys(errorMessages).length > 0 && (
            <div className="bg-destructive/10 text-destructive p-4 rounded border border-destructive/50">
              {Object.entries(errorMessages).map(([k, v], i) => (
                <p key={k}>
                  File {i + 1}: {v}
                </p>
              ))}
            </div>
          )}

          <div className="space-y-2 flex flex-wrap gap-4">
            {uploadedFiles.map((file, index) => {
              const extension =
                file.name.lastIndexOf(".") !== -1
                  ? file.name
                      .slice(file.name.lastIndexOf(".") + 1)
                      .toUpperCase()
                  : "";

              return (
                <Attachment className="h-20" key={`${file.name}-${index}`}>
                  <AttachmentMedia>{getFileIcon(file)}</AttachmentMedia>

                  <AttachmentContent className="min-w-0">
                    <AttachmentTitle className="truncate">
                      {file.name}
                    </AttachmentTitle>

                    <AttachmentDescription>
                      {extension && `${extension} · `}
                      {getSizeStr(file.size)}
                    </AttachmentDescription>
                  </AttachmentContent>

                  <Button
                    variant="ghost"
                    size="icon"
                    className="shrink-0"
                    onClick={() => removeFile(index)}
                    aria-label={`Remove ${file.name}`}
                  >
                    <X className="size-4" />
                  </Button>
                </Attachment>
              );
            })}
          </div>

          <Button
            className="w-full"
            onClick={handleUpload}
            disabled={isPending}
          >
            Upload {uploadedFiles.length}{" "}
            {uploadedFiles.length === 1 ? "file" : "files"}
          </Button>
        </div>
      )}
    </div>
  );
};

export default FilesTabs;
