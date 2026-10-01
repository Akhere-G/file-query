import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ChatTab from "@/features/files/components/ChatTab";
import FilesTab from "@/features/files/components/FilesTabs";
import ProjectSidebar from "@/features/files/components/ProjectSidebar";
import { getProject, getProjects } from "@/features/project/server-actions";
import { Project } from "@/features/project/types";
import { redirect } from "next/navigation";
import { Toaster } from "@/components/ui/toast";
// TODO: fetch projects from backend
// TODO: fetch current project if searchParam has projectId
// TODO: redirect if no project with that id is found
// TODO: display all projects and highlight current project
// TODO: display files for project

interface DashboardPageProps {
  searchParams: Promise<{ projectId?: string }>;
}
export default async function DashboardPage({
  searchParams,
}: DashboardPageProps) {
  const projectId = (await searchParams).projectId;

  const res = await getProjects();

  const projects = res.success ? res.data : [];
  let project: Project | null = null;

  if (projectId) {
    const projectRes = await getProject(Number(projectId));
    project = projectRes.data;

    if ([404, 403].includes(projectRes.status)) {
      redirect("/dashboard", "replace");
    }
  }

  return (
    <div className="min-h-[90vh] flex">
      <ProjectSidebar
        projects={projects}
        currentProjectId={Number(projectId ?? 0)}
      />
      <Tabs className="w-full flex-1">
        <TabsList className="bg-primary-foreground w-full flex justify-start">
          <TabsTrigger className="max-w-30" value="chat">
            Chat
          </TabsTrigger>
          <TabsTrigger className="max-w-30" value="files">
            Files
          </TabsTrigger>
        </TabsList>
        <TabsContent value="chat">
          <ChatTab />
        </TabsContent>
        <TabsContent value="files">
          <FilesTab files={project?.files ?? []} />
        </TabsContent>
        <Toaster />
      </Tabs>
    </div>
  );
}
