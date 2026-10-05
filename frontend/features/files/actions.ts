import { UploadFileResponse } from "./types";
export async function sendFilesToS3(
  presignedFiles: UploadFileResponse["files"],
  files: File[],
) {
  return Promise.all(
    presignedFiles.map(async (file, i) => {
      try {
        const formData = new FormData();

        Object.entries(file.fields).forEach(([key, value]) => {
          formData.append(key, value);
        });

        formData.append("file", files[i]);

        const response = await fetch(file.url, {
          method: "POST",
          body: formData,
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
