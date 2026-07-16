import { Outlet } from "react-router";

export default function App() {
  return (
    <div className="app-layout">
      <header
        style={{
          padding: "16px 24px",
          borderBottom: "1px solid #e5e7eb",
          background: "#ffffff",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h2
          style={{
            margin: 0,
            fontSize: "22px",
            fontWeight: "600",
          }}
        >
          FreProts
        </h2>
      </header>

      <main
        style={{
          padding: "24px",
        }}
      >
        <Outlet />
      </main>
    </div>
  );
}
