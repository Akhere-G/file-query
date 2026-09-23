"use client";

import { Input } from "@/components/ui/input";
import { File as FileType } from "../types";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Attachment,
  AttachmentContent,
  AttachmentDescription,
  AttachmentMedia,
  AttachmentTitle,
} from "@/components/ui/attachment";
import { Upload, X, File as FileIcon } from "lucide-react";
import { getFileIcon, getSizeStr } from "../utils";

const files: FileType[] = [];

const FilesTabs = () => {
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

  const addFiles = (newFiles: File[]) => {
    setUploadedFiles((current) => [...current, ...newFiles]);
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

          <div className="space-y-2">
            {files.map((file) => (
              <Attachment key={file.id}>
                <AttachmentMedia>
                  <FileIcon className="size-5" />
                </AttachmentMedia>

                <AttachmentContent>
                  <AttachmentTitle className="truncate">
                    {file.name}
                  </AttachmentTitle>
                </AttachmentContent>
              </Attachment>
            ))}
          </div>
        </div>
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
              PDF, DOCX, TXT, PNG, JPG up to 10MB
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

          <div className="space-y-2">
            {uploadedFiles.map((file, index) => {
              const extension =
                file.name.lastIndexOf(".") !== -1
                  ? file.name
                      .slice(file.name.lastIndexOf(".") + 1)
                      .toUpperCase()
                  : "";

              return (
                <Attachment key={`${file.name}-${index}`}>
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

          <Button className="w-full">
            Upload {uploadedFiles.length}{" "}
            {uploadedFiles.length === 1 ? "file" : "files"}
          </Button>
        </div>
      )}
    </div>
  );
};

export default FilesTabs;
