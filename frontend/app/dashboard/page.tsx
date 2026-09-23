import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ChatTab from "@/features/files/components/ChatTab.tsx";
import FilesTab from "@/features/files/components/FilesTabs.tsx";
import ProjectSidebar from "@/features/files/components/ProjectSidebar.tsx";
export default function DashboardPage() {
  return (
    <div className="min-h-[90vh] flex">
      <ProjectSidebar />
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
          <FilesTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
