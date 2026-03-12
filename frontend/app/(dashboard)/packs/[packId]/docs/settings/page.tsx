import { Download, FileText, Layers } from "@/components/icons";

const SETTING_ROWS = [
  {
    title: "Tone defaults",
    body: "Tone is chosen when a document is created and can be changed later inside the workspace overview.",
    icon: FileText,
  },
  {
    title: "Exports",
    body: "PDF remains the default output across all document types in v0.1.",
    icon: Download,
  },
  {
    title: "Template scope",
    body: "Blueprints are fixed in code for now. Custom templates, DOCX export, and collaboration stay in later phases.",
    icon: Layers,
  },
];

export default function DocsSettingsPage() {
  return (
    <div className="docs-page-body docs-page-body-narrow">
      <div className="max-w-3xl">
        <p className="docs-eyebrow">Settings</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
          Docs defaults
        </h1>
        <p className="mt-3 text-sm leading-7 text-muted-foreground">
          v0.1 keeps Docs settings intentionally narrow and pack-scoped. The
          workflow stays opinionated so the structure remains consistent.
        </p>
      </div>

      <div className="docs-panel overflow-hidden">
        {SETTING_ROWS.map((row, index) => {
          const Icon = row.icon;
          return (
            <div
              key={row.title}
              className={index < SETTING_ROWS.length - 1 ? "border-b border-border/50" : ""}
            >
              <div className="flex items-start gap-3 px-5 py-5">
                <Icon className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {row.title}
                  </p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">
                    {row.body}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
