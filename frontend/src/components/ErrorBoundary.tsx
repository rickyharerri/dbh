import { Component, type ErrorInfo, type ReactNode } from 'react'

/** Last line of defence: an unexpected UI error shows a message and a reload button instead of a blank page. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('UI error', error, info.componentStack) }
  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div role="alert" className="mx-auto mt-10 max-w-xl rounded-lg border border-red-300 bg-red-50 p-6 text-red-900">
        <p className="text-lg font-semibold">Something went wrong showing this page.</p>
        <p className="mt-1">Your data is safe. Reload the page to try again.</p>
        <button type="button" className="btn btn-secondary mt-4" onClick={() => window.location.reload()}>Reload page</button>
      </div>
    )
  }
}
