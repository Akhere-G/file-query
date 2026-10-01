"use client";
import {
  Attachment,
  AttachmentActions,
  AttachmentContent,
  AttachmentMedia,
  AttachmentTitle,
} from "@/components/ui/attachment";
import { ProjectFile } from "../types";
import { FileIcon, MoreVertical } from "lucide-react";
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
import { deleteFile } from "../server-actions";
import { toast } from "@/components/ui/toast";

type ModalState = "view" | "delete" | null;

export default function FileCard({ file }: { file: ProjectFile }) {
  const [modalState, setModalState] = useState<ModalState>(null);
  const [isDeleting, setIsDeleting] = useState();
  const deleteFileAction = async () => {
    const res = await deleteFile(file.id);
    if (res.success) {
      toast.add({ title: "Deleted file" });
    } else {
      toast.add({ title: "Could not delete file", type: "error" });
    }
  };
  return (
    <>
      <Attachment key={file.id}>
        <AttachmentMedia>
          <FileIcon className="size-5" />
        </AttachmentMedia>

        <AttachmentContent>
          <AttachmentTitle className="truncate">{file.name}</AttachmentTitle>
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
                <DropdownMenuItem onClick={() => setModalState("view")}>
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
            <Button>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
