"use client"

import * as React from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Search } from "lucide-react"

export interface Column<T> {
  header: string
  accessorKey: keyof T
  cell?: (item: T) => React.ReactNode
  sortable?: boolean
}

interface DataTableProps<T> {
  data: T[]
  columns: Column<T>[]
  searchKey?: keyof T
  isLoading?: boolean
}

export function DataTable<T>({
  data,
  columns,
  searchKey,
  isLoading = false,
}: DataTableProps<T>) {
  const [search, setSearch] = React.useState("")
  const [sortConfig, setSortConfig] = React.useState<{ key: keyof T; direction: "asc" | "desc" } | null>(null)
  const [page, setPage] = React.useState(1)
  const itemsPerPage = 10

  const handleSort = (key: keyof T) => {
    let direction: "asc" | "desc" = "asc"
    if (sortConfig && sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc"
    }
    setSortConfig({ key, direction })
  }

  const filteredData = React.useMemo(() => {
    if (!searchKey || !search) return data
    return data.filter((item) =>
      String(item[searchKey]).toLowerCase().includes(search.toLowerCase())
    )
  }, [data, search, searchKey])

  const sortedData = React.useMemo(() => {
    if (!sortConfig) return filteredData
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortConfig.key]
      const bVal = b[sortConfig.key]
      if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1
      if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1
      return 0
    })
  }, [filteredData, sortConfig])

  const paginatedData = React.useMemo(() => {
    const startIndex = (page - 1) * itemsPerPage
    return sortedData.slice(startIndex, startIndex + itemsPerPage)
  }, [sortedData, page])

  const totalPages = Math.ceil(sortedData.length / itemsPerPage)

  return (
    <div className="space-y-4 w-full">
      {searchKey && (
        <div className="flex items-center gap-2">
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={`Filter...`}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              className="pl-8"
            />
          </div>
          {/* Mock filters mirroring "All Statuses / All Types / All Priorities / All Assignees" */}
          <div className="hidden lg:flex gap-2 text-sm text-muted-foreground ml-auto">
            <Button variant="outline" size="sm" className="h-9">All Statuses</Button>
            <Button variant="outline" size="sm" className="h-9">All Types</Button>
            <Button variant="outline" size="sm" className="h-9">Assignees</Button>
          </div>
        </div>
      )}

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead
                  key={String(col.accessorKey)}
                  className={col.sortable ? "cursor-pointer hover:bg-muted/50" : ""}
                  onClick={() => col.sortable && handleSort(col.accessorKey)}
                >
                  <div className="flex items-center gap-1">
                    {col.header}
                    {sortConfig?.key === col.accessorKey && (
                      sortConfig.direction === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                    )}
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : paginatedData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No results found.
                </TableCell>
              </TableRow>
            ) : (
              paginatedData.map((row, i) => (
                <TableRow key={i}>
                  {columns.map((col) => (
                    <TableCell key={String(col.accessorKey)}>
                      {col.cell ? col.cell(row) : String(row[col.accessorKey])}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between px-2">
        <div className="text-sm text-muted-foreground">
          Showing {((page - 1) * itemsPerPage) + 1} to {Math.min(page * itemsPerPage, sortedData.length)} of {sortedData.length} entries
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4" />
            <span className="sr-only">Previous</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || totalPages === 0}
          >
            <ChevronRight className="h-4 w-4" />
            <span className="sr-only">Next</span>
          </Button>
        </div>
      </div>
    </div>
  )
}
