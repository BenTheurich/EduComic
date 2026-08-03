import { isDemoMode } from "@/lib/runtime";

export function DemoBanner() {
  if (!isDemoMode) return null;

  return (
    <div
      className="border-b bg-primary px-4 py-2 text-center text-xs font-semibold text-primary-foreground"
      role="status"
    >
      Public demo · Fictional data · Read-only
    </div>
  );
}
