"use client";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { useSesion } from "@/modulos/acceso/ContextoSesion";

/** HU-01: inicio de sesión. */
export default function PaginaIngresar() {
  const { ingresar } = useSesion();
  const router = useRouter();
  const [correo, setCorreo] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true); setError("");
    try { await ingresar(correo, contrasena); router.push("/inicio"); }
    catch (err) { setError((err as Error).message); }
    finally { setEnviando(false); }
  }

  return (
    <form className="tarjeta tarjeta-acceso formulario" onSubmit={enviar}>
      <h1>Ingresar</h1>
      {error && <div className="error" role="alert">{error}</div>}
      <label className="campo">Correo<input type="email" required value={correo} onChange={(e) => setCorreo(e.target.value)} autoComplete="username" /></label>
      <label className="campo">Contraseña<input type="password" required value={contrasena} onChange={(e) => setContrasena(e.target.value)} autoComplete="current-password" /></label>
      <button className="boton" disabled={enviando}>{enviando ? "Entrando…" : "Entrar"}</button>
      <p className="nota">La sesión se cierra tras 30 minutos sin actividad.</p>
    </form>
  );
}
