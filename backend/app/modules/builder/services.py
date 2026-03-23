"""Builder project services. CRUD scoped to user via pack ownership."""

import json
import re
from datetime import datetime, timezone
from html import escape
from urllib.parse import quote
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.core.storage import delete_file, download_file, storage_enabled, upload_file
from app.modules.builder.models import BuilderProject
from app.shared.generation_schemas import GenerationBrandContext

# Subdomains that must not be used (reserved or ambiguous)
_RESERVED_SUBDOMAINS = frozenset({"www", "api", "app", "admin", "mail", "ftp", "staging"})
_SUBDOMAIN_MAX_LEN = 63
_PUBLIC_HTML_CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=600"
_PUBLIC_META_CACHE_CONTROL = "public, max-age=60"
_PRIVATE_SNAPSHOT_CACHE_CONTROL = "private, max-age=0, no-cache"


# ---------------------------------------------------------------------------
# HTML builder — converts stored files into a self-contained deployable page
# ---------------------------------------------------------------------------

_IMPORT_RE = re.compile(r"import\s+[\s\S]*?from\s+['\"].*?['\"]\s*;?\n?")


def _strip_exports(code: str, fallback_name: str | None = None) -> str:
    code = _IMPORT_RE.sub("", code)
    code = re.sub(r"export\s+default\s+function\s+", "function ", code)
    code = re.sub(r"export\s+default\s+class\s+", "class ", code)
    repl = f"const {fallback_name} = " if fallback_name else "const _default = "
    code = re.sub(r"export\s+default\s+", repl, code)
    code = re.sub(r"export\s+function\s+", "function ", code)
    code = re.sub(r"export\s+class\s+", "class ", code)
    code = re.sub(r"export\s+const\s+", "const ", code)
    code = re.sub(r"export\s+let\s+", "let ", code)
    code = re.sub(r"export\s+var\s+", "var ", code)
    return code


def _inject_head_tag(header: str, tag: str) -> str:
    return header.replace("</head>", f"{tag}\n</head>", 1)


def _svg_to_data_uri(svg_markup: str) -> str:
    return "data:image/svg+xml;charset=utf-8," + quote(
        svg_markup,
        safe="/:;,+-_=?.!~*'()#[]@&$",
    )


def build_site_shell_meta(
    brand_context: GenerationBrandContext | None,
    *,
    fallback_title: str,
) -> dict[str, str]:
    title = (brand_context.brand_name if brand_context else None) or fallback_title or "Website"
    favicon_href = ""
    if brand_context:
        if brand_context.logo_markup:
            favicon_href = _svg_to_data_uri(brand_context.logo_markup.strip())
        elif brand_context.logo_url:
            favicon_href = brand_context.logo_url.strip()
    theme_color = ""
    if brand_context and brand_context.color_palette and brand_context.color_palette.primary:
        theme_color = brand_context.color_palette.primary.strip()
    return {
        "site_title": title,
        "favicon_href": favicon_href,
        "theme_color": theme_color,
    }


_DEPLOY_HEADER = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html, body, #root { height: 100%; }
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel" data-presets="react">
    class _EB extends React.Component {
      constructor(p) { super(p); this.state = { error: null }; }
      static getDerivedStateFromError(e) { return { error: e.message }; }
      render() {
        if (this.state.error) return (
          <div style={{padding:"24px",fontFamily:"ui-monospace,monospace",fontSize:"13px",background:"#fef2f2",minHeight:"100vh"}}>
            <strong style={{color:"#dc2626"}}>Error</strong>
            <pre style={{marginTop:"8px",whiteSpace:"pre-wrap",color:"#374151"}}>{this.state.error}</pre>
          </div>
        );
        return this.props.children;
      }
    }
"""

_DEPLOY_FOOTER = """\

    const _App = typeof App !== "undefined" ? App : () => React.createElement("div", null, "No App component found");
    ReactDOM.createRoot(document.getElementById("root")).render(
      React.createElement(_EB, null, React.createElement(_App))
    );
  </script>
