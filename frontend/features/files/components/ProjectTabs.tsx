"use client";
import { TabsContent } from "@/components/ui/tabs";
import ChatTab from "./ChatTab";
import FilesTabs from "./FilesTabs";
import useGetFiles from "../useGetFiles";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { InfoIcon } from "lucide-react";

export default function ProjectTabs({
  projectId,
}: {
  projectId: number | null;
}) {
  const { files, isLoading, error } = useGetFiles(Number(projectId));

  const someFilesProcessing =
    files.length > 0 &&
    files.some(
      (file) => file.status === "processing" || file.status === "pending",
    );
  const allFileProcessing =
    files.length > 0 &&
    files.every(
      (file) => file.status === "processing" || file.status === "pending",
    );

  const alertText = someFilesProcessing
    ? "Some files are still processing."
    : "";

  return (
    <>
      {someFilesProcessing && (
        <div className="px-5 pt-4">
          <Alert>
            <InfoIcon />
            <AlertTitle className="text-white">{alertText}</AlertTitle>
            <AlertDescription>
              The AI cannot search through files being processed.
            </AlertDescription>
          </Alert>
        </div>
      )}

      <TabsContent value="chat" key={projectId}>
        <ChatTab
          projectId={projectId}
          files={files}
          isLoading={isLoading}
          error={error}
          allFilesProcessing={allFileProcessing}
        />
      </TabsContent>
      <TabsContent value="files">
        <FilesTabs files={files} isLoading={isLoading} error={error} />
      </TabsContent>
    </>
  );
}
