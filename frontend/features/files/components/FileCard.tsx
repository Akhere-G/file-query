"use client";
import {
  Attachment,
  AttachmentActions,
  AttachmentContent,
  AttachmentDescription,
  AttachmentMedia,
  AttachmentTitle,
} from "@/components/ui/attachment";
import { ProjectFile } from "../types";
import { FileIcon, Loader2, MoreVertical } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useState } from "react";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { deleteFile, viewFileContent } from "../server-actions";
import { toast } from "@/components/ui/toast";
import { track } from "@/lib/analytics/client";
import { fileTypeLabel } from "@/lib/analytics/events";

type ModalState = "delete" | null;

export default function FileCard({ file }: { file: ProjectFile }) {
  const [modalState, setModalState] = useState<ModalState>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const deleteFileAction = async () => {
    if (file.status === "pending") {
      toast.add({
        title: "This file is still being uploading. Please wait.",
        type: "info",
      });
      return;
    }
    setIsDeleting(true);
    try {
      const res = await deleteFile(file.id);
      if (res.success) {
        track("file_deleted", {
          file_type: fileTypeLabel(file.mimeType),
          file_status: file.status,
        });
        toast.add({ title: "Deleted file" });
        setModalState(null);
      } else {
        toast.add({ title: "Could not delete file", type: "error" });
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const viewFileAction = async () => {
    if (file.status === "error") {
      toast.add({
        title:
          "There was a problem with uploading this file. Please delete and reupload.",
        type: "error",
      });
      return;
    }

    if (file.status === "pending") {
      toast.add({
        title: "This file is still being uploading. Please wait.",
        type: "info",
      });
      return;
    }
    const res = await viewFileContent(file.id);
    if (res.success) {
      track("file_viewed", {
        file_type: fileTypeLabel(file.mimeType),
        file_status: file.status,
      });
      window.open(res.data.url, "_blank", "noopener,noreferrer");
    } else {
      toast.add({ title: "Could not view file", type: "error" });
    }
  };
  const fileIsLoading = ["processing", "pending"].includes(file.status);
  return (
    <>
      <Attachment
        key={file.id}
        className={`h-16 ${
          file.status === "error"
            ? "border-red-500 bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-100"
            : undefined
        }`}
      >
        <AttachmentMedia>
          {fileIsLoading ? (
            <Loader2 className="animate-spin" />
          ) : (
            <FileIcon className="size-5" />
          )}
        </AttachmentMedia>

        <AttachmentContent>
          <AttachmentTitle className="truncate">{file.name}</AttachmentTitle>
          <AttachmentDescription
            className={file.error ? "text-slate-700 dark:text-slate-300" : ""}
          >
            {file.error
              ? "There was a problem with uploading this file. Please delete and reupload."
              : ""}
          </AttachmentDescription>
        </AttachmentContent>
        <AttachmentActions>
          <DropdownMenu>
            <DropdownMenuTrigger>
              <MoreVertical size={16} />
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuGroup>
                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                <DropdownMenuItem onClick={() => setModalState("delete")}>
                  Delete
                </DropdownMenuItem>
                <DropdownMenuItem onClick={viewFileAction}>
                  View
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </AttachmentActions>
      </Attachment>

      <Dialog
        open={modalState === "delete"}
        onOpenChange={(isOpen) => setModalState(isOpen ? "delete" : null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete File</DialogTitle>
            <DialogDescription>
              Do you want to delete this file?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex gap-4">
            <DialogClose>Cancel</DialogClose>
            <Button onClick={deleteFileAction} disabled={isDeleting}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
