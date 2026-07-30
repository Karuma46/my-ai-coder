type CreatedRecord = {
  createdAt: string
}

export function sortByCreatedAtDescending<T extends CreatedRecord>(
  records: readonly T[],
) {
  return [...records].sort((first, second) =>
    second.createdAt.localeCompare(first.createdAt),
  )
}
