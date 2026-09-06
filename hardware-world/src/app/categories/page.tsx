import { Plus, Tags } from "lucide-react"
import { createCategory } from "@/app/actions"
import { Field } from "@/components/shared/Field"
import { FormDialog } from "@/components/shared/FormDialog"
import { DataNotice } from "@/components/shared/DataNotice"
import { DataTable, type Column } from "@/components/shared/DataTable"
import { Button } from "@/components/ui/button"
import { getCategories, type CategoryRow } from "@/lib/queries"

const columns: Column<CategoryRow>[] = [{ header: "Category", accessorKey: "categoryname", sortable: true }]
export default async function CategoriesPage() { const categories = await getCategories(); return <div className="grid gap-6"><div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-2xl font-semibold">Categories</h1><p className="text-muted-foreground">Classify products with real catalogue groups.</p></div><FormDialog title="Add category" description="Create a category used by products." trigger={<Button><Plus /> Add category</Button>} action={createCategory} submitLabel="Add category"><Field label="Category name" name="categoryname" required placeholder="e.g. Plumbing" /></FormDialog></div><DataNotice {...categories} /><div className="flex items-center gap-2 text-sm text-muted-foreground"><Tags className="size-4" />{categories.data.length} categories</div><DataTable data={categories.data} columns={columns} searchKey="categoryname" rowKey={(row) => row.categoryid} emptyMessage="No categories yet. Add the first category above." /></div> }
