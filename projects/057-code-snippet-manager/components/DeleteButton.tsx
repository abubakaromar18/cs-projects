"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function DeleteButton({ id }: { id: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  async function remove() {
    if (!confirm("Delete this snippet?")) return;
    setBusy(true);
    const res = await fetch(`/api/snippets/${id}`, { method: "DELETE" });
    if (res.ok) {
      router.push("/");
      router.refresh();
    } else {
      setBusy(false);
      alert("Could not delete the snippet.");
    }
  }
  return (
    <button type="button" className="btn small danger" onClick={remove} disabled={busy}>
      Delete
    </button>
  );
}
