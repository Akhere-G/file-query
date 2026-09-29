import { UploadFileResponse } from "./types";
export async function sendFilesToS3(
  presignedFiles: UploadFileResponse["files"],
  files: File[],
) {
  return Promise.all(
    presignedFiles.map(async (file, i) => {
      try {
        const response = await fetch(file.url, {
          method: "PUT",
          body: files[i],
          headers: {
            "Content-Type": files[i].type,
          },
        });

        return {
          id: file.id,
          error: !response.ok ? "Could not upload" : undefined,
        };
      } catch (error) {
        return {
          id: file.id,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }),
  );
}
