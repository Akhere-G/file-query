"use client";

import Link from "next/link";
import { Project } from "../types";

const projects: Project[] = [];
const ProjectSidebar = () => {
  const noProjects = !projects || projects.length == 0;
  return (
    <div className="min-w-30 p-4 inset-shadow-sm">
      <h2 className="title text-xl">Files</h2>
      {noProjects && (
        <div className="text-sm py-12">
          <h3>No projects yet</h3>
        </div>
      )}
      {!noProjects && (
        <div>
          {projects.map((project) => (
            <Link key={project.id} href={`/projects?id=${project.id}`}>
              {project.name}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProjectSidebar;
