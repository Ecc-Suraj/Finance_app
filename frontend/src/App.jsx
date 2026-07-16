import { Routes, Route, Navigate } from "react-router-dom";
import Reports from "./pages/Reports";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Reports />} />

      {/* Redirect any unknown URL back to Home */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
