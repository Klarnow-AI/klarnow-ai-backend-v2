"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { docs as docsApi } from "@/api_requests/docs";
import { Globe, Mail, MapPin, Phone, Users } from "@/components/icons";
import { listToTextarea, textareaToList } from "../_components/docs-utils";
import type { DocsCompanyData } from "@/types/api-types";

function CompanyField({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={htmlFor} className="text-sm font-medium text-foreground">
        {label}
      </Label>
      {children}
    </div>
  );
}

export default function DocsCompanyDataPage() {
  const params = useParams();
  const packId = params.packId as string;
  const [data, setData] = useState<DocsCompanyData | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    docsApi.getCompanyData(packId).then(setData);
  }, [packId]);

  const updateField = (key: keyof DocsCompanyData, value: unknown) => {
    setData((current) => (current ? { ...current, [key]: value } : current));
  };

  const completion = useMemo(() => {
    if (!data) return 0;
    const signatory = data.standard_signatory as Record<string, unknown> | null | undefined;
    const checks = [
      data.business_name,
      data.tagline,
      data.description,
      data.address,
      data.phone,
      data.email,
      data.website,
      Array.isArray(data.services) && data.services.length > 0,
      Array.isArray(data.packages) && data.packages.length > 0,
      signatory?.name,
      data.standard_footer,
    ];
    return checks.filter(Boolean).length;
  }, [data]);

  const save = async () => {
    if (!data) return;
    setSaving(true);
    setMessage(null);
    try {
      const next = await docsApi.updateCompanyData(packId, {
        business_name: data.business_name ?? "",
        tagline: data.tagline ?? "",
        description: data.description ?? "",
        address: data.address ?? "",
        phone: data.phone ?? "",
        email: data.email ?? "",
        website: data.website ?? "",
        services: data.services ?? [],
        team_members: data.team_members ?? [],
        packages: data.packages ?? [],
        standard_signatory: data.standard_signatory ?? {},
        standard_footer: data.standard_footer ?? "",
        logo_url: data.logo_url ?? "",
        logo_markup: data.logo_markup ?? "",
        brand_voice: data.brand_voice ?? "",
      });
      setData(next);
      setMessage("Company data saved.");
    } finally {
      setSaving(false);
    }
  };

  if (!data) {
    return (
      <div className="docs-page-body">
        <p className="text-sm text-muted-foreground">Loading company data…</p>
      </div>
    );
  }

  return (
    <div className="docs-page-body docs-page-body-wide">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <p className="docs-eyebrow">Reusable pack profile</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
            Company data
          </h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">
            Docs uses this record across proposals, invoices, company profiles,
            and formal letters. Fill it once so each new draft starts with
            consistent business context.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {message && <p className="text-sm text-muted-foreground">{message}</p>}
          <Button onClick={save} disabled={saving} className="docs-button">
            {saving ? "Saving..." : "Save company data"}
          </Button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <section className="docs-panel p-6">
            <div className="flex items-center gap-3">
              <Users className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-base font-medium text-foreground">
                  Business basics
                </p>
                <p className="text-sm text-muted-foreground">
                  Identity, positioning, and a reusable company description.
                </p>
              </div>
            </div>
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              <CompanyField label="Business name" htmlFor="business_name">
                <Input
                  id="business_name"
                  className="docs-input"
                  value={data.business_name ?? ""}
                  onChange={(event) => updateField("business_name", event.target.value)}
                />
              </CompanyField>
              <CompanyField label="Tagline" htmlFor="tagline">
                <Input
                  id="tagline"
                  className="docs-input"
                  value={data.tagline ?? ""}
                  onChange={(event) => updateField("tagline", event.target.value)}
                />
              </CompanyField>
            </div>
            <div className="mt-4">
              <CompanyField label="Description" htmlFor="description">
                <Textarea
                  id="description"
                  rows={5}
                  className="docs-textarea"
                  value={data.description ?? ""}
                  onChange={(event) => updateField("description", event.target.value)}
                />
              </CompanyField>
            </div>
          </section>

          <section className="docs-panel p-6">
            <div className="flex items-center gap-3">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-base font-medium text-foreground">
                  Contact and footer
                </p>
                <p className="text-sm text-muted-foreground">
                  Default contact points and the footer block used across exports.
                </p>
              </div>
            </div>
            <div className="mt-6 grid gap-4 lg:grid-cols-3">
              <CompanyField label="Phone" htmlFor="phone">
                <Input
                  id="phone"
                  className="docs-input"
                  value={data.phone ?? ""}
                  onChange={(event) => updateField("phone", event.target.value)}
                />
              </CompanyField>
              <CompanyField label="Email" htmlFor="email">
                <Input
                  id="email"
                  className="docs-input"
                  value={data.email ?? ""}
                  onChange={(event) => updateField("email", event.target.value)}
                />
              </CompanyField>
              <CompanyField label="Website" htmlFor="website">
                <Input
                  id="website"
                  className="docs-input"
                  value={data.website ?? ""}
                  onChange={(event) => updateField("website", event.target.value)}
                />
              </CompanyField>
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <CompanyField label="Address" htmlFor="address">
                <Textarea
                  id="address"
                  rows={4}
                  className="docs-textarea"
                  value={data.address ?? ""}
                  onChange={(event) => updateField("address", event.target.value)}
                />
              </CompanyField>
              <CompanyField label="Standard footer" htmlFor="standard_footer">
                <Textarea
                  id="standard_footer"
                  rows={4}
                  className="docs-textarea"
                  value={data.standard_footer ?? ""}
                  onChange={(event) => updateField("standard_footer", event.target.value)}
                />
              </CompanyField>
            </div>
          </section>

          <section className="docs-panel p-6">
            <div className="flex items-center gap-3">
              <Phone className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-base font-medium text-foreground">
                  Offerings and team
                </p>
                <p className="text-sm text-muted-foreground">
                  Reusable services, packages, and team references for proposals and profiles.
                </p>
              </div>
            </div>
            <div className="mt-6 grid gap-4 lg:grid-cols-3">
              <CompanyField label="Services" htmlFor="services">
                <Textarea
                  id="services"
                  rows={6}
                  className="docs-textarea"
                  value={listToTextarea(data.services as unknown[] | null | undefined)}
                  onChange={(event) =>
                    updateField("services", textareaToList(event.target.value))
                  }
                />
              </CompanyField>
              <CompanyField label="Team members" htmlFor="team_members">
                <Textarea
                  id="team_members"
                  rows={6}
                  className="docs-textarea"
                  value={listToTextarea(data.team_members as unknown[] | null | undefined)}
                  onChange={(event) =>
                    updateField("team_members", textareaToList(event.target.value))
                  }
                />
              </CompanyField>
              <CompanyField label="Packages and prices" htmlFor="packages">
                <Textarea
                  id="packages"
                  rows={6}
                  className="docs-textarea"
                  value={listToTextarea(data.packages as unknown[] | null | undefined)}
                  onChange={(event) =>
                    updateField("packages", textareaToList(event.target.value))
                  }
                />
              </CompanyField>
            </div>
          </section>

          <section className="docs-panel p-6">
            <div className="flex items-center gap-3">
              <Globe className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-base font-medium text-foreground">
                  Brand and signatory
                </p>
                <p className="text-sm text-muted-foreground">
                  Voice, logo references, and default sign-off for formal docs.
                </p>
              </div>
            </div>
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              <CompanyField label="Logo URL" htmlFor="logo_url">
                <Input
                  id="logo_url"
                  className="docs-input"
                  value={data.logo_url ?? ""}
                  onChange={(event) => updateField("logo_url", event.target.value)}
                />
              </CompanyField>
              <CompanyField label="Brand voice" htmlFor="brand_voice">
                <Input
                  id="brand_voice"
                  className="docs-input"
                  value={data.brand_voice ?? ""}
                  onChange={(event) => updateField("brand_voice", event.target.value)}
                />
              </CompanyField>
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <CompanyField label="Signatory name" htmlFor="signatory_name">
                <Input
                  id="signatory_name"
                  className="docs-input"
                  value={String((data.standard_signatory?.name as string | undefined) ?? "")}
                  onChange={(event) =>
                    updateField("standard_signatory", {
                      ...(data.standard_signatory ?? {}),
                      name: event.target.value,
                      title: (data.standard_signatory?.title as string | undefined) ?? "",
                    })
                  }
                />
              </CompanyField>
              <CompanyField label="Signatory title" htmlFor="signatory_title">
                <Input
                  id="signatory_title"
                  className="docs-input"
                  value={String((data.standard_signatory?.title as string | undefined) ?? "")}
                  onChange={(event) =>
                    updateField("standard_signatory", {
                      ...(data.standard_signatory ?? {}),
                      title: event.target.value,
                      name: (data.standard_signatory?.name as string | undefined) ?? "",
                    })
                  }
                />
              </CompanyField>
            </div>
          </section>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
          <div className="docs-panel-muted p-5">
            <p className="docs-eyebrow">Readiness</p>
            <p className="mt-2 text-3xl font-semibold text-foreground">
              {completion}/11
            </p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Core company fields completed for reuse across Docs.
            </p>
          </div>

          <div className="docs-panel p-5">
            <div className="flex items-start gap-3">
              <MapPin className="mt-0.5 h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  What uses this
                </p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  Proposals, invoices, company profiles, employment letters, and sponsorship letters all pull from this profile.
                </p>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
