import { Message } from "../chat/types";
import { ProjectFile } from "../files/types";

export interface Project {
  id: number;
  name: string;
  files: ProjectFile[];
  messages: Message[];
}