</body>
</html>"""


def build_deploy_html(
    files: dict,
    project_id: str | None = None,
    lead_url: str | None = None,
    site_title: str | None = None,
    favicon_href: str | None = None,
    theme_color: str | None = None,
) -> str:
    """Build a self-contained HTML page from a dict of project files.
    If lead_url is set (e.g. /lead for subdomain), use it; else use /p/{project_id}/lead when project_id is set.
    """
    app_code = files.get("/App.tsx") or files.get("App.tsx") or ""

    bundle = ""
    for path, code in files.items():
        if path in ("/App.tsx", "App.tsx"):
            continue
        name = path.split("/")[-1]
        name = re.sub(r"\.(tsx|jsx)$", "", name)
        if not name:
            continue
        bundle += _strip_exports(code, name) + "\n\n"
    bundle += _strip_exports(app_code)

    # Escape any </script> sequences inside the bundle so they don't
    # accidentally close the wrapping <script type="text/babel"> tag.
    escaped = bundle.replace("</script>", r"<\/script>")

    # Inject the lead capture URL so any form in the page can POST to it.
    header = _DEPLOY_HEADER
    if site_title:
        header = _inject_head_tag(header, f"  <title>{escape(site_title)}</title>")
    if favicon_href:
        safe_favicon_href = escape(favicon_href, quote=True)
        header = _inject_head_tag(header, f'  <link rel="icon" href="{safe_favicon_href}" />')
        header = _inject_head_tag(header, f'  <link rel="apple-touch-icon" href="{safe_favicon_href}" />')
    if theme_color:
        header = _inject_head_tag(
            header,
            f'  <meta name="theme-color" content="{escape(theme_color, quote=True)}" />',
        )
    if lead_url:
        header = _inject_head_tag(
            header,
            f'  <script>window.KLARO_LEAD_URL="{escape(lead_url, quote=True)}";</script>',
        )
    elif project_id:
        header = _inject_head_tag(
            header,
            f'  <script>window.KLARO_LEAD_URL="/p/{escape(project_id, quote=True)}/lead";</script>',
        )

    return header + escaped + _DEPLOY_FOOTER


def published_html_key(project_id: UUID | str) -> str:
    return f"builder/published/by-project/{project_id}/index.html"


def published_metadata_key(project_id: UUID | str) -> str:
    return f"builder/published/by-project/{project_id}/meta.json"


def published_snapshot_key(project_id: UUID | str) -> str:
    return f"builder/published/by-project/{project_id}/snapshot.json"


def published_subdomain_html_key(subdomain: str) -> str:
    return f"builder/published/by-subdomain/{subdomain}/index.html"


def published_subdomain_metadata_key(subdomain: str) -> str:
    return f"builder/published/by-subdomain/{subdomain}/meta.json"


def _decode_json_bytes(raw: bytes | None) -> dict | None:
    if not raw:
        return None
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return decoded if isinstance(decoded, dict) else None


def load_published_html(
    *,
    project_id: UUID | str | None = None,
    subdomain: str | None = None,
) -> str | None:
    if not storage_enabled():
        return None
    key: str | None = None
    if project_id is not None:
        key = published_html_key(project_id)
    elif subdomain:
        key = published_subdomain_html_key(subdomain)
    if not key:
        return None
    raw = download_file(key)
    if not raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def load_published_metadata(
    *,
    project_id: UUID | str | None = None,
    subdomain: str | None = None,
) -> dict | None:
    if not storage_enabled():
        return None
    key: str | None = None
    if project_id is not None:
        key = published_metadata_key(project_id)
    elif subdomain:
        key = published_subdomain_metadata_key(subdomain)
    if not key:
        return None
    return _decode_json_bytes(download_file(key))


def load_published_snapshot(project: BuilderProject) -> dict | None:
    if storage_enabled():
        snapshot = _decode_json_bytes(download_file(published_snapshot_key(project.id)))
        if snapshot is not None:
            return snapshot
    if isinstance(project.published_files, dict):
        return dict(project.published_files)
    return None


def publish_project_artifacts(
    project: BuilderProject,
    *,
    lead_url: str,
    previous_subdomain_slug: str | None = None,
    site_meta: dict[str, str] | None = None,
) -> bool:
    """Persist public HTML + metadata to object storage. Returns False when storage is unavailable."""
    if not storage_enabled():
        return False

    files = dict(project.files or {})
    page_meta = site_meta or {}
    html = build_deploy_html(
        files,
        project_id=str(project.id),
        lead_url=lead_url,
        site_title=page_meta.get("site_title"),
        favicon_href=page_meta.get("favicon_href"),
        theme_color=page_meta.get("theme_color"),
    )
    metadata = json.dumps(
        {
            "project_id": str(project.id),
            "pack_id": str(project.pack_id),
            "subdomain_slug": project.subdomain_slug,
            "lead_url": lead_url,
            "site_title": page_meta.get("site_title"),
            "favicon_href": page_meta.get("favicon_href"),
            "theme_color": page_meta.get("theme_color"),
            "published_at": (
                project.published_at.isoformat() if project.published_at else datetime.now(timezone.utc).isoformat()
            ),
        },
        sort_keys=True,
    ).encode("utf-8")
    snapshot = json.dumps(files, sort_keys=True).encode("utf-8")

    upload_file(
        published_html_key(project.id),
        html.encode("utf-8"),
        content_type="text/html; charset=utf-8",
        cache_control=_PUBLIC_HTML_CACHE_CONTROL,
    )
    upload_file(
        published_metadata_key(project.id),
        metadata,
        content_type="application/json",
        cache_control=_PUBLIC_META_CACHE_CONTROL,
    )
    upload_file(
        published_snapshot_key(project.id),
        snapshot,
        content_type="application/json",
        cache_control=_PRIVATE_SNAPSHOT_CACHE_CONTROL,
    )

    current_subdomain = (project.subdomain_slug or "").strip().lower() or None
    previous_subdomain = (previous_subdomain_slug or "").strip().lower() or None
    if previous_subdomain and previous_subdomain != current_subdomain:
        delete_file(published_subdomain_html_key(previous_subdomain))
        delete_file(published_subdomain_metadata_key(previous_subdomain))
    if current_subdomain:
        upload_file(
            published_subdomain_html_key(current_subdomain),
            html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
            cache_control=_PUBLIC_HTML_CACHE_CONTROL,
        )
        upload_file(
            published_subdomain_metadata_key(current_subdomain),
            metadata,
            content_type="application/json",
            cache_control=_PUBLIC_META_CACHE_CONTROL,
        )
    return True


def remove_published_artifacts(
    project_id: UUID | str,
    *,
    subdomain_slug: str | None = None,
) -> bool:
    """Delete storage-backed public artifacts. Returns False when storage is unavailable."""
    if not storage_enabled():
        return False

    delete_file(published_html_key(project_id))
    delete_file(published_metadata_key(project_id))
    delete_file(published_snapshot_key(project_id))
    subdomain = (subdomain_slug or "").strip().lower()
    if subdomain:
        delete_file(published_subdomain_html_key(subdomain))
        delete_file(published_subdomain_metadata_key(subdomain))
    return True


@log_service_action()
def get_for_pack(db: Session, pack_id: UUID, user_id: UUID) -> BuilderProject | None:
    return (
        db.query(BuilderProject)
        .filter(BuilderProject.pack_id == pack_id, BuilderProject.user_id == user_id)
        .first()
    )


@log_service_action()
def get_for_pack_any(db: Session, pack_id: UUID) -> BuilderProject | None:
    """Fetch the builder project for a pack without user scoping (internal use)."""
    return (
        db.query(BuilderProject)
        .filter(BuilderProject.pack_id == pack_id)
        .first()
    )


@log_service_action()
def get_published_for_pack(db: Session, pack_id: UUID) -> BuilderProject | None:
    """Fetch the published builder project for a pack (internal use)."""
    return (
        db.query(BuilderProject)
        .filter(
            BuilderProject.pack_id == pack_id,
            BuilderProject.published_at.isnot(None),
            BuilderProject.live_url.isnot(None),
        )
        .order_by(BuilderProject.published_at.desc())
        .first()
    )


@log_service_action()
def get_by_id(db: Session, project_id: UUID, user_id: UUID) -> BuilderProject | None:
    return (
        db.query(BuilderProject)
        .filter(BuilderProject.id == project_id, BuilderProject.user_id == user_id)
        .first()
    )


@log_service_action()
def list_for_user(db: Session, user_id: UUID) -> list[BuilderProject]:
    return (
        db.query(BuilderProject)
        .filter(BuilderProject.user_id == user_id)
        .order_by(BuilderProject.updated_at.desc())
        .all()
    )


@log_service_action()
def create(
    db: Session,
    user_id: UUID,
    pack_id: UUID,
    name: str = "Untitled Project",
) -> BuilderProject:
    project = BuilderProject(user_id=user_id, pack_id=pack_id, name=name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@log_service_action()
def update(
    db: Session,
    project: BuilderProject,
    name: str | None = None,
    files: dict | None = None,
    messages: list | None = None,
) -> BuilderProject:
    if name is not None:
        project.name = name
    if files is not None:
        project.files = files
    if messages is not None:
        project.messages = messages
    db.commit()
    db.refresh(project)
    return project


@log_service_action()
def delete(db: Session, project: BuilderProject) -> None:
    db.delete(project)
    db.commit()


@log_service_action()
def publish(
    db: Session,
    project: BuilderProject,
    live_url: str,
    *,
    persist_published_files: bool = True,
    commit: bool = True,
) -> BuilderProject:
    project.live_url = live_url
    project.published_at = datetime.now(timezone.utc)
    project.published_files = dict(project.files) if persist_published_files and project.files else None
    if commit:
        db.commit()
        db.refresh(project)
    return project


@log_service_action()
def unpublish(
    db: Session,
    project: BuilderProject,
    *,
    commit: bool = True,
) -> BuilderProject:
    """Clear live_url, published_at, subdomain_slug, and published_files."""
    project.live_url = None
    project.published_at = None
    project.published_files = None
    project.subdomain_slug = None
    if commit:
        db.commit()
        db.refresh(project)
    return project


def get_published(db: Session, project_id: UUID) -> BuilderProject | None:
    """Fetch a project by ID only if it has been published (no user auth required)."""
    return (
        db.query(BuilderProject)
        .filter(
            BuilderProject.id == project_id,
            BuilderProject.live_url.isnot(None),
        )
        .first()
    )


def slug_from_name(name: str) -> str:
    """Produce a DNS-safe subdomain slug from a pack/project name: [a-z0-9-], max 63 chars."""
    if not name or not name.strip():
        return "site"
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    if not s:
        return "site"
    return s[: _SUBDOMAIN_MAX_LEN] if len(s) > _SUBDOMAIN_MAX_LEN else s

@log_service_action()
def ensure_unique_subdomain_slug(
    db: Session,
    base_slug: str,
    project_id: UUID,
) -> str:
    """Return a unique subdomain_slug for the given base_slug (e.g. from pack name).
    If base_slug is reserved or taken, appends -2, -3, ... or short project id.
    """
    slug = base_slug or "site"
    if slug in _RESERVED_SUBDOMAINS:
        slug = f"{slug}-{str(project_id).replace('-', '')[:8]}"
    existing = (
        db.query(BuilderProject.subdomain_slug)
        .filter(
            BuilderProject.subdomain_slug == slug,
            BuilderProject.id != project_id,
        )
        .first()
    )
    if not existing:
        return slug
    for n in range(2, 1000):
        candidate = f"{base_slug}-{n}"[:_SUBDOMAIN_MAX_LEN]
        if (
            db.query(BuilderProject.subdomain_slug)
            .filter(
                BuilderProject.subdomain_slug == candidate,
                BuilderProject.id != project_id,
            )
            .first()
            is None
        ):
            return candidate
    return f"{base_slug}-{str(project_id).replace('-', '')[:8]}"


def get_published_by_subdomain(db: Session, subdomain: str) -> BuilderProject | None:
    """Resolve a published builder project by subdomain (subdomain_slug). No auth."""
    if not subdomain or not subdomain.strip():
        return None
    slug = subdomain.strip().lower()
    return (
        db.query(BuilderProject)
        .filter(
            BuilderProject.subdomain_slug == slug,
            BuilderProject.published_at.isnot(None),
            BuilderProject.live_url.isnot(None),
        )
        .first()
    )
