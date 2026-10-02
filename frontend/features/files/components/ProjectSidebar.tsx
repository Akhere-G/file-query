"use client";

import { Project } from "@/features/project/types";
import Link from "next/link";

const ProjectSidebar = ({
  projects,
  currentProjectId,
}: {
  projects: Project[];
  currentProjectId: number | null;
}) => {
  const noProjects = !projects || projects.length == 0;
  return (
    <div className="min-w-30  p-2 inset-shadow-sm">
      <h2 className="title text-xl">Projects</h2>
      {noProjects && (
        <div className="text-sm py-12">
          <h3>No projects yet</h3>
        </div>
      )}
      {!noProjects && (
        <div className="max-w-[30vw] truncate overflow-x-clip mt-4 text-sm ">
          {projects.map((project) => (
            <Link
              className={`px-2 py-1 w-full truncate text-ellipsis  rounded-md hover:pointer ${project.id === currentProjectId ? "bg-secondary" : ""}`}
              key={project.id}
              href={`/dashboard?projectId=${project.id}`}
            >
              {project.name}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProjectSidebar;
