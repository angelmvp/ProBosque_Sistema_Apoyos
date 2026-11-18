import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Encabezado } from "@/compartido/Encabezado";
import { ProveedorSesion } from "@/modulos/acceso/ContextoSesion";
import "./globals.css";

export const metadata: Metadata = {
  title: "PROBOSQUE · Apoyos forestales",
  description: "Consulta de convocatorias de los programas de apoyo forestal de PROBOSQUE (Estado de México).",
};

export default function DisposicionRaiz({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <ProveedorSesion>
          <Encabezado />
          <main className="contenido">{children}</main>
          <footer className="pie">Proyecto universitario · Sprint 1 · Datos de ejemplo, sin validez oficial.</footer>
        </ProveedorSesion>
      </body>
    </html>
  );
}
