import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ChatTab from "@/features/files/components/ChatTab";
import FilesTab from "@/features/files/components/FilesTabs";
import ProjectSidebar from "@/features/files/components/ProjectSidebar";
import { getProject, getProjects } from "@/features/project/server-actions";
import { Project } from "@/features/project/types";
import { redirect } from "next/navigation";
import { Toaster } from "@/components/ui/toast";

interface DashboardPageProps {
  searchParams: Promise<{ projectId?: string }>;
}
export default async function DashboardPage({
  searchParams,
}: DashboardPageProps) {
  const params = await searchParams;
  const projectId = params.projectId ? Number(params.projectId) : null;

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
      <ProjectSidebar projects={projects} currentProjectId={projectId} />
      <Tabs className="w-full flex-1">
        <TabsList className="bg-primary-foreground w-full flex justify-start">
          <TabsTrigger className="max-w-30" value="files">
            Files
          </TabsTrigger>
          <TabsTrigger className="max-w-30" value="chat">
            Chat
          </TabsTrigger>
        </TabsList>
        <TabsContent value="chat">
          <ChatTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="files">
          <FilesTab files={project?.files ?? []} />
        </TabsContent>
        <Toaster />
      </Tabs>
    </div>
  );
}
