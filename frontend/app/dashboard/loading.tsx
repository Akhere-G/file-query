import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function DashboardPageLoading() {
  return (
    <div className="min-h-[90vh] flex">
      <div className="w-35 p-2">
        <Skeleton className="h-8 w-24 mb-4" />
        <div className="space-y-2 mt-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>

      <Tabs className="w-full flex-1">
        <TabsList className="w-full flex justify-start">
          <TabsTrigger className="max-w-30" value="files" disabled>
            Files
          </TabsTrigger>
          <TabsTrigger className="max-w-30" value="chat" disabled>
            Chat
          </TabsTrigger>
        </TabsList>
        <TabsContent value="chat">
          <div className="p-4 space-y-2">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-3/4" />
            <Skeleton className="h-16 w-5/6" />
          </div>
        </TabsContent>
        <TabsContent value="files">
          <div className="p-6 space-y-4">
            <Skeleton className="h-12 w-32" />
            <Skeleton className="h-64 w-full rounded-xl" />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
