import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Summary, formatAudFromCents } from "../api/client";

const COLORS = ["#1B382B", "#7D9A83", "#C86452", "#B58D4E", "#4A6B5D", "#87968D", "#5C6B61"];

interface Props {
  summary: Summary;
}

export function SpendingDonut({ summary }: Props) {
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);

  const groupData = Object.entries(summary.by_group).map(([name, totalCents]) => ({
    name,
    value: totalCents / 100,
    cents: totalCents,
  }));

  const categoryData = summary.by_category
    .filter((c) => !selectedGroup || c.category_group === selectedGroup)
    .map((c) => ({
      name: c.category_name,
      value: c.total_cents / 100,
      cents: c.total_cents,
    }));

  const data = selectedGroup ? categoryData : groupData;
  const totalCents = data.reduce((acc, item) => acc + item.cents, 0);

  return (
    <div className="lg:col-span-6 bg-surface-card border border-primary/20 p-6 md:p-8 flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between mb-6 pb-4 border-b border-primary/10">
          <div>
            <div className="text-[10px] text-terracotta uppercase tracking-widest mb-1 font-bold font-display">
              .03. Allocation Breakdown
            </div>
            <h2 className="heading-display text-2xl font-bold text-primary">
              {selectedGroup ? `Spending: ${selectedGroup}` : "Spending by Group (Gross)"}
            </h2>
          </div>
          {selectedGroup && (
            <button
              className="border border-primary/25 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-primary hover:bg-surface-low"
              onClick={() => setSelectedGroup(null)}
              type="button"
            >
              All Groups
            </button>
          )}
        </div>

        {data.length === 0 ? (
          <p className="text-xs text-on-surface-variant py-12 text-center">
            No expenses recorded in this period.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
            <div className="w-full h-56">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={52}
                    outerRadius={86}
                    paddingAngle={2}
                    onClick={(entry) => {
                      if (!selectedGroup && entry?.name) {
                        setSelectedGroup(entry.name);
                      }
                    }}
                  >
                    {data.map((entry, idx) => (
                      <Cell
                        key={entry.name}
                        fill={COLORS[idx % COLORS.length]}
                        style={{ cursor: selectedGroup ? "default" : "pointer" }}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#FAF8F5",
                      borderColor: "#1B382B",
                      borderRadius: 0,
                      fontSize: "12px",
                    }}
                    formatter={(val) => formatAudFromCents(Math.round(Number(val) * 100))}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-2">
              {data.map((item, idx) => {
                const pct = totalCents > 0 ? ((item.cents / totalCents) * 100).toFixed(1) : "0.0";
                return (
                  <div
                    key={item.name}
                    onClick={() => {
                      if (!selectedGroup) setSelectedGroup(item.name);
                    }}
                    className={`flex items-center justify-between text-xs py-1.5 border-b border-primary/10 ${
                      selectedGroup ? "" : "cursor-pointer hover:bg-surface-low px-1"
                    }`}
                  >
                    <span className="flex items-center gap-2 font-medium text-primary">
                      <span
                        className="w-2.5 h-2.5 shrink-0"
                        style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                      />
                      <span>{item.name}</span>
                    </span>
                    <span className="tabular-nums font-display font-bold text-primary">
                      {formatAudFromCents(item.cents)}{" "}
                      <span className="text-[10px] font-normal text-on-surface-subtle">({pct}%)</span>
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <div className="mt-6 pt-4 border-t border-primary/10 flex items-center justify-between text-[11px] text-on-surface-variant">
        <span>Click a group slice or row to inspect categories.</span>
        <span className="font-display font-bold text-primary tabular-nums">
          Total: {formatAudFromCents(totalCents)}
        </span>
      </div>
    </div>
  );
}
