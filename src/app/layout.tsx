import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const cuerpo = Inter({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--f-body", display: "swap" });
const titulos = Space_Grotesk({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--f-display", display: "swap" });

const descripcion = "Datos oficiales de la educación en las 17 comunidades autónomas (y Ceuta y Melilla aparte): cada cifra con su fuente, su año y su fiabilidad.";

export const metadata: Metadata = {
  metadataBase: new URL("https://educacion-ccaa.vercel.app"),
  title: "Educación por comunidades",
  description: descripcion,
  // Pendiente: public/og.png (1200x630) con una captura cuando el diseño esté cerrado.
  openGraph: { title: "¿Cómo está la educación en tu comunidad?", description: descripcion, url: "/", siteName: "Educación por comunidades", locale: "es_ES", type: "website" },
  twitter: { card: "summary", title: "¿Cómo está la educación en tu comunidad?", description: descripcion },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" className={`${cuerpo.variable} ${titulos.variable}`}>
      <body>
        {children}
        {/* Recuento anónimo de visitas, sin cookies. Hay que activarlo en Vercel: proyecto > Analytics > Enable. */}
        <Analytics />
      </body>
    </html>
  );
}
