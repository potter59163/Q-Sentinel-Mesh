export const HEMORRHAGE_LABELS: Record<string, string> = {
  any: "Any Hemorrhage",
  epidural: "Epidural",
  subdural: "Subdural",
  subarachnoid: "Subarachnoid",
  intraparenchymal: "Intraparenchymal",
  intraventricular: "Intraventricular",
  no_hemorrhage: "ไม่พบเลือดออก",
};

export function formatHemorrhageLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return HEMORRHAGE_LABELS[value] ?? value;
}
