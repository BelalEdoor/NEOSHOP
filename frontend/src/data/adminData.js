// ── Admin Data ────────────────────────────────────────────────────────────────
// All mock data removed. Real data sources:
//   - Products:  GET /api/products/ (backend API)
//   - Invoices:  localStorage key 'neoshop-invoices' (set by POSPage on checkout)
//   - Employees: Add your own via AdminEmployees page
//   - Suppliers: Add your own via AdminSuppliers page

// Empty defaults — pages will load from real sources
export const mockProducts   = []
export const mockInvoices   = []
export const mockEmployees  = []
export const mockSuppliers  = []
export const mockSalesData  = []
export const mockDashboardStats = {
  todaySales: 0, todayOrders: 0, monthRevenue: 0,
  totalProducts: 0, lowStockCount: 0, activeEmployees: 0,
  topProducts: [],
}
