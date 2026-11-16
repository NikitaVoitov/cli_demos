declare module '*.yaml' {
  const data: unknown
  export default data
}

declare module '*.md' {
  const html: string
  export default html
}
