"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Ellipsis } from "lucide-react";
import { Project } from "@/features/project/types";
import {
  renameProject,
  deleteProject,
} from "@/features/project/server-actions";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const ProjectSidebar = ({
  projects,
  currentProjectId,
}: {
  projects: Project[];
  currentProjectId: number | null;
}) => {
  const router = useRouter();
  const noProjects = !projects || projects.length == 0;

  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [newName, setNewName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRenameOpen = (project: Project) => {
    setSelectedProject(project);
    setNewName(project.name);
    setError(null);
    setRenameDialogOpen(true);
  };

  const handleDeleteOpen = (project: Project) => {
    setSelectedProject(project);
    setError(null);
    setDeleteDialogOpen(true);
  };

  const handleRename = async () => {
    if (!selectedProject || !newName.trim()) return;
    setIsLoading(true);
    setError(null);
    const res = await renameProject(selectedProject.id, newName.trim());
    setIsLoading(false);
    if (res.success) {
      setRenameDialogOpen(false);
      router.refresh();
    } else {
      setError(res.message || "Failed to rename project");
    }
  };

  const handleDelete = async () => {
    if (!selectedProject) return;
    setIsLoading(true);
    setError(null);
    const res = await deleteProject(selectedProject.id);
    setIsLoading(false);
    if (res.success) {
      setDeleteDialogOpen(false);
      router.push("/dashboard");
    } else {
      setError(res.message || "Failed to delete project");
    }
  };

  return (
    <div className="w-35 p-2 inset-shadow-sm">
      <h2 className="title text-xl">Projects</h2>
      {noProjects && (
        <div className="text-sm py-12">
          <h3>No projects yet</h3>
        </div>
      )}
      {!noProjects && (
        <div className="max-w-[30vw] truncate overflow-x-clip mt-4 text-sm flex flex-col">
          {projects.map((project) => (
            <div
              key={project.id}
              className={`flex items-center group rounded-md ${project.id === currentProjectId ? "bg-secondary" : ""}`}
            >
              <Link
                className="px-2 py-1 flex-1 truncate text-ellipsis hover:pointer"
                href={`/dashboard?projectId=${project.id}`}
              >
                {project.name}
              </Link>
              <DropdownMenu>
                <DropdownMenuTrigger className="h-6 w-6 opacity-0 group-hover:opacity-100 shrink-0 inline-flex items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer">
                  <Ellipsis className="h-4 w-4" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => handleRenameOpen(project)}>
                    Rename
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="text-destructive"
                    onClick={() => handleDeleteOpen(project)}
                  >
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          ))}
        </div>
      )}
      {currentProjectId && (
        <Link className="text-sm pl-1 pt-4 block" href="/dashboard">
          Start new project
        </Link>
      )}

      <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Project</DialogTitle>
            <DialogDescription>
              Enter a new name for this project.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="project-name">Name</Label>
            <Input
              id="project-name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleRename();
              }}
              placeholder="Project name"
              className="mt-2"
            />
            {error && <p className="text-sm text-destructive mt-2">{error}</p>}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRenameDialogOpen(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleRename}
              disabled={isLoading || !newName.trim()}
            >
              {isLoading ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Project</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{selectedProject?.name}
              &rdquo;? This will permanently delete the project and all its
              files. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isLoading}
            >
              {isLoading ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProjectSidebar;
