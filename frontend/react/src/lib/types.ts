export interface User {
  id: number;
  username: string;
  email: string | null;
  role: "admin" | "teacher" | "student";
  is_active: number;
  created_at: string;
}
export interface Classroom {
  id: number;
  name: string;
  description: string | null;
  computer_count: number;
  created_at: string;
}
export interface Computer {
  id: number;
  name: string;
  host_address: string;
}
export interface Session {
  user: Pick<User, "id" | "username" | "email" | "role"> | null;
  google?: boolean;
  classroom_id?: number | null;
  csrf: string;
}
export type Notify = (message: string, kind?: "success" | "error") => void;
