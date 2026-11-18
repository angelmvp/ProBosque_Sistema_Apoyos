"use client";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ErrorApi } from "@/compartido/api";
import type { Sesion } from "@/compartido/tipos";

interface Valor {
  sesion: Sesion | null;
  cargando: boolean;
  ingresar: (correo: string, contrasena: string) => Promise<void>;
  salir: () => Promise<void>;
  tiene: (permiso: string) => boolean;
}

const Contexto = createContext<Valor | null>(null);

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [sesion, setSesion] = useState<Sesion | null>(null);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    try {
      setSesion(await api.obtener<Sesion>("/api/auth/yo"));
    } catch (e) {
      if (!(e instanceof ErrorApi) || e.estado !== 401) console.error(e);
      setSesion(null);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { void cargar(); }, [cargar]);

  const ingresar = async (correo: string, contrasena: string) => {
    setSesion(await api.enviarJson<Sesion>("/api/auth/ingresar", { correo, contrasena }));
  };
  const salir = async () => { await api.accion("/api/auth/salir"); setSesion(null); };
  const tiene = (permiso: string) => !!sesion?.permisos.includes(permiso);

  return <Contexto.Provider value={{ sesion, cargando, ingresar, salir, tiene }}>{children}</Contexto.Provider>;
}

export function useSesion(): Valor {
  const v = useContext(Contexto);
  if (!v) throw new Error("useSesion debe usarse dentro de <ProveedorSesion>.");
  return v;
}
