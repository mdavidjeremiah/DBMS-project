import { Tags, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RlsNotice, ErrorNotice } from "@/components/shared/RlsNotice"
import { getCategories, CategoryRow } from "@/lib/queries"

const columns: Column<CategoryRow>[] = [
  { header: "Category", accessorKey: "categoryname", sortable: true },
]

export default async function CategoriesPage() {
  const { data, rlsBlocked, error } = await getCategories()

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Categories
          </h1>
          <p className="text-muted-foreground">
            Classification groups used to organize products.
          </p>
        </div>
        <Modal
          title="Add New Category"
          description="Create a product classification group."
          trigger={
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Add Category
            </Button>
          }
          confirmText="Add Category"
        >
          <div className="grid gap-2 py-2">
            <Label htmlFor="categoryname">Category Name</Label>
            <Input id="categoryname" placeholder="e.g. Cement, Timber, Paint" />
          </div>
        </Modal>
      </div>

      {error && <ErrorNotice message={error} />}
      {rlsBlocked && !error && <RlsNotice />}

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Tags className="h-4 w-4" />
        {data.length} categor{data.length === 1 ? "y" : "ies"} on file
      </div>

      <DataTable
        data={data}
        columns={columns}
        searchKey="categoryname"
        emptyMessage={
          rlsBlocked
            ? "No categories visible yet -- RLS has no read policy configured."
            : "No categories yet. Add your first one above."
        }
      />
    </div>
  )
}