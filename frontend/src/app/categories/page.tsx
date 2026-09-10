import { Tags, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { DataNotice } from "@/components/shared/DataNotice"
import { FormDialog } from "@/components/shared/FormDialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { createCategory } from "@/app/actions"
import { getCategories } from "@/lib/queries"

type Category = { categoryid: number; categoryname: string }
const columns: Column<Category>[] = [
  { header: "Category ID", accessorKey: "categoryid", sortable: true },
  { header: "Category Name", accessorKey: "categoryname", sortable: true },
]

export default async function CategoriesPage() {
  const result = await getCategories()
  return <div className="flex flex-col gap-6"><header className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between"><div><div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600"><Tags className="h-4 w-4" /> Product taxonomy</div><h1 className="text-2xl font-black text-slate-900 dark:text-white">Product Categories</h1><p className="text-sm text-slate-500">Categories currently stored in Supabase.</p></div><FormDialog title="Add product category" description="Create a category in the live catalogue." trigger={<Button><Plus className="mr-2 h-4 w-4" /> Add Category</Button>} action={createCategory} submitLabel="Create category"><Label htmlFor="categoryname">Category name</Label><Input id="categoryname" name="categoryname" required /></FormDialog></header><DataNotice error={result.error} rlsBlocked={result.rlsBlocked} /><DataTable data={result.data} columns={columns} searchKey="categoryname" /></div>
}