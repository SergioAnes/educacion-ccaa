"use client";

import { useEffect } from "react";
import type { DatosApp } from "@/lib/app/datos-app";
import { ESQUELETO } from "@/lib/app/esqueleto";
import { iniciar } from "@/lib/app/ui";

/** Página única: Datos, Tu comunidad y Cómo leer los datos, navegables por #hash. */
export function App({ datos }: { datos: DatosApp }) {
  useEffect(() => {
    iniciar(datos);
  }, [datos]);
  return <div dangerouslySetInnerHTML={{ __html: ESQUELETO }} />;
}
