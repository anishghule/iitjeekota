/**
 * The enquiry form. Until the API exists (Phase 8), it sends on WhatsApp: it checks the fields and
 * opens WhatsApp with the message ready, addressed to D-SAP. The site stores nothing.
 * The form carries its own message template, link pattern and error texts.
 */
import { fill } from "../lib/format.ts";

export interface EnquiryFields {
  name: string;
  class: string;
  area: string;
  phone: string;
  consent: boolean;
}

export type FieldError = "required" | "badPhone" | "needConsent";

/** A 10-digit Indian mobile number, with an optional +91 or 0 in front and spaces or hyphens. */
export function normalisePhone(raw: string): string | null {
  const digits = raw.replace(/[\s-]/g, "").replace(/^(\+91|0091|0)/, "");
  return /^[6-9]\d{9}$/.test(digits) ? digits : null;
}

export function validate(f: EnquiryFields): Partial<Record<keyof EnquiryFields, FieldError>> {
  const errors: Partial<Record<keyof EnquiryFields, FieldError>> = {};
  for (const key of ["name", "class", "area"] as const) if (!f[key].trim()) errors[key] = "required";
  if (!f.phone.trim()) errors.phone = "required";
  else if (!normalisePhone(f.phone)) errors.phone = "badPhone";
  if (!f.consent) errors.consent = "needConsent";
  return errors;
}

export function whatsappLink(pattern: string, digits: string, message: string): string {
  return fill(pattern, { digits, text: encodeURIComponent(message) });
}

export function initEnquiry(form: HTMLFormElement, win: Window): void {
  const field = (name: string) => form.elements.namedItem(name) as HTMLInputElement | HTMLSelectElement | null;
  const read = (): EnquiryFields => ({
    name: field("name")?.value ?? "",
    class: field("class")?.value ?? "",
    area: field("area")?.value ?? "",
    phone: field("phone")?.value ?? "",
    consent: (field("consent") as HTMLInputElement | null)?.checked ?? false,
  });
  form.noValidate = true;
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const values = read();
    const errors = validate(values);
    let first: HTMLElement | null = null;
    for (const key of ["name", "class", "area", "phone", "consent"] as const) {
      const input = field(key);
      const note = form.querySelector<HTMLElement>(`[data-error="${key}"]`);
      const error = errors[key];
      input?.setAttribute("aria-invalid", String(Boolean(error)));
      if (note) note.textContent = error ? (form.dataset[error] ?? "") : "";
      if (error && !first) first = input;
    }
    if (first) {
      first.focus();
      return;
    }
    const message = fill(form.dataset.message ?? "", {
      name: values.name.trim(),
      class: values.class,
      area: values.area,
      phone: normalisePhone(values.phone) ?? values.phone,
    });
    win.open(whatsappLink(form.dataset.link ?? "", form.dataset.digits ?? "", message), "_blank", "noopener");
  });
}
