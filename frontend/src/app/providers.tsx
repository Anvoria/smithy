import { AuthProvider } from "@/contexts/AuthContext";

export default function GlobalProviders({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <AuthProvider>{children}</AuthProvider>;
}