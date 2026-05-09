import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
  id?: string;
};

export function Card({ children, className = "", id }: CardProps) {
  return (
    <article className={`ui-card ${className}`.trim()} id={id}>
      {children}
    </article>
  );
}

type DataTableRow = {
  label: string;
  value: ReactNode;
  tone?: "success" | "warning" | "danger" | "neutral";
};

export function DataTable({ rows }: { rows: DataTableRow[] }) {
  return (
    <table className="data-table">
      <tbody>
        {rows.map((row) => (
          <tr key={row.label}>
            <th scope="row">{row.label}</th>
            <td className={row.tone ? `table-tone table-tone-${row.tone}` : undefined}>{row.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
