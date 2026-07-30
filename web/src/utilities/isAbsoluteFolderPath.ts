export function isAbsoluteFolderPath(path: string) {
  const normalizedPath = path.trim()

  return (
    normalizedPath.startsWith('/') ||
    /^[a-zA-Z]:[\\/]/.test(normalizedPath) ||
    /^\\\\[^\\]+\\[^\\]+/.test(normalizedPath)
  )
}
