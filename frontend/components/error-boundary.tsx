"use client";

import React from "react";
import { Button } from "@/components/ui/button";

type Props = {
  children: React.ReactNode;
  /** Shown above the error message. Defaults to "Something went wrong". */
  fallbackTitle?: string;
};

type State = {
  error: Error | null;
};

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-8 text-center">
          <h2 className="text-lg font-semibold text-foreground">
            {this.props.fallbackTitle ?? "Something went wrong"}
          </h2>
          <p className="max-w-md text-sm text-muted-foreground">
            {this.state.error.message || "An unexpected error occurred."}
          </p>
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => this.setState({ error: null })}
            >
              Try again
            </Button>
            <Button onClick={() => window.location.reload()}>
              Reload page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
