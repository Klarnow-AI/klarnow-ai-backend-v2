import { NextRequest, NextResponse } from "next/server";

const BACKEND_TIMEOUT_MS = 60000; // 60s

function getBackendUrl(pathSegments: string[], search?: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const path = pathSegments.length ? `/${pathSegments.join("/")}` : "";
  const q = search && search.startsWith("?") ? search : search ? `?${search}` : "";
  return `${base.replace(/\/$/, "")}${path}${q}`;
}

/** Forward request to backend with explicit timeout; returns 504 on timeout instead of ECONNRESET. */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

async function proxyRequest(
  req: NextRequest,
  { path }: { path: string[] }
): Promise<NextResponse> {
  const url = getBackendUrl(path, req.nextUrl.search);
  const headers = new Headers(req.headers);
  headers.delete("host");
  const init: RequestInit = {
    method: req.method,
    headers,
    signal: AbortSignal.timeout(BACKEND_TIMEOUT_MS),
  };
  if (req.method !== "GET" && req.method !== "HEAD" && req.body) {
    init.body = req.body;
  }
  try {
    const res = await fetch(url, init);
    const resHeaders = new Headers(res.headers);
    resHeaders.delete("transfer-encoding");
    return new NextResponse(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: resHeaders,
    });
  } catch (err) {
    const isTimeout =
      err instanceof Error && (err.name === "TimeoutError" || err.name === "AbortError");
    if (isTimeout) {
      return NextResponse.json(
        { detail: "Backend request timed out" },
        { status: 504 }
      );
    }
    throw err;
  }
}
