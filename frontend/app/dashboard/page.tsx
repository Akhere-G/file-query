import { TabsList, TabsTrigger } from "@/components/ui/tabs";
import TrackedTabs from "@/components/common/TrackedTabs";
import ProjectSidebar from "@/features/files/components/ProjectSidebar";
import { getProject, getProjects } from "@/features/project/server-actions";
import { redirect } from "next/navigation";
import { Toaster } from "@/components/ui/toast";
import ProjectTabs from "@/features/files/components/ProjectTabs";
import { isDemoSession } from "@/components/common/DemoBanner";

interface DashboardPageProps {
  searchParams: Promise<{ projectId?: string }>;
}
export default async function DashboardPage({
  searchParams,
}: DashboardPageProps) {
  const params = await searchParams;
  const projectId = params.projectId ? Number(params.projectId) : null;

  const [isDemo, res, projectRes] = await Promise.all([
    isDemoSession(),
    getProjects(),
    projectId ? getProject(projectId) : Promise.resolve(null),
  ]);

  const projects = res.success ? res.data : [];

  if (projectRes && [404, 403].includes(projectRes.status)) {
    redirect("/dashboard", "replace");
  }

  return (
    <div className="min-h-[90vh] flex">
      <ProjectSidebar
        projects={projects}
        currentProjectId={projectId}
        isDemo={isDemo}
      />
      <TrackedTabs className="w-full flex-1">
        <TabsList className="w-full flex justify-start">
          <TabsTrigger className="max-w-30" value="files">
            Files
          </TabsTrigger>
          <TabsTrigger className="max-w-30" value="chat">
            Chat
          </TabsTrigger>
        </TabsList>
        <ProjectTabs projectId={projectId} isDemo={isDemo} />
        <Toaster />
      </TrackedTabs>
    </div>
  );
}
