export function fechaCorta(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export const ETIQUETA_ESTADO: Record<string, string> = {
  vigente: "Convocatoria abierta",
  historica: "Convocatoria concluida",
  sin_convocatoria: "Sin convocatoria abierta",
  borrador: "Borrador",
  programada: "Programada",
};
