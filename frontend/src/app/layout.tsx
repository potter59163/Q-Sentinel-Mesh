import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";

export const metadata: Metadata = {
  title: "Q-Sentinel Mesh",
  description: "แพลตฟอร์ม AI สำหรับวิเคราะห์ CT เลือดออกในสมอง พร้อม Federated Learning และระบบความปลอดภัย",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="th" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        {children}
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
