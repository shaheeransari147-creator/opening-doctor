"use client";

import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// Single-series magnitude comparison: one hue, sequential job (never a
// rainbow-per-bar -- the axis label already carries identity, per the
// dataviz skill's categorical-vs-sequential rule). The --chart-series value
// itself (light #158a5c / dark #3fa578, each validated against its chart
// surface with scripts/validate_palette.js) is defined once in globals.css
// so it swaps automatically with the theme.
interface DatumBase {
  name: string;
  value: number;
}

export function RankedBarChart({
  data,
  valueFormatter = (v: number) => String(v),
  height,
}: {
  data: DatumBase[];
  valueFormatter?: (value: number) => string;
  height?: number;
}) {
  const rowHeight = 40;
  const chartHeight = height ?? Math.max(120, data.length * rowHeight);

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 36, bottom: 4, left: 4 }}>
        <CartesianGrid horizontal={false} stroke="var(--border)" strokeWidth={1} />
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="name"
          width={150}
          tickLine={false}
          axisLine={false}
          tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
        />
        <Tooltip
          cursor={{ fill: "var(--muted)" }}
          contentStyle={{
            background: "var(--popover)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12,
            color: "var(--popover-foreground)",
          }}
          formatter={(value) => [valueFormatter(Number(value)), "Value"]}
        />
        <Bar dataKey="value" fill="var(--chart-series)" radius={[0, 4, 4, 0]} maxBarSize={24}>
          <LabelList
            dataKey="value"
            position="right"
            formatter={(v: ReactNode) => valueFormatter(Number(v))}
            style={{ fill: "var(--muted-foreground)", fontSize: 12 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
