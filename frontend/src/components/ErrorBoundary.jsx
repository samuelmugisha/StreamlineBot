import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { crashed: false, resetKey: 0 }
  }

  static getDerivedStateFromError() {
    return { crashed: true }
  }

  render() {
    if (this.state.crashed) {
      return (
        <div className="flex flex-col w-[440px] h-[500px] bg-white rounded-2xl shadow-2xl border border-slate-200 items-center justify-center gap-3 p-6 text-center">
          <svg className="w-10 h-10 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
          </svg>
          <div>
            <p className="text-sm font-semibold text-slate-700">AdminIE ran into a problem</p>
            <p className="text-xs text-slate-400 mt-1">Please refresh the page to restart the chat.</p>
          </div>
          <button
            onClick={() => this.setState(s => ({ crashed: false, resetKey: s.resetKey + 1 }))}
            className="text-xs font-semibold text-white bg-brand-primary hover:bg-brand-light px-4 py-1.5 rounded-full transition-colors">
            Try again
          </button>
        </div>
      )
    }
    return <div key={this.state.resetKey} style={{ display: 'contents' }}>{this.props.children}</div>
  }
}
