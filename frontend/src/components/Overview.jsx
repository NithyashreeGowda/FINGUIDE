import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const incomeExpense = [
  { name: "Income", value: 85000 },
  { name: "Expenses", value: 52000 },
  { name: "Savings", value: 33000 },
];

const allocation = [
  { name: "Stocks", value: 40 },
  { name: "Mutual Funds", value: 25 },
  { name: "ETFs", value: 15 },
  { name: "Fixed Deposits", value: 12 },
  { name: "Gold", value: 8 },
];

const COLORS = ["#B7A9E0", "#A8D8C0", "#F5C9A8", "#A9C8EA", "#D8D2EC"];

export default function Overview() {
  return (
    <div className="overview-page">
      <div className="grid-4 overview-stats" style={{ marginBottom: 28 }}>
        <div className="g-card overview-stat-card">
          <div className="stat-label">Investable Amount</div>
          <div className="stat-value">₹2,50,000</div>
        </div>
        <div className="g-card overview-stat-card">
          <div className="stat-label">Risk Profile</div>
          <div className="stat-value">Moderate</div>
        </div>
        <div className="g-card overview-stat-card">
          <div className="stat-label">Investment Horizon</div>
          <div className="stat-value">5–10 Years</div>
        </div>
        <div className="g-card overview-stat-card">
          <div className="stat-label">Primary Goal</div>
          <div className="stat-value">Wealth Creation</div>
        </div>
      </div>

      <div className="grid-2 overview-charts">
        <div className="g-card overview-chart-card">
          <div className="section-heading">Income vs Expenses</div>
          <div className="section-sub">Monthly snapshot</div>
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={incomeExpense}>
              <XAxis dataKey="name" tick={{ fontSize: 14 }} />
              <YAxis tick={{ fontSize: 14 }} />
              <Tooltip />
              <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#B7A9E0" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="g-card overview-chart-card">
          <div className="section-heading">Current Asset Allocation</div>
          <div className="section-sub">Across your portfolio</div>
          <ResponsiveContainer width="100%" height={340}>
            <PieChart>
              <Pie data={allocation} dataKey="value" nameKey="name" innerRadius={80} outerRadius={130} paddingAngle={3} label={{ fontSize: 13 }}>
                {allocation.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}