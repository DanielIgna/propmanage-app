// Scoped error boundary around the 3D <Canvas>. A single failed model load
// shows an inline banner instead of crashing the whole Digital Twin route.
import React from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

export class ViewerErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(error) {
    // eslint-disable-next-line no-console
    console.warn("[DT viewer] 3D load error (contained):", error?.message);
  }
  componentDidUpdate(prev) {
    if (prev.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="absolute inset-0 flex items-center justify-center bg-stone-950" data-testid="viewer-3d-error">
          <div className="text-center max-w-sm px-6">
            <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-3" />
            <p className="text-sm text-white">Un strat 3D nu a putut fi încărcat.</p>
            <p className="text-xs text-stone-500 mt-1">Restul funcțiilor (Q&A, Concept AI, Validare) rămân disponibile în bara laterală.</p>
            <button
              onClick={() => this.props.onRetry?.()}
              className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-stone-200 text-xs"
              data-testid="viewer-3d-retry"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Reîncearcă
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ViewerErrorBoundary;
