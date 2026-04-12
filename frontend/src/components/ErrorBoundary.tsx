"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div
          className="flex min-h-[300px] flex-col items-center justify-center rounded-[1.25rem] border p-8 text-center"
          style={{ background: "var(--surface-warning)", borderColor: "var(--warning-soft)" }}
        >
          <div className="mb-3 text-4xl">⚠️</div>
          <div className="text-base font-semibold" style={{ color: "var(--warning)" }}>
            เกิดข้อผิดพลาดในส่วนนี้
          </div>
          <p className="mt-1 max-w-xs text-sm leading-6" style={{ color: "var(--text-2)" }}>
            {this.state.error?.message ?? "มีข้อผิดพลาดที่ไม่คาดคิดในแผงนี้"}
          </p>
          <button
            className="q-btn-secondary mt-4 px-4 py-2 text-sm"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            ลองใหม่
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
