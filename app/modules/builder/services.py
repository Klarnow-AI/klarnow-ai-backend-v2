"""Builder project services. CRUD scoped to user via pack ownership."""

import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.builder.models import BuilderProject

# Subdomains that must not be used (reserved or ambiguous)
_RESERVED_SUBDOMAINS = frozenset({"www", "api", "app", "admin", "mail", "ftp", "staging"})
_SUBDOMAIN_MAX_LEN = 63


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
    if lead_url:
        lead_tag = f'  <script>window.KLARO_LEAD_URL="{lead_url}";</script>\n'
        header = header.replace("</head>", lead_tag + "</head>", 1)
    elif project_id:
        lead_tag = f'  <script>window.KLARO_LEAD_URL="/p/{project_id}/lead";</script>\n'
        header = header.replace("</head>", lead_tag + "</head>", 1)

    return header + escaped + _DEPLOY_FOOTER


@log_service_action()
def get_for_pack(db: Session, pack_id: UUID, user_id: UUID) -> BuilderProject | None:
    return (
        db.query(BuilderProject)
        .filter(BuilderProject.pack_id == pack_id, BuilderProject.user_id == user_id)
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
def publish(db: Session, project: BuilderProject, live_url: str) -> BuilderProject:
    project.live_url = live_url
    project.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    return project


@log_service_action()
def unpublish(db: Session, project: BuilderProject) -> BuilderProject:
    """Clear live_url, published_at, and subdomain_slug so the site is no longer served."""
    project.live_url = None
    project.published_at = None
    project.subdomain_slug = None
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
