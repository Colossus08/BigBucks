# Personal Finance Manager

A local, ledger-driven personal finance and financial planning application built with **FastAPI**, **SQLite** (SQLAlchemy 2.0 + Alembic), and **React + TypeScript + Recharts**.

> **Philosophy:** *Understand your money. Manage your present. Plan your future. Build your wealth.*

---

## 1. Quick Start (Running the App)

Open **two** PowerShell terminals:

### Terminal 1 — Backend API (`http://localhost:8000`)
```powershell
& C:\Users\messa\Menu\my_coding\finance\.venv\Scripts\Activate.ps1
cd C:\Users\messa\Menu\my_coding\finance\finance-app\backend
uvicorn app.main:app --reload
```
*(Database migrations and default categories/rules run automatically on startup. Interactive API docs are at `http://localhost:8000/docs`.)*

### Terminal 2 — Frontend UI (`http://localhost:5173`)
```powershell
cd C:\Users\messa\Menu\my_coding\finance\finance-app\frontend
npm run dev
```

Open **`http://localhost:5173`** in your browser.

---

## 2. Step-by-Step User Guide (How to Use the App)

### Step 1: Import Your CommBank CSV
1. Export your transactions from **CommBank NetBank** as a **CSV** (`Date, Amount, Description, Balance`).
2. In the top-right header, click **Import CSV** (or open **Ledger & Settings → Import NetBank CSV**).
3. Select **Smart Access**, choose your `.csv` file, and click **Upload & Import**.
   - **Duplicate-safe:** Every row is hashed with SHA-256 (`account + date + amount + description + running balance`). Re-uploading overlapping CSV exports will automatically skip duplicates.
   - **Balance Continuity Check:** If any rows are missing between dates, the import report flags exact running-balance gaps.

---

### Step 2: Categorise Transactions Quickly
1. Open **Ledger & Settings** (top-right) → **Categories & Quick Rules** (or click **Review & Categorise** on the yellow banner on Overview).
2. You have **three fast ways** to categorise:
   - **Multi-Select Bulk Assign:** Tick the checkboxes next to multiple merchants (e.g. 10 restaurants), choose `Lifestyle — Restaurants` at the top, and click **Apply to Selected**. This categorises all of them and saves learned rules in one click.
   - **Single-Merchant Dropdown:** Pick a category on any merchant row in **Quick Categorise by Merchant** to categorise every transaction from that merchant at once.
   - **Quick Keyword Rule:** Type a keyword (e.g. `SHILOH`, `OPSM`, `BUNNINGS`), select a category, and click **Add & Apply Rule**.
3. **Mistake Recovery:** Click **Undo Latest Rule** (or open **Rule Registry** to delete any specific learned rule) to revert changes and re-apply baseline rules.
4. **Custom Categories:** Use **Create Custom Category** to add your own categories under any group (`Essential`, `Transport`, `Lifestyle`, `Commitments`, `Giving`, `Growth`, `Income`, `Reimbursements`).

#### How Incoming Money Is Handled
- **Salary / Allowance / Gifts (`Income` group):** Counted as real **Income**.
- **People Paying You Back (`Reimbursements` group):** Offsets your **Net Spent** rather than inflating your Income.
- **Merchant Refunds (positive amount in an expense category like `Shopping` or `Subscription services`):** Reduces spending in that specific category.
- **Uncategorised Incoming Money:** Held aside and highlighted in the banner until you categorise it, so random deposits or uncategorised PayID transfers never silently inflate your Income.
- **PayID Transfers from the Same Person:** If the same person sometimes pays you back and other times sends a gift, switch to **All Transactions**, **uncheck** *"Apply category change to all transactions from the same merchant"*, and categorise that single row.
- **Exclude One-Off Anomalies:** In **All Transactions**, click **Exclude** on any row to omit it from reports and budgets.

---

### Step 3: Track Your Savings Accounts & Link Goals
1. Open **Ledger & Settings → Savings Accounts**.
2. Under **Detected transfer accounts**, you'll see the internal accounts you transfer to/from (`xx0464`, `xx1800`, `xx3834`).
3. Give each one a name (e.g. `Emergency Saver`, `Car Saver`) and click **Track as savings**.
   - Transfers between Smart Access and your savings accounts are never double-counted as expenses or income, and net transfers into tracked savings accounts appear on **Overview** under **Net Saved (`Moved to savings`)**.
4. Go to the **Goals** tab in the top navigation:
   - Use the **Linked account** dropdown on any goal card (or when creating a new goal) to link it to one of your tracked savings accounts.
   - Your goal progress, completion `%`, and projected completion date will then update **automatically** from your bank transfers!
   - You can also log manual contributions (`+ Contribute`) or include a buffer for extra costs (e.g., car registration, insurance, and servicing).

