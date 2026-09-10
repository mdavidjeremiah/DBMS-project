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
import { cn } from "@/lib/utils"

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
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="relative w-full max-w-md">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-orange-600 dark:text-orange-400" />
            <Input
              placeholder={`Filter by ${String(searchKey)}...`}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              className="pl-9 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 rounded-xl text-sm focus-visible:ring-2 focus-visible:ring-orange-500 shadow-sm"
            />
          </div>
          {/* Quick filter pills */}
          <div className="hidden lg:flex gap-2 text-xs font-semibold">
            <Button variant="outline" size="sm" className="h-9 rounded-xl border-slate-200 dark:border-slate-800 hover:bg-orange-50 hover:text-orange-600 dark:hover:bg-slate-800">All Statuses</Button>
            <Button variant="outline" size="sm" className="h-9 rounded-xl border-slate-200 dark:border-slate-800 hover:bg-orange-50 hover:text-orange-600 dark:hover:bg-slate-800">All Types</Button>
            <Button variant="outline" size="sm" className="h-9 rounded-xl border-slate-200 dark:border-slate-800 hover:bg-orange-50 hover:text-orange-600 dark:hover:bg-slate-800">Export CSV</Button>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-lg overflow-hidden">
        <Table>
          <TableHeader className="bg-slate-900 text-white dark:bg-slate-950">
            <TableRow className="border-b border-slate-800 hover:bg-slate-900">
              {columns.map((col) => (
                <TableHead
                  key={String(col.accessorKey)}
                  className={cn(
                    "text-xs font-bold uppercase tracking-wider text-slate-300 py-3.5 px-4 select-none",
                    col.sortable ? "cursor-pointer hover:text-orange-400 transition-colors" : ""
                  )}
                  onClick={() => col.sortable && handleSort(col.accessorKey)}
                >
                  <div className="flex items-center gap-1.5">
                    {col.header}
                    {col.sortable && (
                      <span className="text-slate-500">
                        {sortConfig?.key === col.accessorKey ? (
                          sortConfig.direction === "asc" ? <ArrowUp className="h-3.5 w-3.5 text-orange-400" /> : <ArrowDown className="h-3.5 w-3.5 text-orange-400" />
                        ) : (
                          <span className="text-[10px] opacity-40">↕</span>
                        )}
                      </span>
                    )}
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-32 text-center text-slate-500 font-medium">
                  <div className="flex items-center justify-center gap-2">
                    <div className="h-4 w-4 rounded-full border-2 border-orange-600 border-t-transparent animate-spin" />
                    Loading records...
                  </div>
                </TableCell>
              </TableRow>
            ) : paginatedData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-32 text-center text-slate-500 font-medium">
                  No records match your filter criteria.
                </TableCell>
              </TableRow>
            ) : (
              paginatedData.map((row, i) => (
                <TableRow
                  key={i}
                  className="border-b border-slate-100 dark:border-slate-800/60 hover:bg-orange-500/5 dark:hover:bg-slate-800/50 transition-colors text-slate-800 dark:text-slate-200 text-sm font-medium"
                >
                  {columns.map((col) => (
                    <TableCell key={String(col.accessorKey)} className="py-3.5 px-4">
                      {col.cell ? col.cell(row) : String(row[col.accessorKey])}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between px-2 pt-1 text-xs text-slate-500 dark:text-slate-400">
        <div className="font-semibold">
          Showing <span className="text-slate-900 dark:text-white">{sortedData.length === 0 ? 0 : ((page - 1) * itemsPerPage) + 1}</span> to <span className="text-slate-900 dark:text-white">{Math.min(page * itemsPerPage, sortedData.length)}</span> of <span className="text-slate-900 dark:text-white">{sortedData.length}</span> entries
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            className="h-8 rounded-lg border-slate-200 dark:border-slate-800 font-semibold"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4 mr-1 text-orange-600" />
            Prev
          </Button>
          <span className="text-xs font-bold text-slate-700 dark:text-slate-300 px-1">
            Page {page} of {totalPages || 1}
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-8 rounded-lg border-slate-200 dark:border-slate-800 font-semibold"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || totalPages === 0}
          >
            Next
            <ChevronRight className="h-4 w-4 ml-1 text-orange-600" />
          </Button>
        </div>
      </div>
    </div>
  )
}
