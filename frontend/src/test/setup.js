import '@testing-library/jest-dom/vitest'

// jsdom doesn't implement scrollIntoView — ChatWindow calls it on every
// message update to keep the view pinned to the latest message.
Element.prototype.scrollIntoView = Element.prototype.scrollIntoView || (() => {})