#### Handling Monthly Holding Buckets (e.g., Saving Weekly for Tithes & Paying Monthly)
If you transfer money out of **Smart Access** into a separate sub-account each pay (like `xx1800`) and then transfer it back at the end of the month to pay **Shiloh / TITHE.LY**:
1. **No double-counting:** Both the weekly `Transfer to xx1800` and the end-of-month `Transfer from xx1800` are automatically marked as `Internal transfer` and excluded from Income and Spent totals. Only the final payment to **Shiloh / TITHE.LY** is recorded as an expense under `Giving — Tithes & Offering`.
2. **Track the bucket without linking it to a long-term Goal:** In **Ledger & Settings → Savings Accounts**, name `xx1800` (e.g. `Tithes Holding`) so you can see its balance accumulate during the month and reset when transferred back, while only linking your long-term savers (`xx0464` / `xx3834`) to your **Goals**.
3. **Reserve it in your Pay-Cycle Plan:** Add a monthly **Budget** for `Tithes & Offering` on the **Budget** tab (or add `Shiloh` under **Your Recurring Payments** on **Insights**) so your **Safe-to-Spend** and **Pay-Cycle Allocation** reserve that money each pay.

---

### Step 4: Read Your Overview Dashboard
- **Period Switcher:** Switch between **Monthly** (with a dropdown to inspect any specific past month like `2026-11`, `2026-10`), **Full Year**, or **All Time**.
- **Safe-to-Spend (Payday Calendar):** Shows how much of your current Smart Access balance is genuinely free to spend before next payday (`Bank Balance − Upcoming Recurring Bills − Planned Goal Allocations`), plus your **Daily Burn Rate (`$/day`)**.
- **Spending by Group (Gross):** Interactive donut chart with dollar & percentage breakdown. Click any group slice or legend row (e.g. `Lifestyle` or `Essential`) to drill down into individual categories, then click **All Groups** to zoom back out.
- **Income vs. Spending:** 6-month trajectory comparing monthly inflows, outflows, and net surplus.

---

### Step 5: Set Budgets & Pay-Cycle Plan (`Budget` Tab)
- **Pay-Cycle Allocation:** Shows your estimated net pay per cycle alongside **Budgeted + Bills / Pay**, **Planned Goals / Pay**, and **Unallocated Discretionary** cash.
- **Set Category Budgets:** Create weekly, fortnightly, or monthly limits for any expense category, or click **Apply** on any row in **Recommended Monthly Budgets** (auto-calculated from your 3-month spending average).
- **Progress & Alerts:** Active budgets show progress bars, end-of-period spend projections, and `80%+ used` / `Over budget` warnings.

---

### Step 6: Manage Recurring Bills & Forecast (`Insights` Tab)
- **Your Recurring Payments:** Add your real fixed commitments manually (e.g. Rent, Spotify, Lebara) or click **+ Add** on items in **Suggested Periodic Payments**. Click **Dismiss** on non-commitments (saved permanently in SQLite so they never reappear), or **Remove** any saved commitment at any time.
- **Price-Creep & Hike Alerts:** Whenever an imported transaction for a confirmed recurring bill exceeds its baseline price, an alert banner shows the old price, new price, and `%` increase with a one-click **Update Baseline** button.
- **Cash Flow Forecast & What-If Scenarios:** View 3-month, 6-month, 12-month, and 5-year cash projections, and test scenarios (e.g., *"What if I save an extra $100/fortnight?"*) to see the 5-year impact.

---

### Step 7: Track Investments, Super & Tax (`Wealth` & `Tax & Rule Engine`)
- **Wealth Tab:**
  - Track **Total Net Worth** (`Cash + Investments + Superannuation`).
  - Add ETFs, shares, or index funds (`Symbol`, `Units`, `Avg Cost`, `Current Price`) and refresh prices anytime using the inline **Refresh** control.
  - Update your **Superannuation** balance, extra monthly contributions, and expected return `%` to view 5, 10, 20, and 30-year compound projections.
- **Ledger & Settings → Tax & Rule Engine:**
  - **Real-Time Salary Reconciliation:** Compares your declared annualized net pay against actual `Salary` direct credits from your bank statements.
  - **EOFY Tax Deduction & WFH Ledger:** Tag work-related expenses in **All Transactions** with `+ Tax (D5)` and log Work-From-Home hours (calculated at the ATO fixed rate of `67c/hr`). Click **Export EOFY Tax CSV** to download your claimable schedule for the Australian financial year (`1 July – 30 June`).

---

### Step 8: Back Up & Export Your Data
Open **Ledger & Settings** (top-right):
- **Export CSV:** Downloads all transactions (with cleaned merchant names and assigned categories) as `transactions_export.csv`.
- **Backup DB:** Downloads a complete, consistent snapshot of your SQLite database (`finance_backup.db`).

---

## 3. Running Tests & Production Build

```powershell
# Backend test suite (30 tests)
cd C:\Users\messa\Menu\my_coding\finance\finance-app\backend
C:\Users\messa\Menu\my_coding\finance\.venv\Scripts\pytest.exe -q -p no:cacheprovider

# Frontend TypeScript check & production bundle
cd C:\Users\messa\Menu\my_coding\finance\finance-app\frontend
npm run build
```
