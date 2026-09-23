export interface Project {
  id: number;
  name: string;
  userId: number;
}

export interface Chat {
  id: number;
  content: string;
  role: string;
}

export interface File {
  id: number;
  name: string;
  url: string;
  thumbnail: string;
}
